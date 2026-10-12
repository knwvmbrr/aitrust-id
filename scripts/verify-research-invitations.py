#!/usr/bin/env python3
"""Actual invented invitation controls in the owned PostgreSQL 18 sandbox only."""
import argparse
import concurrent.futures
import copy
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('metadata_base_controls', ROOT/'scripts/verify-metadata-store.py')
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)
NAMES = ['deploy/research/metadata-development.sql', 'deploy/research/metadata-invitation-development.sql',
         'scripts/metadata-store-sandbox.py', 'scripts/verify-metadata-store.py',
         'scripts/verify-research-invitations.py', 'site/src/research-feedback.js', 'protocol/reports.py']
CASES = []


def inventory():
    return {name: hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in NAMES}


def digest(number):
    return "decode('" + number.to_bytes(32, 'big').hex() + "','hex')"


def verify(path):
    directory = base.sandbox(path)
    before = inventory()
    command = ['/usr/lib/postgresql/18/bin/psql', '-X', '-q', '-A', '-t',
               '-v', 'ON_ERROR_STOP=1', '-h', str(directory/'socket'), '-p', '55443', '-d', 'postgres']
    environment = {'PATH': os.defpath, 'LANG': 'C.UTF-8'}
    def execute(query, role=None):
        if role not in (None, 'ait_metadata_intake', 'ait_metadata_review',
                         'ait_metadata_maintenance', 'ait_metadata_owner', 'pg_monitor'):
            raise ValueError('Unknown synthetic role')
        query = "SET statement_timeout='5s'; SET lock_timeout='2s';\n" + (
            'SET ROLE '+role+';\n' if role else '') + query
        return subprocess.run(command, input=query.encode(), capture_output=True,
                              env=environment, timeout=12)
    def sql(query, good=True, role=None):
        result = execute(query, role)
        if ((result.returncode == 0) != good or len(result.stdout)+len(result.stderr)>65536
                or b'PRIVATE_INVITATION_CANARY' in result.stdout+result.stderr):
            raise ValueError('Synthetic invitation control failed')
        return result.stdout.decode().strip()
    def case(name):
        CASES.append({'case': name, 'pass': True})
    observed=json.loads(sql("SELECT json_build_object('data',current_setting('data_directory'),"
        "'socket',current_setting('unix_socket_directories'),'cluster',current_setting('cluster_name'),"
        "'listen',current_setting('listen_addresses'),'version',current_setting('server_version_num'),"
        "'tcp',inet_server_addr());"))
    if (observed['data'] != str(directory/'data') or observed['socket'] != str(directory/'socket')
            or observed['cluster'] != 'aitrust-metadata-synthetic' or observed['listen'] != ''
            or observed['tcp'] is not None or not 180000 <= int(observed['version']) < 190000):
        raise ValueError('Refused a database outside the synthetic cluster')
    sql((ROOT/NAMES[0]).read_text())
    sql((ROOT/NAMES[1]).read_text())
    case('owned_private_socket_cluster_and_separate_synthetic_profile')
    raw=json.dumps(base.ENVELOPE,separators=(',',':'))
    def issue(key, slots=3, life=3600, good=True, role='ait_metadata_maintenance'):
        return sql('SELECT metadata_dev.issue_invitation_synthetic('+digest(key)+','+str(slots)+','+str(life)+');',good,role)
    def submit(key, token, value=raw, good=True):
        return sql('SELECT metadata_dev.record_invited_synthetic('+base.literal(value)+','+
                   digest(token)+','+digest(key)+');',good,'ait_metadata_intake')
    def consumed(key):
        return sql('SELECT used FROM metadata_dev.invitations WHERE digest='+digest(key)+';')
    assert issue(1)=='t'
    original_expiry=sql('SELECT expires_at FROM metadata_dev.invitations WHERE digest='+digest(1)+';')
    assert issue(1,slots=20,life=86400)=='f' and consumed(1)=='0'
    assert sql('SELECT expires_at FROM metadata_dev.invitations WHERE digest='+digest(1)+';')==original_expiry
    case('maintenance_issuance_duplicate_cannot_expand_capacity')
    for slots in (0,21,-1):issue(2,slots=slots,good=False)
    for life in (0,86401,-1):issue(2,life=life,good=False)
    for expression in ('NULL', "decode('00','hex')"):
        sql('SELECT metadata_dev.issue_invitation_synthetic('+expression+',2,60);',False,'ait_metadata_maintenance')
        sql('SELECT metadata_dev.record_invited_synthetic('+base.literal(raw)+','+expression+','+digest(1)+');',False,'ait_metadata_intake')
        sql('SELECT metadata_dev.record_invited_synthetic('+base.literal(raw)+','+digest(4)+','+expression+');',False,'ait_metadata_intake')
    sql('SELECT metadata_dev.issue_invitation_synthetic('+digest(2)+',NULL,60);',False,'ait_metadata_maintenance')
    sql('SELECT metadata_dev.issue_invitation_synthetic('+digest(2)+',2,NULL);',False,'ait_metadata_maintenance')
    case('strict_digest_lifetime_and_capacity_limits')
    submit(99,10,good=False)
    assert sql('SELECT count(*) FROM metadata_dev.feedback;')=='0'
    case('unknown_invitation_inserts_nothing')
    identity=submit(1,10)
    assert len(identity)==36 and submit(1,10)==identity and consumed(1)=='1'
    case('valid_record_and_duplicate_use_one_lifetime_slot')
    assert issue(2)=='t'
    submit(2,10,good=False)
    assert consumed(2)=='0'
    case('withdrawal_digest_cannot_move_between_invitations')
    bad=copy.deepcopy(base.ENVELOPE);bad['feedback']['feedback']='hard_to_use'
    submit(1,10,json.dumps(bad),good=False)
    bad=copy.deepcopy(base.ENVELOPE);bad['prompt']='PRIVATE_INVITATION_CANARY'
    submit(1,11,json.dumps(bad),good=False)
    submit(1,11,'{',good=False)
    assert consumed(1)=='1' and sql('SELECT count(*) FROM metadata_dev.feedback;')=='1'
    case('conflicting_and_private_invalid_payload_roll_back_quota_and_rows')
    submit(1,11);submit(1,12);submit(1,13,good=False)
    assert consumed(1)=='3' and submit(1,10)==identity
    case('full_capacity_refuses_new_record_but_allows_exact_duplicate')
    assert sql('SELECT metadata_dev.withdraw_synthetic('+digest(10)+');',role='ait_metadata_intake')=='t'
    submit(1,10,good=False);submit(1,13,good=False)
    # Simulate the original tombstone completing; the invitation binding still
    # refuses resurrection while this invitation remains valid.
    sql('DELETE FROM metadata_dev.withdrawals;',role='ait_metadata_owner')
    submit(1,10,good=False)
    assert consumed(1)=='3' and sql('SELECT count(*) FROM metadata_dev.feedback;')=='2'
    case('withdrawal_never_refunds_capacity_or_resurrects_after_tombstone_expiry')
    for role in ('ait_metadata_intake','ait_metadata_review','ait_metadata_maintenance','pg_monitor'):
        sql('SELECT metadata_dev.record_synthetic('+base.literal(raw)+','+digest(50)+');',False,role)
    for role in ('ait_metadata_intake','ait_metadata_review','pg_monitor'):
        issue(8,good=False,role=role)
        sql('SELECT metadata_dev.revoke_invitation_synthetic('+digest(1)+');',False,role)
        sql('SELECT metadata_dev.prune_invitations_synthetic();',False,role)
    for role in ('ait_metadata_intake','ait_metadata_review','ait_metadata_maintenance'):
        for table in ('invitations','invitation_claims'):
            for query in ('SELECT * FROM','DELETE FROM'):
                sql(query+' metadata_dev.'+table+';',False,role)
            sql("UPDATE metadata_dev."+table+" SET retain_until=clock_timestamp();",False,role)
    sql('SELECT metadata_dev.record_invited_synthetic(NULL,NULL,NULL);',False,'ait_metadata_review')
    case('no_legacy_insert_issuance_prune_or_private_table_role_bypass')
    assert issue(3,2)=='t'
    submit(3,20)
    assert sql('SELECT metadata_dev.revoke_invitation_synthetic('+digest(3)+');',role='ait_metadata_maintenance')=='t'
    assert sql('SELECT metadata_dev.revoke_invitation_synthetic('+digest(3)+');',role='ait_metadata_maintenance')=='f'
    submit(3,20,good=False);submit(3,21,good=False)
    assert issue(4,2)=='t'
    submit(4,22)
    sql('UPDATE metadata_dev.invitations SET expires_at=clock_timestamp()-interval \'1 second\' WHERE digest='+digest(4)+';',role='ait_metadata_owner')
    submit(4,22,good=False);submit(4,23,good=False)
    case('revoked_and_expired_invitations_refuse')
    assert issue(5,2)=='t'
    def concurrent_submission(token):
        result=execute('SELECT metadata_dev.record_invited_synthetic('+base.literal(raw)+','+
                       digest(token)+','+digest(5)+');','ait_metadata_intake')
        if len(result.stdout)+len(result.stderr)>65536:raise ValueError('Oversized synthetic diagnostic')
        return result.returncode
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        statuses=list(pool.map(concurrent_submission,range(30,36)))
    assert statuses.count(0)==2 and consumed(5)=='2'
    case('six_concurrent_submissions_cannot_exceed_two_slots')
    sql('CREATE TEMP TABLE invitations(dummy text); CREATE TEMP TABLE invitation_claims(dummy text); '
        'SELECT metadata_dev.prune_invitations_synthetic();',role='ait_metadata_maintenance')
    assert consumed(5)=='2'
    assert sql("SELECT count(*) FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace, "
               "LATERAL aclexplode(p.proacl) a WHERE n.nspname='metadata_dev' AND a.grantee=0 "
               "AND a.privilege_type='EXECUTE';")=='0'
    case('temporary_shadow_and_public_execute_privilege_refused')
    for key in range(100,195):issue(key,1)
    assert sql('SELECT count(*) FROM metadata_dev.invitations;')=='100'
    issue(195,good=False)
    case('retained_issuance_count_is_bounded_at_one_hundred')
    sql("UPDATE metadata_dev.invitations SET expires_at=clock_timestamp()-interval '31 days', "
        "retain_until=clock_timestamp()-interval '1 second'; "
        "UPDATE metadata_dev.invitation_claims SET retain_until=clock_timestamp()-interval '1 second'; "
        "UPDATE metadata_dev.feedback SET expires_at=clock_timestamp()-interval '1 second';",role='ait_metadata_owner')
    assert sql('SELECT metadata_dev.prune_invitations_synthetic();',role='ait_metadata_maintenance')=='100'
    assert sql('SELECT count(*) FROM metadata_dev.invitations;')=='0'
    assert sql('SELECT count(*) FROM metadata_dev.invitation_claims;')=='0'
    assert sql('SELECT count(*) FROM metadata_dev.feedback;')=='0'
    case('expired_feedback_and_invitation_bindings_pruned_together')
    if before != inventory():raise ValueError('Synthetic sources changed during execution')
    return {'captured_at':datetime.now(timezone.utc).isoformat(),'pass':True,
        'cases':CASES,'case_count':len(CASES),'sources':before,'source_unchanged_during_execution':True,
        'server_version_num':observed['version'],'nonroot_execution':True,'database_tcp_listening':False,
        'only_synthetic_records':True,'participant_consent_verified':False,'production_database_changed':False,
        'new_endpoints':0,'real_backup_expiry_verified':False,'independent_accuracy_evidence':False,
        'research_service_running':False,'requirements_closed':0}


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sandbox-dir',required=True)
    args=parser.parse_args()
    try:print(json.dumps(verify(args.sandbox_dir),indent=2))
    except (ValueError,AssertionError,OSError,subprocess.SubprocessError):
        print(json.dumps({'pass':False,'completed_cases':[c['case'] for c in CASES]}))
        print('Synthetic invitation verification failed; no production acceptance.',file=sys.stderr)
        raise SystemExit(1)
