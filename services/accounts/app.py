"""Approved account routes using the existing FastAPI stack; no payment or tag calls."""
import asyncio
from contextlib import asynccontextmanager
import hmac
import ipaddress
from pathlib import Path
import re
import threading
import time
from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, FastAPI, Request
from fastapi.responses import JSONResponse, Response
from starlette.middleware.cors import CORSMiddleware

from tools import account_core as c
from tools.account_store import AccountStore, BOOTSTRAP_SECONDS, SESSION_SECONDS
from tools.artifact_evidence_io import Capture

ROOT = Path(__file__).absolute().parents[2]
COOKIE = 'aitrust_account_session'
PREFIX = '/v1/account'
SECURITY_HEADERS = {
    'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff',
    'X-Frame-Options': 'DENY', 'Referrer-Policy': 'no-referrer',
    'X-Robots-Tag': 'noindex, noarchive',
    'Content-Security-Policy': "default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'",
}


def error_response(error):
    return JSONResponse({'format': 'account-error/v1',
                         'state': 'UNAVAILABLE' if error.status >= 500 else 'REFUSED',
                         'reason': error.code}, status_code=error.status, headers=SECURITY_HEADERS)


def cookie(request):
    raw = request.headers.get('cookie', '')
    c.need(len(raw) <= 2048)
    values = {}
    if raw:
        for part in raw.split(';'):
            pair = part.strip().split('=', 1)
            c.need(len(values) < 16 and len(pair) == 2 and re.fullmatch('[A-Za-z0-9_-]{1,80}', pair[0]) is not None and pair[0] not in values)
            values[pair[0]] = pair[1]
    value = values.get(COOKIE)
    if value is not None:
        c.token_hash(value)
    return value


class Boundary:
    """Bound headers/body before framework parsing and never reflect private inputs."""
    def __init__(self, app, *, origin, host):
        self.app, self.origin, self.host = app, origin, host
        self.read_slots = threading.BoundedSemaphore(16)

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            return await self.app(scope, receive, send)
        reading = False
        try:
            headers = scope.get('headers', [])
            c.need(len(headers) <= 32 and sum(len(k) + len(v) for k, v in headers) <= 8192)
            fields = {}
            for key, value in headers:
                c.need(type(key) is bytes and type(value) is bytes and len(key) <= 64 and len(value) <= 2048)
                if key in (b'host', b'origin', b'cookie', b'content-length', b'content-type', b'x-csrf-token', b'sec-fetch-site'):
                    c.need(key not in fields)
                    fields[key] = value
            c.need(fields.get(b'host', b'').decode('ascii', 'strict') == self.host, 'host_refused', 403)
            supplied_origin = fields.get(b'origin')
            c.need(supplied_origin is None or supplied_origin.decode('ascii', 'strict') == self.origin, 'origin_refused', 403)
            c.need(fields.get(b'sec-fetch-site') in (None, b'same-origin', b'same-site', b'none'), 'origin_refused', 403)
            method = scope['method']
            if method in ('POST', 'DELETE'):
                c.need(supplied_origin is not None, 'origin_refused', 403)
            length = fields.get(b'content-length')
            if length is not None:
                c.need(re.fullmatch(rb'[0-9]{1,6}', length) is not None and int(length) <= 16_384, 'request_too_large', 413)
            if method == 'POST' or method == 'DELETE' and length not in (None, b'0'):
                c.need(fields.get(b'content-type') in (b'application/json', b'application/json; charset=utf-8'), 'invalid_request', 415)
            c.need(self.read_slots.acquire(blocking=False), 'busy', 503)
            reading = True
            raw = bytearray()
            deadline = time.monotonic() + 5
            for _ in range(64):
                left = deadline - time.monotonic()
                c.need(left > 0, 'request_timeout', 408)
                message = await asyncio.wait_for(receive(), left)
                c.need(message['type'] == 'http.request')
                data = message.get('body', b'')
                c.need(type(data) is bytes and len(raw) + len(data) <= 16_384, 'request_too_large', 413)
                raw.extend(data)
                if not message.get('more_body', False):
                    break
            else:
                raise c.AccountError('invalid_request', 400)
            c.need(length is None or int(length) == len(raw))
            c.need(method in ('POST', 'DELETE') or not raw)
        except (UnicodeError, ValueError, KeyError, TypeError, asyncio.TimeoutError) as error:
            fixed = error if isinstance(error, c.AccountError) else c.AccountError('invalid_request', 400)
            return await error_response(fixed)(scope, receive, send)
        finally:
            if reading:
                self.read_slots.release()
        delivered = False
        async def bounded_receive():
            nonlocal delivered
            if not delivered:
                delivered = True
                return {'type': 'http.request', 'body': bytes(raw), 'more_body': False}
            return {'type': 'http.disconnect'}
        async def safe_send(message):
            if message['type'] == 'http.response.start':
                protected = {k.lower().encode() for k in SECURITY_HEADERS}
                message = {**message, 'headers': [(k, v) for k, v in message.get('headers', []) if k.lower() not in protected]
                           + [(k.lower().encode(), v.encode()) for k, v in SECURITY_HEADERS.items()]}
            await send(message)
        return await self.app(scope, bounded_receive, safe_send)


