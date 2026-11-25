#!/usr/bin/env python3
"""Phase-specific actual PG erasure drill; synthetic fixtures stay private."""
import argparse
import copy
import hashlib
import hmac
import json
import os
from pathlib import Path
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools import account_core as c
from tools import account_erasure as e
from tools import account_postgres as p
from tools.history_entitlements import initialize, HistoryEntitlements

PASSWORD = 'synthetic-account-erasure-review-2026'


def need(value):
    if not value: raise AssertionError('Synthetic account erasure check failed.')


def refused(callback, status=None):
    try: callback()
    except c.AccountError as error:
        if status is not None: need(error.status == status)
        return
    raise AssertionError('Expected fixed erasure refusal.')


def runtime(work, phase):
    folder = work / 'erasure/runtime'
    selected = folder / ('restore-profile.json' if phase in ('after', 'unready') else 'source-profile.json')
    store = p.PostgresAccountStore(selected)
    now = lambda: int(time.time())
    cases = []
    if phase == 'unready':
        forged = {'format': 'account-erasure-serving-receipt/v1', 'database': 'ait_erasure_restore',
                  'database_oid': 1, 'generation': store.profile['generation'], 'migration_one': p.SCHEMA_SHA,
                  'migration_two': e.MIGRATION_SHA, 'system_identity_sha256': store.profile['system_identity_sha256'],
                  'journal_sha256': None, 'backup_sha256': '0' * 64, 'head': 0, 'reconciled_at': None}
        fake_path = folder / 'forged-ready-negative.json'; e.write_record(fake_path, forged)
        negative = dict(store.profile, restore_receipt=str(fake_path))
        profile_path = folder / 'forged-ready-profile.json'; e.write_record(profile_path, negative)
        candidate = p.PostgresAccountStore(profile_path)
        try: candidate.session(None, now, 'synthetic-unreconciled-negative')
        except c.AccountError as error: need(error.code == 'recovery_unavailable' and error.status == 503)
        else: need(False)
        return ['actual_runtime_peer_refuses_forged_null_ready_receipt_on_unreconciled_database']
    if phase == 'seed':
        initialize(folder / 'entitlements')
        access = HistoryEntitlements(folder / 'entitlements', clock=now)
        fixture = {'format': 'synthetic-account-erasure-fixture/v1', 'accounts': []}
        for index in range(2):
            name = 'e' + uuid.uuid4().hex[:20]
            _, anonymous = store.session(None, now, 'synthetic-erasure-seed')
            public, token = store.signup(name, PASSWORD, anonymous, now, 'synthetic-erasure-seed')
            identity = public['account']['id']
            access.grant(identity, str(uuid.uuid4()), now() + 3600, now())
            store.history_change(token, now, 'enable', access.assess, acknowledge=True)
            record = {'event_id': str(uuid.uuid4()), 'displayed_at': now(), 'adapter': 'summary-import',
                      'tag': 'PS', 'state': 'UNSUPPORTED', 'method': None}
            saved = store.history_change(token, now, 'append', access.assess, record=record)
            with store._db(now) as (transaction, _):
                row = transaction.execute('SELECT payload FROM history WHERE account_id=? AND event_id=?', (identity, record['event_id'])).fetchone()
                payload_sha = e.digest(row['payload'])
            fixture['accounts'].append({'account_id': identity, 'username': name, 'token': token,
                                        'event_id': record['event_id'], 'payload_sha256': payload_sha})
        e.write_record(folder / 'fixture.json', fixture)
        cases.append('two_real_accounts_sessions_and_nonempty_private_history_before_backup')
    else:
        fixture, _ = e.read_record(folder / 'fixture.json')
        victim, survivor = fixture['accounts']
        access = HistoryEntitlements(folder / 'entitlements', clock=now)
        if phase == 'delete':
            result = store.delete_account(victim['token'], PASSWORD, now)
            need(result['deleted'] is True and store.finish_cleanup(victim['account_id'], access.forget, now) is True)
            with store._db(now) as (transaction, _):
                need(transaction.execute('SELECT 1 FROM cleanup WHERE account_id=?', (victim['account_id'],)).fetchone() is None)
                state = e.state(transaction)
                need(state['retained_rows'] >= 1)
            cases.append('real_account_delete_and_successful_external_cleanup_leave_independent_erasure_journal')
        else:
            refused(lambda: store.authenticate(victim['token'], now), 401)
            _, anonymous = store.session(None, now, 'synthetic-erasure-restored')
            refused(lambda: store.login(victim['username'], PASSWORD, anonymous, now, 'synthetic-erasure-restored'), 401)
            _, anonymous = store.session(None, now, 'synthetic-erasure-survivor')
            public, token = store.login(survivor['username'], PASSWORD, anonymous, now, 'synthetic-erasure-survivor')
            need(public['account']['id'] == survivor['account_id'])
            exported = store.history_list(token, now, export=True)
            need(any(item['event_id'] == survivor['event_id'] for item in exported['items']))
            with store._db(now) as (transaction, _):
                need(transaction.execute('SELECT payload FROM history WHERE account_id=? AND event_id=?', (victim['account_id'], victim['event_id'])).fetchone() is None)
                row = transaction.execute('SELECT payload FROM history WHERE account_id=? AND event_id=?', (survivor['account_id'], survivor['event_id'])).fetchone()
                need(e.digest(row['payload']) == survivor['payload_sha256'])
                need(transaction.execute('SELECT 1 FROM cleanup WHERE account_id=?', (victim['account_id'],)).fetchone() is not None)
            need(store.finish_cleanup(victim['account_id'], access.forget, now) is True)
            cases.extend(['restored_deleted_password_and_old_session_refuse',
                          'restored_deleted_history_absent_and_survivor_password_and_exact_payload_preserved',
                          'restored_entitlement_cleanup_outbox_survives_and_retries_with_real_access_engine'])
            connection = p.connect(store.profile)
            try:
                for query in ('DELETE FROM accounts.erasure_journal', 'TRUNCATE accounts.erasure_journal',
                              'UPDATE accounts.erasure_state SET reserved_live=0',
                              'SELECT accounts.record_account_erasure()',
                              'ALTER TABLE accounts.accounts DISABLE TRIGGER account_erasure_record',
                              'SET ROLE ait_account_owner'):
                    try: connection.execute(query).close()
                    except Exception: pass
                    else: raise AssertionError('Runtime erasure privilege unexpectedly granted.')
            finally:
                connection.close()
            cases.append('actual_runtime_cannot_mutate_journal_state_trigger_or_owner_role')
    return cases


