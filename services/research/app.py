"""Disabled public entry point and separately constructed synthetic HTTP transport."""
import asyncio
import hmac
import ipaddress
import json
from pathlib import Path
import sys
import uuid

from tools.research_admission import MAX_BYTES, digest_token, parse, unique
from scripts.worker_process import run_worker

ROOT = Path(__file__).resolve().parents[2]
PATH = '/v1/feedback'
BODY_SECONDS = 2
WORKER_SECONDS = 15
SLOTS = 2


async def respond(send, status, value):
    raw = json.dumps(value, separators=(',', ':'), allow_nan=False).encode('ascii')
    await send({'type': 'http.response.start', 'status': status, 'headers': [
        (b'content-type', b'application/json'), (b'content-length', str(len(raw)).encode()),
        (b'cache-control', b'no-store'), (b'x-content-type-options', b'nosniff'),
        (b'connection', b'close')]})
    await send({'type': 'http.response.body', 'body': raw})


def result(raw, operation):
    """Never forward a worker's arbitrary output to an HTTP caller."""
    value = json.loads(raw.decode('utf-8', 'strict'), object_pairs_hook=unique,
                       parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
    expected = {'pass', 'synthetic_only', 'operation'} | (
        {'feedback_id'} if operation == 'submit' else {'removed'})
    if (type(value) is not dict or set(value) != expected or value['pass'] is not True
            or value['synthetic_only'] is not True or value['operation'] != operation):
        raise ValueError('Worker result refused')
    if operation == 'submit':
        identity = value['feedback_id']
        if type(identity) is not str:
            raise ValueError('Worker identity refused')
        parsed = uuid.UUID(identity)
        if str(parsed) != identity or parsed.version != 4 or parsed.variant != uuid.RFC_4122:
            raise ValueError('Worker identity refused')
    elif type(value['removed']) is not bool:
        raise ValueError('Worker result refused')
    return value


class ResearchTransport:
    def __init__(self):
        # The installed entry point is permanently disabled; no env activation.
        self.worker = None
        self.host = None
        self.authorization = None
        self.active = 0

    async def __call__(self, scope, receive, send):
        if scope['type'] == 'lifespan':
            while True:
                message = await receive()
                if message['type'] == 'lifespan.startup':
                    await send({'type': 'lifespan.startup.complete'})
                elif message['type'] == 'lifespan.shutdown':
                    await send({'type': 'lifespan.shutdown.complete'})
                    return
        if scope['type'] != 'http':
            if scope['type'] == 'websocket':
                await send({'type': 'websocket.close', 'code': 1008})
            return
        if scope.get('path') != PATH or scope.get('raw_path', PATH.encode()) != PATH.encode():
            return await respond(send, 404, {'state': 'Unsupported'})
        if scope.get('method') != 'POST':
            return await respond(send, 405, {'state': 'Unsupported'})
        if self.worker is None:
            return await respond(send, 503, {'state': 'Unavailable', 'collection_enabled': False})
        try:
            length = self.admit(scope)
        except (ValueError, TypeError, KeyError, UnicodeError):
            return await respond(send, 400, {'state': 'Refused', 'synthetic_only': True})
        if self.active >= SLOTS:
            return await respond(send, 503, {'state': 'Busy', 'synthetic_only': True})
        self.active += 1
        handed_to_worker = False
        try:
            try:
                raw = await asyncio.wait_for(self.body(receive, length), BODY_SECONDS)
                request = parse(raw)
            except (ValueError, TypeError, KeyError, asyncio.TimeoutError):
                return await respond(send, 400, {'state': 'Refused', 'synthetic_only': True})
            job = asyncio.create_task(asyncio.to_thread(self.worker, raw))
            # Cancellation cannot release capacity ahead of an outstanding worker.
            # Retrieve exceptions even if the HTTP handler has disconnected.
            def finished(task):
                self.active -= 1
                if not task.cancelled():
                    task.exception()
            job.add_done_callback(finished)
            handed_to_worker = True
            try:
                completed = await asyncio.shield(job)
                value = result(completed, request['operation'])
            except asyncio.CancelledError:
                raise
            except Exception:
                return await respond(send, 503, {'state': 'Unavailable', 'synthetic_only': True})
            return await respond(send, 200, value)
        finally:
            if not handed_to_worker:
                self.active -= 1

    def admit(self, scope):
        if scope.get('query_string', b'') or scope.get('scheme') != 'http':
            raise ValueError('Development transport refused')
        client = scope.get('client')
        if not client or not ipaddress.ip_address(client[0]).is_loopback:
            raise ValueError('Direct loopback required')
        fields = {}
        headers = scope.get('headers', [])
        if len(headers) > 16:
            raise ValueError('Header count limit')
        for key, value in headers:
            if (type(key) is not bytes or type(value) is not bytes or key in fields
                    or len(key) > 64 or len(value) > 512):
                raise ValueError('Ambiguous headers')
            fields[key] = value
        # No proxy/cookie/content-encoding or chunked ambiguity. A fixed small set
        # also prevents new metadata/identity headers from silently being used.
        allowed = {b'host', b'authorization', b'content-type', b'content-length',
                   b'connection', b'accept', b'user-agent', b'accept-encoding'}
        if not set(fields) <= allowed or fields.get(b'host') != self.host:
            raise ValueError('Unsupported transport')
        if not hmac.compare_digest(fields.get(b'authorization', b''), self.authorization):
            raise ValueError('Capability refused')
        if fields.get(b'content-type') != b'application/json':
            raise ValueError('JSON framing required')
        if fields.get(b'accept-encoding', b'identity') != b'identity':
            raise ValueError('Response encoding refused')
        raw_length = fields.get(b'content-length', b'')
        if not raw_length.isdigit() or len(raw_length) > 4 or raw_length.startswith(b'0'):
            raise ValueError('Invalid length')
        length = int(raw_length)
        if not 0 < length <= MAX_BYTES:
            raise ValueError('Body limit')
        return length

    @staticmethod
    async def body(receive, length):
        raw = bytearray()
        for _ in range(64):
            message = await receive()
            if message.get('type') != 'http.request' or type(message.get('body', b'')) is not bytes:
                raise ValueError('Request disconnected')
            chunk = message.get('body', b'')
            if len(chunk) > length - len(raw):
                raise ValueError('Body limit')
            raw.extend(chunk)
            if not message.get('more_body', False):
                if len(raw) != length:
                    raise ValueError('Framing mismatch')
                return bytes(raw)
        raise ValueError('Fragment limit')


def development_app(sandbox_dir, capability, host):
    """Explicit synthetic fixture only; no production path or credential lookup."""
    # Validate every immutable argument before constructing or invoking a worker.
    digest_token(capability)
    import re
    if type(host) is not str or not re.fullmatch(r'127\.0\.0\.1:[1-9][0-9]{0,4}', host):
        raise ValueError('Exact loopback host required')
    if not 0 < int(host.rsplit(':', 1)[1]) < 65536:
        raise ValueError('Port refused')
    import importlib.util
    spec = importlib.util.spec_from_file_location('research_sandbox_guard', ROOT/'scripts/verify-metadata-store.py')
    guard = importlib.util.module_from_spec(spec); spec.loader.exec_module(guard)
    directory = guard.sandbox(sandbox_dir)
    def execute(raw):
        completed = run_worker([sys.executable, '-B', str(ROOT/'services/research/worker.py'),
                                '--sandbox-dir', str(directory)],
                               input=raw, timeout=WORKER_SECONDS, output_limit=2048)
        if completed.returncode != 0:
            raise ValueError('Synthetic worker refused')
        return completed.stdout
    app = ResearchTransport()
    app.worker = execute
    app.host = host.encode('ascii')
    app.authorization = ('Bearer ' + capability).encode('ascii')
    return app


app = ResearchTransport()
