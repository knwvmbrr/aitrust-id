"""Actual FastAPI/HTTPX flow; generated review users, no provider or paid-charge claim."""
import asyncio
from pathlib import Path
import tempfile
import threading
import unittest
import uuid
from unittest import mock

import httpx
from services.accounts import app as api
from tools import account_core as c
from tools.account_store import initialize

NOW = 1800000000
ORIGIN = 'http://127.0.0.1:8791'
PASSWORD = 'a public synthetic passphrase only'


def record():
    return {'event_id': str(uuid.uuid4()), 'displayed_at': NOW, 'adapter': 'summary-import',
            'tag': 'PS', 'state': 'FINDING',
            'method': {'name': 'rules-only', 'revision': 'context-v6', 'sha256': 'a' * 64}}


class AccountAPITests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=Path(tempfile.gettempdir()).resolve())
        self.store = initialize(Path(self.temp.name) / 'accounts')
        self.now = NOW
        self.grants = {}
        self.engine_failed = False
        self.assessed = []
        def assess(owner, now):
            self.assessed.append(owner)
            if self.engine_failed:
                raise OSError('PRIVATE_ENGINE_ERROR')
            end = self.grants.get(owner)
            return {'format': 'account-history-entitlement/v1', 'account_id': owner,
                    'state': 'ACTIVE' if end is not None and now < end else 'INACTIVE',
                    'valid_until': end, 'revision': 1 if end else 0}
        self.app = api.create_app(self.store, origin=ORIGIN, host='127.0.0.1:8791',
                                  entitlement=assess, secure_cookie=False, clock=lambda: self.now)
        self.clients = []
        self.csrf = {}

    async def asyncTearDown(self):
        for client in self.clients:
            await client.aclose()
        self.temp.cleanup()

    def client(self):
        client = httpx.AsyncClient(transport=httpx.ASGITransport(app=self.app, client=('127.0.0.1', 50000)), base_url=ORIGIN)
        self.clients.append(client)
        return client

    async def call(self, client, method, path, data=None, *, headers=None):
        fields = {'Origin': ORIGIN}
        if method != 'GET':
            fields['X-CSRF-Token'] = self.csrf.get(id(client), '')
        fields.update(headers or {})
        response = await client.request(method, '/v1/account' + path, json=data, headers=fields)
        value = response.json()
        if 'csrf_token' in value:
            self.csrf[id(client)] = value['csrf_token'] or ''
        return response

    async def signup(self, name):
        client = self.client()
        initial = await self.call(client, 'GET', '/session')
        self.assertEqual(initial.status_code, 200)
        bootstrap = client.cookies.get(api.COOKIE)
        created = await self.call(client, 'POST', '/signup', {'username': name, 'password': PASSWORD})
        self.assertEqual(created.status_code, 201, created.text)
        self.assertNotEqual(client.cookies.get(api.COOKIE), bootstrap)
        self.assertTrue(created.json()['authenticated'])
        return client, created.json()['account']['id']

    async def test_actual_two_user_signup_history_export_expiry_and_account_removal(self):
        alice, alice_id = await self.signup('api-alice')
        bob, bob_id = await self.signup('api-bob')
        self.assertNotEqual(alice_id, bob_id)
        denied = await self.call(alice, 'POST', '/history', {'operation': 'enable', 'acknowledge_metadata': True})
        self.assertEqual(denied.status_code, 403)
        self.grants[alice_id] = NOW + 5
        self.assertEqual((await self.call(alice, 'POST', '/history', {'operation': 'enable', 'acknowledge_metadata': True})).status_code, 200)
        item = record()
        saved = await self.call(alice, 'POST', '/history', {'operation': 'append', 'record': item})
        self.assertEqual(saved.status_code, 200, saved.text)
        self.assertFalse(saved.json()['verified_assertion'])
        self.assertEqual((await self.call(bob, 'GET', '/history')).json()['items'], [])
        self.assertEqual((await self.call(bob, 'DELETE', '/history/' + item['event_id'])).status_code, 404)
        self.now += 6
        self.engine_failed = True
        self.assessed.clear()
        exported = await self.call(alice, 'GET', '/history/export')
        self.assertEqual(exported.status_code, 200)
        self.assertEqual(exported.json()['items'], [saved.json()])
        self.assertIn('attachment;', exported.headers['content-disposition'])
        deleted = await self.call(alice, 'DELETE', '/history/' + item['event_id'])
        self.assertEqual(deleted.status_code, 200)
        self.assertEqual(self.assessed, [])
        removed = await self.call(alice, 'DELETE', '', {'password': PASSWORD})
        self.assertEqual(removed.status_code, 200)
        self.assertEqual(removed.json()['entitlement_cleanup'], 'PENDING')
        self.assertNotIn('_cleanup_account_id', removed.json())
        self.assertEqual((await self.call(alice, 'GET', '/history')).status_code, 401)
        self.assertEqual((await self.call(bob, 'GET', '/history')).status_code, 200)

    async def test_history_result_filter_is_closed_and_export_remains_complete(self):
        client, owner = await self.signup('api-filter')
        self.grants[owner] = NOW + 100
        self.assertEqual((await self.call(client, 'POST', '/history', {'operation': 'enable', 'acknowledge_metadata': True})).status_code, 200)
        for state in ('FINDING', 'NO_FINDING'):
            item = record()
            item['state'] = state
            self.assertEqual((await self.call(client, 'POST', '/history', {'operation': 'append', 'record': item})).status_code, 200)
        response = await self.call(client, 'GET', '/history?state=NO_FINDING&limit=1')
        self.assertEqual(response.status_code, 200)
        value = response.json()
        self.assertEqual((value['total_entries'], value['matching_entries']), (2, 1))
        self.assertEqual([r['state'] for r in value['items']], ['NO_FINDING'])
        for query in ('state=UNKNOWN', 'state=FINDING&state=NO_FINDING', 'state=', 'role=admin'):
            self.assertEqual((await self.call(client, 'GET', '/history?' + query)).status_code, 400)
        self.engine_failed = True
        exported = await self.call(client, 'GET', '/history/export')
        self.assertEqual(exported.status_code, 200)
        self.assertEqual(len(exported.json()['items']), 2)

    async def test_optional_read_binding_refuses_cross_tab_principal_swap(self):
        alice, _ = await self.signup('tab-alice')
        bob, _ = await self.signup('tab-bob')
        alice_binding = self.csrf[id(alice)]
        bob_binding = self.csrf[id(bob)]
        self.assertNotEqual(alice_binding, bob_binding)
        for endpoint in ('/history', '/history/export', '/entitlements'):
            response = await self.call(bob, 'GET', endpoint, headers={'X-CSRF-Token': alice_binding})
            self.assertEqual(response.status_code, 403)
            self.assertEqual(response.json()['reason'], 'csrf_refused')
            self.assertNotIn('items', response.json())
            valid = await self.call(bob, 'GET', endpoint, headers={'X-CSRF-Token': bob_binding})
            self.assertEqual(valid.status_code, 200)
        self.assertEqual((await self.call(bob, 'GET', '/history')).status_code, 200)

    async def test_csrf_origin_installation_token_and_mass_assignment_refuse(self):
        client, owner = await self.signup('api-guard')
        for headers in ({'X-CSRF-Token': '0' * 64}, {'Origin': 'https://other.invalid'}, {'X-CSRF-Token': 'é' * 64}):
            # HTTP headers are ASCII on the wire; use a plain malformed token here.
            if 'é' in headers.get('X-CSRF-Token', ''):
                headers = {'X-CSRF-Token': 'z' * 64}
            response = await self.call(client, 'DELETE', '/history', headers=headers)
            self.assertEqual(response.status_code, 403)
        response = await self.call(client, 'POST', '/history', {'operation': 'enable', 'acknowledge_metadata': True, 'paid': True})
        self.assertEqual(response.status_code, 400)
        stranger = self.client()
        response = await stranger.get('/v1/account/history', headers={'Authorization': 'Bearer PUBLIC_INSTALLATION_TOKEN_FIXTURE'})
        self.assertEqual(response.status_code, 401)
        raw = await stranger.post('/v1/account/signup', content=b'{"username":"x","password":"PRIVATE_CANARY","role":"administrator"}', headers={'Origin': ORIGIN, 'Content-Type': 'application/json'})
        self.assertNotIn('PRIVATE_CANARY', raw.text)
        self.assertNotIn(PASSWORD, response.text)

    async def test_login_rotation_logout_and_secure_cookie_configuration(self):
        client, owner = await self.signup('api-login')
        old = client.cookies.get(api.COOKIE)
        logged_out = await self.call(client, 'DELETE', '/session')
        self.assertEqual(logged_out.status_code, 200)
        await self.call(client, 'GET', '/session')
        bootstrap = client.cookies.get(api.COOKIE)
        logged_in = await self.call(client, 'POST', '/sessions', {'username': 'api-login', 'password': PASSWORD})
        self.assertEqual(logged_in.status_code, 200)
        self.assertNotEqual(client.cookies.get(api.COOKIE), bootstrap)
        self.assertNotIn(client.cookies.get(api.COOKIE), logged_in.text)
        self.assertIn('HttpOnly', logged_in.headers['set-cookie'])
        self.assertIn('Path=/v1/account', logged_in.headers['set-cookie'])
        self.assertIn('SameSite=strict', logged_in.headers['set-cookie'])
        self.assertNotIn('Secure;', logged_in.headers['set-cookie'])
        stale = await self.call(client, 'GET', '/history', headers={'Cookie': api.COOKIE + '=' + old})
        self.assertEqual(stale.status_code, 401)
        with self.assertRaises(c.AccountError):
            api.create_app(self.store, origin='http://example.test', host='example.test', entitlement=lambda *_: {}, secure_cookie=False)

    async def test_bounded_wire_json_and_missing_fixed_asset_routes(self):
        client = self.client()
        oversized = await client.post('/v1/account/signup', content=b'x' * 16385, headers={'Origin': ORIGIN, 'Content-Type': 'application/json'})
        self.assertEqual(oversized.status_code, 413)
        foreign = await client.get('/v1/account/session', headers={'Host': 'other.invalid'})
        self.assertEqual(foreign.status_code, 403)
        with tempfile.TemporaryDirectory(dir=Path(tempfile.gettempdir()).resolve()) as temporary:
            site = Path(temporary) / 'site/account'
            site.mkdir(parents=True)
            (site / 'index.html').write_text('<!doctype html><title>Review</title>')
            fixture = api.create_app(self.store, origin=ORIGIN, host='127.0.0.1:8791', entitlement=lambda *_: {},
                                     secure_cookie=False, asset_directory=site)
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=fixture), base_url=ORIGIN) as static:
                page = await static.get('/account/')
                self.assertEqual(page.status_code, 200)
                self.assertEqual((await static.get('/account/app.js')).status_code, 404)
                self.assertEqual((await static.get('/account/unknown')).status_code, 404)
                self.assertEqual((await static.get('/account/../../accounts.sqlite')).status_code, 404)
            self.assertIn("script-src 'self'", page.headers['content-security-policy'])
            self.assertEqual(page.headers['cache-control'], 'no-store')
            self.assertEqual(page.headers['referrer-policy'], 'no-referrer')

    async def test_session_expiry_and_internal_clock_failure_are_explicit(self):
        client, owner = await self.signup('api-clock')
        self.now = NOW - 1
        refused = await self.call(client, 'GET', '/history')
        self.assertEqual(refused.status_code, 503)
        self.now = NOW + 86401
        expired = await self.call(client, 'GET', '/history')
        self.assertEqual(expired.status_code, 401)
        session = await self.call(client, 'GET', '/session')
        self.assertFalse(session.json()['authenticated'])

    async def test_cancelled_http_handler_keeps_owned_worker_capacity_until_finished(self):
        client, owner = await self.signup('api-cancel')
        release = threading.Event()
        started = []
        lock = threading.Lock()
        def blocked(*unused):
            with lock:
                started.append(True)
            if not release.wait(3):
                raise RuntimeError('fixture release timeout')
            return {'format': 'account-history-entitlement/v1', 'account_id': owner,
                    'state': 'INACTIVE', 'valid_until': None, 'revision': 0}
        tasks = []
        try:
            with mock.patch.object(self.store, 'entitlements', side_effect=blocked):
                first = asyncio.create_task(self.call(client, 'GET', '/entitlements'))
                tasks.append(first)
                for _ in range(100):
                    if len(started) == 1:
                        break
                    await asyncio.sleep(.005)
                self.assertEqual(len(started), 1)
                second = asyncio.create_task(self.call(client, 'GET', '/entitlements'))
                tasks.append(second)
                for _ in range(100):
                    if len(started) == 2:
                        break
                    await asyncio.sleep(.005)
                self.assertEqual(len(started), 2)
                first.cancel()
                with self.assertRaises(asyncio.CancelledError):
                    await first
                saturated = await self.call(client, 'GET', '/history')
                self.assertEqual(saturated.status_code, 503)
                self.assertEqual(saturated.json()['reason'], 'busy')
                release.set()
                self.assertEqual((await second).status_code, 200)
            for _ in range(100):
                response = await self.call(client, 'GET', '/history')
                if response.status_code == 200:
                    break
                await asyncio.sleep(.005)
            self.assertEqual(response.status_code, 200)
        finally:
            release.set()
            await asyncio.gather(*tasks, return_exceptions=True)

    async def test_monotonic_maintenance_interleave_succeeds_but_real_rollback_refuses(self):
        client, owner = await self.signup('clock-interleave')
        original = self.store.authenticate
        def advance_after_authentication(*args, **kwargs):
            result = original(*args, **kwargs)
            self.now += 1
            self.store.maintenance(self.now)
            return result
        with mock.patch.object(self.store, 'authenticate', side_effect=advance_after_authentication):
            result = await self.call(client, 'GET', '/history')
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json()['items'], [])
        committed = self.now
        for invalid in (committed - 1, float('nan')):
            self.now = invalid
            result = await self.call(client, 'GET', '/history')
            self.assertEqual(result.status_code, 503)
            self.assertEqual(result.json()['reason'], 'clock_unavailable')
        self.now = committed
        self.assertEqual((await self.call(client, 'GET', '/history')).status_code, 200)


if __name__ == '__main__':
    unittest.main()