def operator(work, phase):
    folder = work / 'erasure/operator'
    fixture, _ = e.read_record(folder / 'fixture.json')
    selected = p.load_profile(folder / 'restore-profile.json')
    victim, survivor = fixture['accounts']
    def present():
        with e.operator(selected) as transaction:
            e.require_quiescent(transaction)
            row = transaction.one('SELECT salt,password_hash FROM accounts.accounts WHERE account_id=%s', (victim['account_id'],))
            need(row is not None and hmac.compare_digest(c.derive(PASSWORD, bytes(row[0])), bytes(row[1])))
            need(transaction.one('SELECT count(*) FROM accounts.sessions WHERE token_hash=%s', (c.token_hash(victim['token']),)) == (1,))
            row = transaction.one('SELECT payload FROM accounts.history WHERE account_id=%s AND event_id=%s', (victim['account_id'], victim['event_id']))
            need(row is not None and e.digest(bytes(row[0])) == victim['payload_sha256'])
            need(transaction.one('SELECT count(*) FROM accounts.accounts WHERE account_id=%s', (survivor['account_id'],)) == (1,))
            need(e.state(transaction)['reconciled_sha'] is None)
    present()
    if phase == 'before': return ['actual_old_backup_contains_valid_password_session_and_exact_history_while_serving_is_blocked']
    manifest, _ = e.read_record(folder / 'backup.json')
    received, raw = e.read_record(folder / 'journal.json')
    expected, _ = e.read_record(folder / 'selected-checkpoint.json')
    # Negative recovery input uses an explicit owner-created synthetic extra
    # erasure, NOT a claimed additional real user deletion. Filler is rolled back.
    extra = copy.deepcopy(received)
    extra['head'] += 1
    extra['rows'].append({'sequence': extra['head'], 'account_id': str(uuid.uuid4()), 'erased_at': extra['clock']})
    extra_raw = c.encode(extra) + b'\n'
    extra_expected = dict(expected, head=extra['head'], journal_sha256=e.digest(extra_raw))
    filled = False
    def pending_capacity(transaction):
        nonlocal filled
        live, pending = transaction.one('SELECT (SELECT count(*) FROM accounts.accounts),(SELECT count(*) FROM accounts.cleanup)')
        count = e.MAX_ACCOUNTS - live - pending
        need(0 <= count <= e.MAX_ACCOUNTS)
        transaction.raw('INSERT INTO accounts.cleanup SELECT gen_random_uuid()::text,%s FROM generate_series(1,%s)', (int(time.time()), count)).close()
        filled = True
    try:
        e.reconcile(selected, manifest, extra, extra_expected, extra_raw, lambda: int(time.time()), _before_apply=pending_capacity)
    except c.AccountError as error:
        need(filled and error.code == 'recovery_capacity_unavailable')
    else: need(False)
    present()
    def fault(): raise RuntimeError('synthetic precommit rollback')
    refused(lambda: e.reconcile(selected, manifest, received, expected, raw,
                               lambda: int(time.time()), before_commit=fault))
    present()
    need(not (folder / 'serving-receipt.json').exists())
    with e.operator(selected) as transaction:
        need(transaction.one("SELECT tgenabled FROM pg_trigger WHERE tgname='account_erasure_record'") == ('O',))
    return ['owner_created_pending_cleanup_capacity_refuses_without_dropping_actions_or_issuing_receipt',
            'real_reconciliation_precommit_failure_restores_account_trigger_and_outbox_without_serving_receipt']


