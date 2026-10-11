#!/usr/bin/env python3
"""Actual PostgreSQL 18 controls, restricted to a disposable synthetic cluster."""
import argparse
import copy
from datetime import datetime, timezone
import hashlib
import itertools
import json
import os
from pathlib import Path
import pwd
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from protocol.reports import write_report

SCHEMA = ROOT/'deploy/research/metadata-development.sql'
LOCAL = {'schema_version':1,'purpose':'PS_preview_usability_and_failure_review',
    'tag':'PS','method_version':'context-v6','reported_result':'pattern_found',
    'failure_category':'none_observed','feedback':'easy_to_understand',
    'sharing':'local_file_not_submitted'}
ENVELOPE = {'format':'metadata-storage-development/v1','synthetic':True,
    'permission':'synthetic_test_only','feedback':LOCAL}


def literal(value):
    """Quote only synthetic test text; the SQL functions perform no dynamic SQL."""
    return "'"+value.replace("'", "''")+"'"


def sandbox(path):
    path = Path(path).absolute()
    if (os.geteuid()==0 or path.parent != Path('/tmp') or
            not path.name.startswith('aitrust-metadata-') or path.is_symlink() or
            path.resolve()!=path or path.stat().st_uid!=os.geteuid() or
            path.stat().st_mode & 0o777 != 0o700):
        raise ValueError('Use an owned private disposable synthetic directory.')
    for name in ('data','socket'):
        child=path/name
        if child.is_symlink() or child.stat().st_uid!=os.geteuid() or child.stat().st_mode & 0o777 != 0o700:
            raise ValueError('Synthetic data and socket directories must be private.')
    return path


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sandbox-dir',required=True);parser.add_argument('--output');args=parser.parse_args()
    directory=sandbox(args.sandbox_dir)
    paths=['deploy/research/metadata-development.sql','scripts/verify-metadata-store.py','scripts/metadata-store-sandbox.py',
        'site/src/research-feedback.js','protocol/reports.py']
    def inventory():return {p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths}
    before=inventory();cases=[]
    command=['/usr/lib/postgresql/18/bin/psql','-XqAt','--set','ON_ERROR_STOP=1',
        '--host',str(directory/'socket'),'--port','55443','--dbname','postgres',
        '--username',pwd.getpwuid(os.geteuid()).pw_name]
    environment={'PATH':os.defpath,'LANG':'C.UTF-8',
        'PGOPTIONS':'-c statement_timeout=5000 -c lock_timeout=3000 -c standard_conforming_strings=on'}
    def sql(query, good=True, role=None):
        if role:query='SET ROLE '+role+';\n'+query
        result=subprocess.run(command,input=query.encode(),capture_output=True,env=environment,timeout=15)
        if len(result.stdout)+len(result.stderr)>65536 or (result.returncode==0)!=good:
            raise ValueError('Synthetic database control failed; inspect private diagnostics.')
        if b'PRIVATE_METADATA_CANARY' in result.stdout+result.stderr:
            raise ValueError('Synthetic sensitive field was reflected.')
        return result.stdout.decode().strip()
    observed=json.loads(sql("SELECT json_build_object('data',current_setting('data_directory'),'socket',current_setting('unix_socket_directories'),'cluster',current_setting('cluster_name'),'listen',current_setting('listen_addresses'),'version',current_setting('server_version_num'),'tcp',inet_server_addr());"))
    if (observed['data']!=str(directory/'data') or observed['socket']!=str(directory/'socket') or
            observed['cluster']!='aitrust-metadata-synthetic' or observed['listen']!='' or
            observed['tcp'] is not None or not 180000 <= int(observed['version']) < 190000):
        raise ValueError('Refused a database outside the synthetic cluster.')
    sql(SCHEMA.read_text());cases.append({'case':'private_nonroot_socket_cluster_and_schema','pass':True})
    digest="decode('"+'01'*32+"','hex')"
    def record(value=ENVELOPE, token=digest, good=True):
        raw=value if isinstance(value,str) else json.dumps(value,separators=(',',':'))
        return sql('SELECT metadata_dev.record_synthetic('+literal(raw)+','+token+');',good,'ait_metadata_intake')
    identity=record();assert len(identity)==36
    assert record()==identity
    cases.append({'case':'valid_insert_and_idempotent_duplicate','pass':True})
    bad=copy.deepcopy(ENVELOPE);bad['feedback']['feedback']='hard_to_use';record(bad,good=False)
    cases.append({'case':'conflicting_duplicate_cannot_overwrite','pass':True})
    mutations=[('unknown_prompt',lambda x:x.update(prompt='PRIVATE_METADATA_CANARY')),
        ('nested_content',lambda x:x['feedback'].update(text='PRIVATE_METADATA_CANARY')),
        ('not_synthetic',lambda x:x.update(synthetic=False)),
        ('wrong_format',lambda x:x.update(format='participant_submission/v1')),
        ('download_is_not_consent',lambda x:x.update(permission='local_download')),
        ('unsupported_method',lambda x:x['feedback'].update(method_version='unknown')),
        ('unsupported_tag',lambda x:x['feedback'].update(tag='FA')),
        ('wrong_version',lambda x:x['feedback'].update(schema_version=1.0)),
        ('null_enum',lambda x:x['feedback'].update(feedback=None)),
        ('nested_enum',lambda x:x['feedback'].update(feedback={})),
        ('unknown_result',lambda x:x['feedback'].update(reported_result='safe')),
        ('unknown_failure',lambda x:x['feedback'].update(failure_category='identity')),
        ('false_sharing_marker',lambda x:x['feedback'].update(sharing='submitted')),
        ('sql_injection_value',lambda x:x['feedback'].update(feedback="'; DROP SCHEMA metadata_dev CASCADE; --"))]
    for name, mutate in mutations:
        value=copy.deepcopy(ENVELOPE);mutate(value);record(value,good=False);cases.append({'case':name,'pass':True})
    for name,raw in [('malformed_json','{'),('array_json','[]'),('null_json','null'),
        ('oversized_json','x'*4097),('duplicate_top_key',json.dumps(ENVELOPE)[:-1]+',"synthetic":true}'),
        ('duplicate_nested_key',json.dumps(ENVELOPE).replace('"schema_version": 1','"schema_version": 1, "schema_version": 1')),
        ('escaped_duplicate_key',json.dumps(ENVELOPE).replace('"schema_version": 1','"schema_version": 1, "\\u0073chema_version": 1')),
        ('escaped_nul_key',json.dumps(ENVELOPE)[:-1]+',"PRIVATE_METADATA_CANARY\\u0000":true}'),
        ('escaped_surrogate_key',json.dumps(ENVELOPE)[:-1]+',"PRIVATE_METADATA_CANARY\\ud800":true}'),
        ('escaped_surrogate_value',json.dumps(ENVELOPE).replace('metadata-storage-development/v1','PRIVATE_METADATA_CANARY\\ud800'))]:
        record(raw,good=False);cases.append({'case':name,'pass':True})
    for name,token in [('null_digest','NULL'),('short_digest',"decode('00','hex')")]:
        record(token=token,good=False);cases.append({'case':name,'pass':True})
    for role in ('ait_metadata_intake','ait_metadata_review','ait_metadata_maintenance'):
        for operation in ('SELECT *','DELETE','UPDATE'):
            query={'SELECT *':'SELECT * FROM metadata_dev.feedback;',
                'DELETE':'DELETE FROM metadata_dev.feedback;',
                'UPDATE':"UPDATE metadata_dev.feedback SET feedback='hard_to_use';"}[operation]
            sql(query,False,role)
        sql('SELECT * FROM metadata_dev.withdrawals;',False,role)
        cases.append({'case':role+'_cannot_read_or_mutate_private_tables','pass':True})
    sql('SELECT metadata_dev.prune_synthetic();',False,'ait_metadata_intake')
    record(good=True)
    sql('SELECT metadata_dev.record_synthetic(NULL,NULL);',False,'ait_metadata_review')
    sql('SELECT metadata_dev.record_synthetic(NULL,NULL);',False,'ait_metadata_maintenance')
    sql('SELECT metadata_dev.record_synthetic(NULL,NULL);',False,'pg_monitor')
    sql('SELECT * FROM metadata_dev.review_counts;',False,'pg_monitor')
    assert sql("SELECT count(*) FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace, LATERAL aclexplode(p.proacl) a WHERE n.nspname='metadata_dev' AND a.grantee=0 AND a.privilege_type='EXECUTE';")=='0'
    assert sql("SELECT count(*) FROM pg_roles WHERE rolname LIKE 'ait_metadata_%' AND (rolsuper OR rolcreaterole OR rolcreatedb OR rolcanlogin OR rolreplication OR rolbypassrls OR rolinherit);")=='0'
    cases.append({'case':'restricted_function_grants_and_nonlogin_roles','pass':True})
    assert sql('SELECT count(*) FROM metadata_dev.review_counts;',role='ait_metadata_review')=='0'
    for i in range(2,6):record(token="decode('"+f'{i:02x}'*32+"','hex')")
    assert sql('SELECT reports FROM metadata_dev.review_counts;',role='ait_metadata_review')=='5'
    cases.append({'case':'review_exposes_only_five_record_enum_groups','pass':True})
    sql('CREATE TEMP TABLE feedback(dummy text); CREATE TEMP TABLE withdrawals(dummy text); SELECT metadata_dev.prune_synthetic();',role='ait_metadata_maintenance')
    assert sql('SELECT count(*) FROM metadata_dev.feedback;')=='5'
    cases.append({'case':'temporary_relation_shadow_cannot_redirect_definer','pass':True})
    sql('CREATE TABLE metadata_dev.synthetic_snapshot AS SELECT * FROM metadata_dev.feedback;',role='ait_metadata_owner')
    assert sql("SELECT metadata_dev.withdraw_synthetic(decode('"+'ff'*32+"','hex'));",role='ait_metadata_intake')=='f'
    assert sql('SELECT count(*) FROM metadata_dev.withdrawals;')=='0'
    assert sql('SELECT metadata_dev.withdraw_synthetic('+digest+');',role='ait_metadata_intake')=='t'
    assert sql('SELECT metadata_dev.withdraw_synthetic('+digest+');',role='ait_metadata_intake')=='f'
    assert sql('SELECT count(*) FROM metadata_dev.feedback;')=='4';record(good=False)
    cases.append({'case':'wrong_digest_isolation_withdrawal_and_no_resurrection','pass':True})
    sql('INSERT INTO metadata_dev.feedback SELECT * FROM metadata_dev.synthetic_snapshot ON CONFLICT DO NOTHING;',role='ait_metadata_owner')
    assert sql('SELECT count(*) FROM metadata_dev.review_counts;',role='ait_metadata_review')=='0'
    assert sql('SELECT metadata_dev.prune_synthetic();',role='ait_metadata_maintenance')=='1'
    assert sql('SELECT count(*) FROM metadata_dev.feedback;')=='4'
    cases.append({'case':'restored_rows_hidden_and_pending_deletion_applied','pass':True})
    sql("UPDATE metadata_dev.feedback SET expires_at=clock_timestamp()-interval '1 second';",role='ait_metadata_owner')
    assert sql('SELECT count(*) FROM metadata_dev.review_counts;',role='ait_metadata_review')=='0'
    assert sql('SELECT metadata_dev.prune_synthetic();',role='ait_metadata_maintenance')=='4'
    sql("UPDATE metadata_dev.withdrawals SET retain_until=clock_timestamp()-interval '1 second';",role='ait_metadata_owner')
    sql('SELECT metadata_dev.prune_synthetic();',role='ait_metadata_maintenance')
    assert sql('SELECT count(*) FROM metadata_dev.withdrawals;')=='0'
    cases.append({'case':'expired_rows_and_finished_deletion_instructions_removed','pass':True})
    combinations=itertools.product(
        ['pattern_found','no_pattern_found','unavailable','not_checked'],
        ['none_observed','unexpected_finding','possible_missed_pattern','could_not_check','unclear_result'],
        ['easy_to_understand','needs_clearer_explanation','hard_to_use','could_not_complete'])
    for index,(reported,failure,feedback) in enumerate(combinations,start=10):
        value=copy.deepcopy(ENVELOPE);value['feedback'].update(reported_result=reported,
            failure_category=failure,feedback=feedback)
        record(value,token="decode('"+f'{index:064x}'+"','hex')")
    assert sql('SELECT count(*) FROM metadata_dev.feedback;')=='80'
    cases.append({'case':'all_80_supported_feedback_enum_combinations','pass':True})
    stable=before==inventory();assert stable
    result={'captured_at':datetime.now(timezone.utc).isoformat(),'pass':True,'cases':cases,
        'case_count':len(cases),'sources':before,'source_unchanged_during_execution':stable,
        'server_version_num':observed['version'],'nonroot_execution':True,'database_tcp_listening':False,
        'only_synthetic_records':True,'participant_consent_verified':False,
        'production_database_changed':False,'new_endpoints':0,'real_backup_expiry_verified':False,
        'complete_restore_or_anonymity_claim':False,'independent_accuracy_evidence':False}
    if args.output:write_report(args.output,result,root=ROOT)
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    try:main()
    except (AssertionError,ValueError,OSError,subprocess.SubprocessError):
        print('Synthetic metadata-store verification failed; no production acceptance.',file=sys.stderr)
        raise SystemExit(1)
