"""Synthetic ASGI boundaries, cancellation and actual disabled HTTP entry point."""
import asyncio
import base64
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request

import pytest
from services.research import app as module
from tools.research_admission import PROFILE, FIXED, CHOICES

ROOT = Path(__file__).resolve().parents[1]
TOKEN = base64.urlsafe_b64encode(bytes([17])*32).decode().rstrip('=')
ID = 'a161b589-8a25-470f-bc1d-3d78d5786c0a'


def request():
    return json.dumps({'format': PROFILE, 'synthetic': True, 'operation': 'submit',
        'invitation_token': base64.urlsafe_b64encode(bytes([1])*32).decode().rstrip('='),
        'withdrawal_token': base64.urlsafe_b64encode(bytes([2])*32).decode().rstrip('='),
        'feedback': {**FIXED, **{key: values[0] for key, values in CHOICES.items()}}}).encode()


def success(_raw):
    return json.dumps({'pass': True, 'synthetic_only': True, 'operation': 'submit', 'feedback_id': ID}).encode()


def development(worker=success):
    # Test-double transport; real sandbox construction is tested separately.
    app = module.ResearchTransport(); app.worker = worker
    app.host = b'127.0.0.1:12345'; app.authorization = ('Bearer '+TOKEN).encode()
    return app


def scope(raw=None):
    raw = request() if raw is None else raw
    return {'type': 'http', 'method': 'POST', 'path': '/v1/feedback',
        'raw_path': b'/v1/feedback', 'scheme': 'http', 'query_string': b'',
        'client': ('127.0.0.1', 1234), 'headers': [(b'host', b'127.0.0.1:12345'),
        (b'authorization', ('Bearer '+TOKEN).encode()), (b'content-type', b'application/json'),
        (b'content-length', str(len(raw)).encode())]}


async def call(app, selected=None, raw=None, receiver=None):
    raw = request() if raw is None else raw
    sent = []; read = []
    async def receive():
        read.append(True)
        return {'type': 'http.request', 'body': raw}
    async def send(value): sent.append(value)
    await app(scope(raw) if selected is None else selected, receiver or receive, send)
    return sent[0]['status'], json.loads(sent[1]['body']), sent[0]['headers'], read


def run(*args, **kwargs): return asyncio.run(call(*args, **kwargs))


def test_default_entry_point_does_not_read_body_or_inspect_environment(monkeypatch):
    monkeypatch.setenv('AITRUST_RESEARCH_ENABLED', 'true')
    monkeypatch.setenv('AITRUST_TOKEN', TOKEN)
    status, row, headers, read = run(module.app)
    assert status == 503 and row == {'state': 'Unavailable', 'collection_enabled': False}
    assert not read and dict(headers)[b'cache-control'] == b'no-store'


@pytest.mark.parametrize('mutation', ['auth', 'duplicate-auth', 'duplicate-length', 'length-zero',
    'length-too-big', 'length-leading-zero', 'transfer', 'encoding', 'cookie', 'origin',
    'forwarded', 'wrong-host', 'nonlocal', 'query', 'content-type', 'https', 'unknown-header'])
def test_header_and_transport_refusals_happen_before_read_or_worker(mutation):
    s = scope(); headers = dict(s['headers'])
    if mutation == 'auth': headers[b'authorization'] = b'Bearer PRIVATE_CANARY'
    if mutation == 'duplicate-auth': s['headers'].append(s['headers'][1])
    elif mutation == 'duplicate-length': s['headers'].append(s['headers'][-1])
    elif mutation == 'length-zero': headers[b'content-length'] = b'0'
    elif mutation == 'length-too-big': headers[b'content-length'] = b'4097'
    elif mutation == 'length-leading-zero': headers[b'content-length'] = b'0123'
    elif mutation == 'transfer': headers[b'transfer-encoding'] = b'chunked'
    elif mutation == 'encoding': headers[b'content-encoding'] = b'gzip'
    elif mutation == 'cookie': headers[b'cookie'] = b'PRIVATE_CANARY'
    elif mutation == 'origin': headers[b'origin'] = b'https://example.test'
    elif mutation == 'forwarded': headers[b'x-forwarded-for'] = b'127.0.0.1'
    elif mutation == 'wrong-host': headers[b'host'] = b'example.test'
    elif mutation == 'nonlocal': s['client'] = ('203.0.113.1', 1234)
    elif mutation == 'query': s['query_string'] = b'token=PRIVATE_CANARY'
    elif mutation == 'content-type': headers[b'content-type'] = b'text/plain'
    elif mutation == 'https': s['scheme'] = 'https'
    elif mutation == 'unknown-header': headers[b'private-identity'] = b'PRIVATE_CANARY'
    if not mutation.startswith('duplicate-'): s['headers'] = list(headers.items())
    status, row, _, read = run(development(lambda _: pytest.fail('Forbidden worker')), s)
    assert status == 400 and not read and 'PRIVATE_CANARY' not in json.dumps(row)