def capacity(work):
    """Owner-created SQL filler is not4096 people or password/signup tests."""
    folder = work / 'erasure/operator'
    fixture, _ = e.read_record(folder / 'fixture.json')
    selected = p.load_profile(folder / 'source-profile.json')
    account = fixture['accounts'][1]
    with e.operator(selected) as transaction:
        e.require_quiescent(transaction)
        before = e.state(transaction)
        need(before['retained_rows'] == 0)
    completed = False
    try:
        with e.operator(selected, write=True) as transaction:
            transaction.raw('SELECT singleton FROM accounts.meta WHERE singleton=1 FOR UPDATE').close()
            value = e.state(transaction, True)
            chosen = transaction.one('SELECT clock FROM accounts.meta WHERE singleton=1')[0]
            fill = e.MAX_ROWS - value['reserved_live']
            need(0 < fill <= e.MAX_ROWS)
            transaction.raw('SET LOCAL ROLE ait_account_owner').close()
            transaction.raw('INSERT INTO accounts.erasure_journal SELECT %s+g,gen_random_uuid()::text,%s FROM generate_series(1,%s) AS g', (value['head'], chosen, fill)).close()
            transaction.raw('UPDATE accounts.erasure_state SET head=head+%s,retained_rows=%s,clock=%s WHERE singleton=1', (fill, fill, chosen)).close()
            full = e.state(transaction)
            need(full['reserved_live'] + full['retained_rows'] == e.MAX_ROWS)
            # An actual ignored conflict must not reserve a phantom slot.
            transaction.raw('INSERT INTO accounts.accounts VALUES(%s,%s,%s,%s,%s,0) ON CONFLICT(username) DO NOTHING',
                            (str(uuid.uuid4()), account['username'], b'x' * 16, b'y' * 32, chosen)).close()
            need(e.state(transaction) == full)
            transaction.raw('SAVEPOINT erasure_capacity_probe').close()
            rejected = False
            try:
                transaction.raw('INSERT INTO accounts.accounts VALUES(%s,%s,%s,%s,%s,0)',
                                (str(uuid.uuid4()), 'erasure_capacity_probe', b'x' * 16, b'y' * 32, chosen)).close()
            except Exception:
                rejected = True
                # Restore a failed SQL transaction without first issuing set_config.
                transaction.connection.execute('ROLLBACK TO SAVEPOINT erasure_capacity_probe').close()
            need(rejected and e.state(transaction) == full)
            transaction.raw('DELETE FROM accounts.accounts WHERE account_id=%s', (account['account_id'],)).close()
            deleted = e.state(transaction)
            need(deleted['reserved_live'] == full['reserved_live'] - 1
                 and deleted['retained_rows'] == full['retained_rows'] + 1
                 and deleted['reserved_live'] + deleted['retained_rows'] == e.MAX_ROWS)
            need(e._prune(transaction, chosen + e.WINDOW)['pruned'] == 0)
            need(e._prune(transaction, chosen + e.WINDOW + 1)['pruned'] == deleted['retained_rows'])
            final = e.state(transaction)
            need(final['retained_rows'] == 0 and final['floor'] == final['head'])
            completed = True
            raise RuntimeError('intentional owner-only capacity drill rollback')
    except c.AccountError:
        need(completed)
    with e.operator(selected) as transaction:
        need(e.state(transaction) == before)
        need(transaction.one('SELECT count(*) FROM accounts.accounts WHERE account_id=%s', (account['account_id'],)) == (1,))
    return ['owner_only_rolledback4096_capacity_reserves_real_account_deletion_without_phantom_conflict_slot',
            'actual_seven_day_boundary_retention_then_pruning_and_full_rollback']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', required=True, type=Path)
    parser.add_argument('--phase', required=True, choices=('seed', 'capacity', 'delete', 'before', 'unready', 'rollback', 'after'))
    args = parser.parse_args()
    try:
        need(sys.platform == 'linux' and ROOT == args.workspace / 'erasure-source')
        start = time.monotonic()
        if args.phase == 'capacity': cases = capacity(args.workspace)
        elif args.phase in ('before', 'rollback'): cases = operator(args.workspace, args.phase)
        else: cases = runtime(args.workspace, args.phase)
        result = {'pass': True, 'phase': args.phase, 'actual_postgresql': True, 'synthetic_only': True,
                  'cases': [{'case': name, 'pass': True} for name in cases], 'seconds': time.monotonic() - start,
                  'source': {name: e.digest((ROOT / name).read_bytes()) for name in
                             ('tools/account_postgres.py', 'tools/account_erasure.py', 'scripts/account-erasure.py',
                              'scripts/verify-account-erasure.py', e.MIGRATION_FILE)},
                  'public_service_enabled': False, 'payment_processed': False}
        print(json.dumps(result, sort_keys=True)); return 0
    except Exception as error:
        print(json.dumps({'pass': False, 'phase': args.phase, 'failure_type': type(error).__name__,
                          'synthetic_only': True, 'public_service_enabled': False})); return 2


if __name__ == '__main__': raise SystemExit(main())
