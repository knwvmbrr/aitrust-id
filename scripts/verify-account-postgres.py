#!/usr/bin/env python3
"""Actual isolated PostgreSQL/domain/approved HTTP workflow; synthetic accounts only."""
import argparse
import hashlib
import http.cookiejar
import json
import os
from pathlib import Path
import secrets
import signal
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools import account_core as c
from tools import account_postgres as pg
from tools.history_entitlements import initialize as initialize_access, HistoryEntitlements

PASSWORD = 'synthetic-review-only-passphrase-2026'
ORIGIN = 'http://127.0.0.1:18791'


def need(value):
    if not value: raise AssertionError('Synthetic PostgreSQL review failed.')


class Browser:
    def __init__(self):
        self.jar = http.cookiejar.CookieJar()
        self.client = urllib.request.build_opener(urllib.request.ProxyHandler({}), urllib.request.HTTPCookieProcessor(self.jar))
        self.csrf = None

    def call(self, method, path, value=None, code=200, headers=None):
        fields = {'Origin': ORIGIN}
        if self.csrf is not None and method != 'GET': fields['X-CSRF-Token'] = self.csrf
        if value is not None: fields['Content-Type'] = 'application/json'
        if headers: fields.update(headers)
        request = urllib.request.Request(ORIGIN + path, data=None if value is None else c.encode(value), headers=fields, method=method)
        try: response = self.client.open(request, timeout=15)
        except urllib.error.HTTPError as error: response = error
        with response:
            need(response.code == code and response.headers.get('Cache-Control') == 'no-store')
            need(response.headers.get('X-Content-Type-Options') == 'nosniff')
            raw = response.read(6_000_001); need(len(raw) <= 6_000_000)
            result = json.loads(raw)
            if 'csrf_token' in result: self.csrf = result['csrf_token']
            return result