@pytest.mark.parametrize('raw', [b'{', b'null', b'{"text":"PRIVATE_CANARY"}', b'\xff',
    b'{"format":1,"format":2}', b'{"number":NaN}'])
def test_invalid_payloads_refuse_without_worker_or_echo(raw):
    status, row, _, _ = run(development(lambda _: pytest.fail('Forbidden worker')), raw=raw)
    assert status == 400 and 'PRIVATE_CANARY' not in json.dumps(row)


@pytest.mark.parametrize('path,method,status', [('/other','POST',404),('/v1/feedback','GET',405),
    ('/v1/feedback','OPTIONS',405),('/v1/feedback/','POST',404)])
def test_only_the_approved_exact_route_exists(path, method, status):
    s = scope(); s.update(path=path, raw_path=path.encode(), method=method)
    observed = run(development(lambda _: pytest.fail('Forbidden worker')), s)
    assert observed[0] == status and not observed[3]


def test_exact_success_has_no_input_tokens_or_paths():
    status, row, headers, read = run(development())
    assert status == 200 and row['feedback_id'] == ID and read
    assert TOKEN not in json.dumps(row) and 'invitation_token' not in row
    assert dict(headers)[b'connection'] == b'close'
    assert dict(headers)[b'x-content-type-options'] == b'nosniff'


@pytest.mark.parametrize('output', [b'{}', b'null', b'PRIVATE_CANARY',
    json.dumps({'pass': True,'synthetic_only':True,'operation':'submit','feedback_id':'wrong'}).encode(),
    json.dumps({'pass': True,'synthetic_only':True,'operation':'submit','feedback_id':ID,'text':'PRIVATE_CANARY'}).encode(),
    json.dumps({'pass': True,'synthetic_only':True,'operation':'withdraw','removed':True}).encode()])
def test_worker_results_are_checked_and_not_forwarded(output):
    app = development(lambda _: output)
    assert run(app)[0] == 503 and app.active == 0


def test_worker_exception_releases_slot_without_traceback_then_recovers():
    def fail(_): raise RuntimeError('PRIVATE_CANARY')
    app = development(fail); status, row, _, _ = run(app)
    assert status == 503 and 'PRIVATE_CANARY' not in json.dumps(row) and app.active == 0
    app.worker = success; assert run(app)[0] == 200


def test_stream_disconnect_length_mismatch_oversize_and_fragment_limits():
    async def checks():
        for message in ({'type':'http.disconnect'}, {'type':'http.request','body':b'x'},
                        {'type':'http.request','body':request()+b'x'},
                        {'type':'http.request','body':b'','more_body':True}):
            async def receive(): return message
            app = development(lambda _: pytest.fail('Forbidden worker'))
            assert (await call(app,receiver=receive))[0] == 400 and app.active == 0
    asyncio.run(checks())


def test_whole_body_deadline_releases_slot(monkeypatch):
    monkeypatch.setattr(module, 'BODY_SECONDS', .02)
    async def checks():
        async def receive(): await asyncio.sleep(1)
        app = development(lambda _: pytest.fail('Forbidden worker'))
        assert (await call(app,receiver=receive))[0] == 400 and app.active == 0
    asyncio.run(checks())