def create_app(store: AccountStore, *, origin: str, host: str, entitlement,
               secure_cookie: bool = True, clock=lambda: int(time.time()), entitlement_forget=None,
               asset_directory=None):
    """Trusted server configuration only; callbacks are never selected by HTTP input."""
    selected = urlsplit(origin)
    c.need(selected.scheme in ('http', 'https') and selected.hostname is not None and not selected.username
           and not selected.password and not selected.path and not selected.query and not selected.fragment
           and selected.netloc == host and type(secure_cookie) is bool)
    if not secure_cookie:
        try:
            loopback = ipaddress.ip_address(selected.hostname).is_loopback
        except ValueError:
            loopback = False
        c.need(selected.scheme == 'http' and loopback)
    else:
        c.need(selected.scheme == 'https')
    c.need(callable(entitlement) and callable(clock))
    assets = ROOT / 'site/account' if asset_directory is None else Path(asset_directory).absolute()
    slots = threading.BoundedSemaphore(2)
    @asynccontextmanager
    async def lifetime(application):
        stop = asyncio.Event()
        await work(store.maintenance, clock)
        async def expire():
            while not stop.is_set():
                try:
                    await asyncio.wait_for(stop.wait(), 60)
                except asyncio.TimeoutError:
                    try:
                        await work(store.maintenance, clock)
                        application.state.expiry_maintenance_available = True
                    except Exception:
                        application.state.expiry_maintenance_available = False
        task = asyncio.create_task(expire())
        try:
            yield
        finally:
            stop.set()
            await task
    app = FastAPI(debug=False, docs_url=None, redoc_url=None, openapi_url=None,
                  redirect_slashes=False, lifespan=lifetime)

    async def work(function, *args, **kwargs):
        c.need(slots.acquire(blocking=False), 'busy', 503)
        coroutine = asyncio.to_thread(function, *args, **kwargs)
        try:
            task = asyncio.create_task(coroutine)
        except BaseException:
            coroutine.close()
            slots.release()
            raise
        def done(finished):
            slots.release()
            if not finished.cancelled():
                finished.exception()
        task.add_done_callback(done)
        try:
            return await asyncio.wait_for(asyncio.shield(task), 10)
        except asyncio.TimeoutError:
            raise c.AccountError('operation_unavailable', 503) from None
        except c.AccountError:
            raise
        except Exception:
            raise c.AccountError('unavailable', 503) from None

    def context(request):
        if not hasattr(request.state, 'account_context'):
            peer = request.client.host if request.client is not None else 'unknown-peer'
            c.need(type(peer) is str and 0 < len(peer) <= 128)
            request.state.account_context = (cookie(request), clock, peer)
        return request.state.account_context

    async def check(request, authenticated):
        value, now, peer = context(request)
        c.need(value is not None, 'authentication_required', 401)
        if request.method != 'GET' or 'x-csrf-token' in request.headers:
            supplied = request.headers.get('x-csrf-token', '')
            c.need(re.fullmatch('[a-f0-9]{64}', supplied) is not None
                   and hmac.compare_digest(supplied, c.csrf(value)), 'csrf_refused', 403)
        await work(store.authenticate, value, now, authenticated)
        return value, now, peer

    async def bootstrap(request: Request):
        return await check(request, False)

    async def authenticated(request: Request):
        return await check(request, True)

    async def body(request, fields):
        raw = await request.body()
        value = c.parse(raw) if raw else {}
        c.need(set(value) == set(fields))
        return value

    def session_response(public, value, status=200):
        response = JSONResponse(public, status_code=status)
        response.set_cookie(COOKIE, value, max_age=SESSION_SECONDS if public['authenticated'] else BOOTSTRAP_SECONDS,
                            httponly=True, secure=secure_cookie, samesite='strict', path=PREFIX)
        return response

    @app.exception_handler(c.AccountError)
    async def refused(request, error):
        return error_response(error)

    @app.exception_handler(Exception)
    async def unavailable(request, error):
        return error_response(c.AccountError('unavailable', 503))

    @app.get(PREFIX + '/session')
    async def session(request: Request):
        value, now, peer = context(request)
        public, value = await work(store.session, value, now, peer)
        return session_response(public, value)

    @app.post(PREFIX + '/signup', status_code=201)
    async def signup(request: Request, selected=Depends(bootstrap)):
        data = await body(request, ('username', 'password'))
        value, now, peer = selected
        public, new = await work(store.signup, data['username'], data['password'], value, now, peer)
        return session_response(public, new, 201)

    @app.post(PREFIX + '/sessions')
    async def login(request: Request, selected=Depends(bootstrap)):
        data = await body(request, ('username', 'password'))
        value, now, peer = selected
        public, new = await work(store.login, data['username'], data['password'], value, now, peer)
        return session_response(public, new)

    @app.delete(PREFIX + '/session')
    async def logout(request: Request, selected=Depends(bootstrap)):
        await body(request, ())
        result = await work(store.logout, selected[0], selected[1])
        response = JSONResponse(result)
        response.delete_cookie(COOKIE, path=PREFIX, httponly=True, secure=secure_cookie, samesite='strict')
        return response

    private = APIRouter(prefix=PREFIX, dependencies=[Depends(authenticated)])

    @private.get('/entitlements')
    async def entitlements(request: Request):
        value, now, _ = context(request)
        return await work(store.entitlements, value, now, entitlement)

    @private.get('/history')
    async def history(request: Request):
        query = request.query_params
        c.need(set(query) <= {'after', 'limit', 'state'} and len(query.multi_items()) == len(query))
        limit = query.get('limit', '50')
        c.need(re.fullmatch('[1-9][0-9]?', limit) is not None)
        value, now, _ = context(request)
        return await work(store.history_list, value, now, after=query.get('after'), limit=int(limit), state=query.get('state'))

    @private.get('/history/export')
    async def export(request: Request):
        c.need(not request.query_params)
        value, now, _ = context(request)
        result = await work(store.history_list, value, now, export=True)
        return JSONResponse(result, headers={'Content-Disposition': 'attachment; filename="ai-trust-id-history.json"'})

    @private.post('/history')
    async def change_history(request: Request):
        data = c.parse(await request.body())
        operation = data.get('operation')
        fields = {'enable': {'operation', 'acknowledge_metadata'}, 'disable': {'operation'}, 'append': {'operation', 'record'}}
        c.need(type(operation) is str and operation in fields and set(data) == fields[operation])
        value, now, _ = context(request)
        return await work(store.history_change, value, now, operation, entitlement,
                          record=data.get('record'), acknowledge=data.get('acknowledge_metadata', False))

    @private.delete('/history')
    async def delete_history(request: Request):
        await body(request, ())
        value, now, _ = context(request)
        return await work(store.history_delete, value, now)

    @private.delete('/history/{event_id}')
    async def delete_event(event_id: str, request: Request):
        await body(request, ())
        value, now, _ = context(request)
        return await work(store.history_delete, value, now, event_id)

    @private.delete('')
    async def delete_account(request: Request):
        data = await body(request, ('password',))
        value, now, _ = context(request)
        result = await work(store.delete_account, value, data['password'], now)
        account_id = result.pop('_cleanup_account_id')
        try:
            complete = await work(store.finish_cleanup, account_id, entitlement_forget, now)
        except Exception:
            complete = False  # Account data is already gone; durable cleanup remains pending.
        result['entitlement_cleanup'] = 'COMPLETE' if complete else 'PENDING'
        result['cleanup_pending'] = not complete
        response = JSONResponse(result)
        response.delete_cookie(COOKIE, path=PREFIX, httponly=True, secure=secure_cookie, samesite='strict')
        return response

    app.include_router(private)

    def asset(name, media_type, cap):
        try:
            with Capture() as capture:
                raw = capture.read(assets / name, cap, private=False)
                capture.check()
            return Response(raw, media_type=media_type)
        except (OSError, ValueError):
            raise c.AccountError('not_found', 404) from None

    @app.get('/account/')
    async def page():
        return await work(asset, 'index.html', 'text/html', 65536)

    @app.get('/account/app.js')
    async def script():
        return await work(asset, 'app.js', 'application/javascript', 262144)

    @app.get('/account/style.css')
    async def style():
        return await work(asset, 'style.css', 'text/css', 65536)

    app.add_middleware(CORSMiddleware, allow_origins=[origin], allow_credentials=True,
                       allow_methods=['GET', 'POST', 'DELETE'], allow_headers=['Content-Type', 'X-CSRF-Token'])
    app.add_middleware(Boundary, origin=origin, host=host)
    return app