def recovery(profile, work, mode):
    store = pg.PostgresAccountStore(profile)
    fixture_path = work / 'runtime/recovery-fixture.json'
    fixture = json.loads(fixture_path.read_text())
    now = lambda: int(time.time())
    cases = []
    if mode == 'seed':
        from tools.history_entitlements import HistoryEntitlements
        access = HistoryEntitlements(work / 'runtime/entitlements', clock=now)
        access.grant(fixture['account_id'], str(uuid.uuid4()), now() + 600, now())
        public, token = store.session(None, now, 'synthetic-restore-seed')
        public, token = store.login(fixture['username'], PASSWORD, token, now, 'synthetic-restore-seed')
        store.history_change(token, now, 'enable', access.assess, acknowledge=True)
        record = {'event_id': str(uuid.uuid4()), 'displayed_at': now(), 'adapter': 'summary-import',
                  'tag': 'PS', 'state': 'UNSUPPORTED', 'method': None}
        saved = store.history_change(token, now, 'append', access.assess, record=record)
        fixture.update(event_id=record['event_id'], payload_sha256=hashlib.sha256(c.encode(saved)).hexdigest())
        fixture_path.write_text(json.dumps(fixture)); fixture_path.chmod(0o600)
        # Actual contending transactions; no connection/row substitution.
        from concurrent.futures import ThreadPoolExecutor
        def authenticated(_): return store.authenticate(token, now)
        with ThreadPoolExecutor(max_workers=2) as pool:
            need(list(pool.map(authenticated, (1, 2))) == [fixture['account_id']] * 2)
        cases.extend(['actual_nonempty_backup_seed', 'two_actual_concurrent_peer_transactions'])
    else:
        need(store.profile['database'] == 'ait_account_restore')
        _, token = store.session(None, now, 'synthetic-restore')
        public, token = store.login(fixture['username'], PASSWORD, token, now, 'synthetic-restore')
        need(public['account']['id'] == fixture['account_id'])
        records = store.history_list(token, now, export=True)['items']
        need(len(records) == 1 and records[0]['event_id'] == fixture['event_id']
             and hashlib.sha256(c.encode(records[0])).hexdigest() == fixture['payload_sha256'])
        cases.append('real_dump_restore_password_login_and_exact_nonempty_payload')
        future = now() + c.RETENTION + 1
        _, token = store.session(None, future, 'synthetic-retention')
        _, token = store.login(fixture['username'], PASSWORD, token, future, 'synthetic-retention')
        need(store.history_list(token, future, export=True)['items'] == [])
        cases.append('actual_sql_logical_retention_expiry_without_owner_view_dependency')
        try:
            with store._db(now): pass
        except c.AccountError: pass
        else: need(False)
        cases.append('persisted_clock_rollback_refuses_after_restore')
        result = store.delete_account(token, PASSWORD, future)
        need(result['deleted'] and result['entitlement_cleanup'] == 'PENDING')
        need(store.finish_cleanup(fixture['account_id'], None, future) is False)
        cases.append('restored_account_delete_keeps_durable_unavailable_cleanup_outbox')
        separate_access = initialize_access(work / 'runtime/restored-entitlements')
        replay = store.retry_cleanup(separate_access.forget, future)
        need(replay['examined'] == 1 and replay['completed'] == 1)
        with store._db(future) as (tx, _):
            need(tx.execute('SELECT count(*) FROM cleanup').fetchone()[0] == 0)
        cases.append('actual_recovered_deletion_outbox_retry_with_separate_real_access_engine')
    return {'pass': True, 'actual_postgresql': True, 'synthetic_only': True, 'mode': mode,
            'cases': [{'case': name, 'pass': True} for name in cases],
            'public_service_enabled': False, 'payment_processed': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile', type=Path, required=True)
    parser.add_argument('--workspace', type=Path, required=True)
    parser.add_argument('--mode', choices=('http', 'seed', 'restore'), default='http')
    parser.add_argument('--run-name', choices=('first', 'final'), default='first')
    args = parser.parse_args(); work = args.workspace
    need(sys.platform == 'linux' and os.geteuid() != 0 and ROOT == work / 'source'
         and args.profile == work / 'runtime' / ('restore-profile.json' if args.mode == 'restore' else 'profile.json'))
    observed = json.loads((ROOT / 'source-manifest.json').read_text())
    def hashes(): return {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in observed['files']}
    before = hashes(); need(before == {n: r['sha256'] for n, r in observed['files'].items()})
    report = {'profile': 'synthetic-postgres-account-http-review/v1', 'source': before,
              'source_commit': observed['source_base'], 'actual_postgresql': True, 'synthetic_only': True,
              'public_service_enabled': False, 'payment_processed': False, 'cases': []}
    stage = 'startup'; process = None; output = None; started = time.monotonic(); failed = None
    if args.mode != 'http':
        try:
            result = recovery(args.profile, work, args.mode)
        except BaseException as error:
            result = {'pass': False, 'failure_type': type(error).__name__, 'mode': args.mode,
                      'synthetic_only': True, 'public_service_enabled': False}
            if isinstance(error, c.AccountError): result['failure_code'] = error.code
        result.update(source=before, source_commit=observed['source_base'], source_unchanged=before == hashes(),
                      seconds=time.monotonic() - started)
        target = work / 'runtime' / ('actual-pg-' + args.mode + '.json')
        need(not target.exists()); target.write_text(json.dumps(result, indent=2) + '\n'); target.chmod(0o600)
        print(json.dumps(result, sort_keys=True)); return 0 if result['pass'] else 2
    try:
        import psycopg
        need(psycopg.__version__ == '3.3.9' and psycopg.pq.__impl__ == 'python')
        report['driver'] = {'name': 'psycopg', 'version': psycopg.__version__, 'implementation': psycopg.pq.__impl__, 'libpq_version': psycopg.pq.version()}
        store = pg.PostgresAccountStore(args.profile)
        with store._db(lambda: int(time.time())): pass
        report['cases'].append({'case': 'actual_unprivileged_peer_store_transaction', 'pass': True})
        access_dir = work / 'runtime/entitlements'
        access = HistoryEntitlements(access_dir) if access_dir.exists() else initialize_access(access_dir)
        log_name = 'http-private.log' if args.run_name == 'first' else 'http-final-private.log'
        output = (work / 'runtime' / log_name).open('xb')
        child_environment = {'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8',
                             'PYTHONDONTWRITEBYTECODE': '1', 'PSYCOPG_IMPL': 'python'}
        if 'HOME' in os.environ: child_environment['HOME'] = os.environ['HOME']
        process = subprocess.Popen([sys.executable, '-B', '-m', 'services.accounts.postgres', '--profile', str(args.profile),
                                    '--review-http', '--entitlements', str(access_dir)], cwd=ROOT,
                                   stdout=output, stderr=output, start_new_session=True, env=child_environment)
        ready = False
        for _ in range(100):
            need(process.poll() is None)
            try:
                with socket.create_connection(('127.0.0.1', 18791), .1): ready = True; break
            except OSError: time.sleep(.05)
        need(ready)
        def done(name): report['cases'].append({'case': name, 'pass': True})
        a, b = Browser(), Browser(); name_a, name_b = 'pga_' + secrets.token_hex(5), 'pgb_' + secrets.token_hex(5)
        stage = 'signup_two_real_accounts'
        for client, username in ((a, name_a), (b, name_b)):
            need(client.call('GET', '/v1/account/session')['authenticated'] is False)
            value = client.call('POST', '/v1/account/signup', {'username': username, 'password': PASSWORD}, 201)
            need(value['authenticated'] is True and value['account']['username'] == username and value['recovery_available'] is False)
            cookies = list(client.jar); need(len(cookies) == 1 and cookies[0].has_nonstandard_attr('HttpOnly') and cookies[0].path == '/v1/account')
        aa = a.call('GET', '/v1/account/session')['account']['id']; bb = b.call('GET', '/v1/account/session')['account']['id']; need(aa != bb); done(stage)
        stage = 'exact_origin_csrf_and_optional_get_binding'
        a.call('POST', '/v1/account/history', {'operation': 'disable'}, 403, {'X-CSRF-Token': '0' * 64})
        a.call('GET', '/v1/account/history', code=403, headers={'Origin': 'https://untrusted.invalid'})
        b.call('GET', '/v1/account/history', code=403, headers={'X-CSRF-Token': a.csrf})
        need(b.call('GET', '/v1/account/history')['items'] == []); done(stage)
        stage = 'server_owned_access_not_client_payment'
        a.call('POST', '/v1/account/history', {'operation': 'enable', 'acknowledge_metadata': True}, 403)
        now = int(time.time()); access.grant(aa, str(uuid.uuid4()), now + 600, now)
        need(a.call('GET', '/v1/account/entitlements')['state'] == 'ACTIVE')
        a.call('POST', '/v1/account/history', {'operation': 'enable', 'acknowledge_metadata': True}); done(stage)
        stage = 'actual_history_append_owner_isolation_and_conflict'
        finding = {'event_id': str(uuid.uuid4()), 'displayed_at': int(time.time()), 'adapter': 'summary-import', 'tag': 'PS',
                   'state': 'FINDING', 'method': {'name': 'synthetic-declared-review', 'revision': '1', 'sha256': '0' * 64}}
        unavailable = {**finding, 'event_id': str(uuid.uuid4()), 'state': 'UNAVAILABLE', 'method': None}
        saved = a.call('POST', '/v1/account/history', {'operation': 'append', 'record': finding})
        need(saved['verified_assertion'] is False and saved['input_included'] is False and saved['research_consent'] is False)
        need(a.call('POST', '/v1/account/history', {'operation': 'append', 'record': finding}) == saved)
        a.call('POST', '/v1/account/history', {'operation': 'append', 'record': unavailable})
        a.call('POST', '/v1/account/history', {'operation': 'append', 'record': {**finding, 'state': 'UNAVAILABLE', 'method': None}}, 409)
        need(b.call('GET', '/v1/account/history')['items'] == [])
        b.call('DELETE', '/v1/account/history/' + finding['event_id'], {}, 404); done(stage)
        stage = 'actual_filtered_history_counts_cursor_and_complete_export'
        filtered = a.call('GET', '/v1/account/history?state=FINDING&limit=1')
        need(filtered['total_entries'] == 2 and filtered['matching_entries'] == 1 and len(filtered['items']) == 1 and filtered['items'][0]['event_id'] == finding['event_id'])
        empty = a.call('GET', '/v1/account/history?state=NO_FINDING'); need(empty['total_entries'] == 2 and empty['matching_entries'] == 0)
        a.call('GET', '/v1/account/history?state=FINDING&after=' + unavailable['event_id'], code=404)
        exported = a.call('GET', '/v1/account/history/export'); need(len(exported['items']) == 2)
        need(all(x['input_included'] is False and x['research_consent'] is False for x in exported['items'])); done(stage)
        stage = 'revocation_does_not_block_read_export_disable_or_removal'
        access.revoke(aa, str(uuid.uuid4()), int(time.time()))
        a.call('POST', '/v1/account/history', {'operation': 'append', 'record': {**finding, 'event_id': str(uuid.uuid4())}}, 403)
        need(len(a.call('GET', '/v1/account/history/export')['items']) == 2)
        a.call('POST', '/v1/account/history', {'operation': 'disable'})
        a.call('DELETE', '/v1/account/history/' + unavailable['event_id'], {})
        need(a.call('GET', '/v1/account/history')['total_entries'] == 1); done(stage)
        stage = 'logout_and_real_password_login'
        a.call('DELETE', '/v1/account/session', {})
        a.call('GET', '/v1/account/session')
        a.call('POST', '/v1/account/sessions', {'username': name_a, 'password': PASSWORD})
        need(a.call('GET', '/v1/account/history')['total_entries'] == 1); done(stage)
        stage = 'real_precommit_cancellation_rolls_back'
        try:
            with store._db(lambda: int(time.time())) as (tx, _):
                tx.execute('UPDATE accounts SET history_enabled=1 WHERE account_id=?', (aa,))
                raise KeyboardInterrupt()
        except KeyboardInterrupt: pass
        else: need(False)
        need(a.call('GET', '/v1/account/session')['history_enabled'] is False); done(stage)
        stage = 'real_commit_then_lost_ack_is_typed_not_fake_rollback'
        real_connect = pg.connect
        class LostAcknowledgement:
            def __init__(self, conn): self.conn = conn
            def execute(self, query, *values, **kwargs):
                result = self.conn.execute(query, *values, **kwargs)
                if query == 'COMMIT': result.close(); raise OSError('synthetic lost commit acknowledgement')
                return result
            def close(self): self.conn.close()
        with mock.patch.object(pg, 'connect', side_effect=lambda profile: LostAcknowledgement(real_connect(profile))):
            try:
                with store._db(lambda: int(time.time())) as (tx, _): tx.execute('UPDATE accounts SET history_enabled=1 WHERE account_id=?', (aa,))
            except pg.CommitUncertain: pass
            else: need(False)
        need(a.call('GET', '/v1/account/session')['history_enabled'] is True); done(stage)
        stage = 'delete_account_reauthentication_and_durable_cleanup'
        a.call('DELETE', '/v1/account', {'password': PASSWORD + '-wrong'}, 401)
        deleted = a.call('DELETE', '/v1/account', {'password': PASSWORD})
        need(deleted['deleted'] and deleted['entitlement_cleanup'] == 'COMPLETE' and deleted['cleanup_pending'] is False)
        need(b.call('GET', '/v1/account/session')['account']['id'] == bb)
        b.call('DELETE', '/v1/account/history', {})
        need(b.call('GET', '/v1/account/history')['total_entries'] == 0); done(stage)
        fixture = {'username': name_b, 'account_id': bb, 'contains_real_participant_data': False, 'password_is_fixed_synthetic_source_fixture': True}
        target = work / 'runtime' / ('recovery-fixture.json' if args.run_name == 'first' else 'recovery-fixture-final.json')
        need(not target.exists()); target.write_text(json.dumps(fixture)); target.chmod(0o600)
        report['pass'] = True
    except BaseException as error:
        failed = error
        report.update(failure_stage=stage, failure_type=type(error).__name__)
        if isinstance(error, c.AccountError): report['failure_code'] = error.code
    finally:
        cleanup = True
        if process is not None:
            try:
                if process.poll() is None: process.terminate()
                process.wait(timeout=10)
            except BaseException:
                cleanup = False
                if process.returncode is None:
                    try: os.killpg(process.pid, signal.SIGKILL)
                    except ProcessLookupError: pass
                    process.wait(timeout=5)
            report['http_process_exit_code'] = process.returncode
        if output is not None: output.close()
        report['owned_http_process_stopped'] = cleanup
        report['source_unchanged'] = before == hashes(); report['seconds'] = time.monotonic() - started
        report['pass'] = failed is None and cleanup and report['source_unchanged']
        path = work / 'runtime' / ('actual-pg-http.json' if args.run_name == 'first' else 'actual-pg-http-final.json'); need(not path.exists()); path.write_text(json.dumps(report, indent=2) + '\n'); path.chmod(0o600)
        print(json.dumps(report, sort_keys=True))
    return 0 if report['pass'] else 2


if __name__ == '__main__': raise SystemExit(main())