def test_saturation_and_handler_cancellation_do_not_refund_running_workers():
    started = threading.Event(); release = threading.Event(); lock = threading.Lock(); count = 0
    def worker(raw):
        nonlocal count
        with lock:
            count += 1
            if count == 2: started.set()
        assert release.wait(5)
        return success(raw)
    async def checks():
        app = development(worker)
        tasks = [asyncio.create_task(call(app)) for _ in range(2)]
        try:
            assert await asyncio.to_thread(started.wait, 3)
            checked = await asyncio.to_thread(subprocess.run,
                [sys.executable, str(ROOT/'scripts/check-ps.py')],
                input=b'An ordinary invented sentence.', capture_output=True, timeout=15)
            assert checked.returncode == 0 and checked.stdout.startswith(b'PS: no supported command pattern found.\n')
            assert app.active == 2
            tasks[0].cancel()
            with pytest.raises(asyncio.CancelledError): await tasks[0]
            assert app.active == 2
            status, _, _, read = await call(app)
            assert status == 503 and not read
        finally: release.set()
        assert (await tasks[1])[0] == 200
        for _ in range(100):
            if app.active == 0: break
            await asyncio.sleep(.01)
        assert app.active == 0 and (await call(app))[0] == 200
    asyncio.run(checks())


def test_unsafe_development_database_or_capability_is_refused_before_worker():
    for directory, capability, host in [('/',TOKEN,'127.0.0.1:12345'),
        ('/tmp',TOKEN,'127.0.0.1:12345'),('/tmp', 'wrong','127.0.0.1:12345'),
        ('/tmp',TOKEN,'example.test:12345'),('/tmp',TOKEN,'127.0.0.1:65536')]:
        with pytest.raises((ValueError, OSError)):
            module.development_app(directory, capability, host)


def test_actual_uvicorn_disabled_service_never_enables_intake():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1',0)); port = sock.getsockname()[1]
    environment = {**os.environ,'PYTHONPATH':str(ROOT),'AITRUST_RESEARCH_ENABLED':'true'}
    worker = subprocess.Popen([sys.executable,'-m','uvicorn','services.research.app:app',
        '--host','127.0.0.1','--port',str(port),'--no-access-log','--no-proxy-headers',
        '--log-level','critical'], cwd=ROOT, env=environment,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        deadline = time.monotonic()+8
        while True:
            try:
                req = urllib.request.Request('http://127.0.0.1:'+str(port)+'/v1/feedback',
                    data=b'PRIVATE_HTTP_CANARY',headers={'Content-Type':'application/json'})
                opener.open(req,timeout=2)
                pytest.fail('Disabled service accepted a request')
            except urllib.error.HTTPError as error:
                assert error.code == 503
                assert json.loads(error.read()) == {'state':'Unavailable','collection_enabled':False}
                assert error.headers['Cache-Control'] == 'no-store'; break
            except OSError:
                assert worker.poll() is None and time.monotonic()<deadline
                time.sleep(.05)
    finally:
        worker.terminate()
        try: out, err = worker.communicate(timeout=5)
        except subprocess.TimeoutExpired: worker.kill(); out, err = worker.communicate(timeout=5)
    assert b'PRIVATE_HTTP_CANARY' not in out+err and not out and not err


@pytest.mark.parametrize('raw', [b'{', b'null', b'PRIVATE_WORKER_CANARY', b'x'*4097])
def test_actual_worker_refuses_invalid_stdin_without_echo_or_database_access(raw):
    checked = subprocess.run([sys.executable,str(ROOT/'services/research/worker.py'),
        '--sandbox-dir','/unavailable/PRIVATE_WORKER_CANARY'],input=raw,
        capture_output=True,timeout=8)
    assert checked.returncode == 1 and not checked.stdout and not checked.stderr


def test_actual_worker_argument_errors_do_not_reflect_private_paths():
    checked = subprocess.run([sys.executable,str(ROOT/'services/research/worker.py'),
        '--PRIVATE_WORKER_CANARY'],capture_output=True,timeout=8)
    assert checked.returncode == 2 and not checked.stdout
    assert checked.stderr == b'Synthetic worker arguments refused.\n'
