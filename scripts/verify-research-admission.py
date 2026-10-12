#!/usr/bin/env python3
"""Actual synthetic private request -> intake role -> PostgreSQL -> withdrawal."""
import argparse
import base64
import concurrent.futures
from datetime import datetime,timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tools.research_admission import PROFILE, FIXED, CHOICES, digest_token
from protocol.reports import write_report
spec=importlib.util.spec_from_file_location('admission_base',ROOT/'scripts/verify-metadata-store.py')
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
NAMES=['tools/research_admission.py','scripts/research-admission.py','scripts/verify-research-admission.py',
       'scripts/metadata-store-sandbox.py','scripts/verify-metadata-store.py',
       'deploy/research/metadata-development.sql','deploy/research/metadata-invitation-development.sql',
       'tools/blind_review_io.py','site/src/research-feedback.js','tests/test_research_admission.py']
CASES=[]


def inventory():return {n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in NAMES}


def token(n):return base64.urlsafe_b64encode(n.to_bytes(32,'big')).decode().rstrip('=')


def digest(n):return "decode('"+digest_token(token(n))+"','hex')"


def verify(path):
    directory=base.sandbox(path);before=inventory()
    command=['/usr/lib/postgresql/18/bin/psql','-XqAtw','-v','ON_ERROR_STOP=1',
             '-h',str(directory/'socket'),'-p','55443','-d','postgres']
    environment={'PATH':os.defpath,'LANG':'C.UTF-8'}
    def sql(query,role=None):
        require_role=role in (None,'ait_metadata_owner','ait_metadata_maintenance')
        if not require_role:raise ValueError('Unsupported synthetic verifier role')
        prefix="SET statement_timeout='5s'; SET lock_timeout='2s';\n"+('SET ROLE '+role+';\n' if role else '')
        r=subprocess.run(command,input=(prefix+query).encode(),capture_output=True,env=environment,timeout=12)
        if r.returncode or len(r.stdout)+len(r.stderr)>65536:raise ValueError('Synthetic admission SQL control failed')
        return r.stdout.decode().strip()
    observed=json.loads(sql("SELECT json_build_object('data',current_setting('data_directory'),"
        "'socket',current_setting('unix_socket_directories'),'cluster',current_setting('cluster_name'),"
        "'listen',current_setting('listen_addresses'),'version',current_setting('server_version_num'),"
        "'tcp',inet_server_addr());"))
    if (observed['data']!=str(directory/'data') or observed['socket']!=str(directory/'socket')
        or observed['cluster']!='aitrust-metadata-synthetic' or observed['listen']!=''
        or observed['tcp'] is not None or not 180000<=int(observed['version'])<190000):
        raise ValueError('Refused a database outside the synthetic cluster')
    sql((ROOT/'deploy/research/metadata-development.sql').read_text())
    sql((ROOT/'deploy/research/metadata-invitation-development.sql').read_text())
    inputs=directory/'requests';inputs.mkdir(mode=0o700)
    def request(invite=1,withdraw=2):
        return {'format':PROFILE,'synthetic':True,'operation':'submit','invitation_token':token(invite),
                'withdrawal_token':token(withdraw),'feedback':{**FIXED,**{k:v[0] for k,v in CHOICES.items()}}}
    counter=0
    def call(value,good=True,name=None):
        nonlocal counter
        # Concurrent callers supply distinct fixed filenames.
        counter+=1;file=inputs/(name or ('input-'+str(counter)+'.json'))
        raw=value if isinstance(value,bytes) else json.dumps(value).encode()
        file.write_bytes(raw);file.chmod(0o600)
        r=subprocess.run([sys.executable,str(ROOT/'scripts/research-admission.py'),
            '--sandbox-dir',str(directory),'--request',str(file)],capture_output=True,env=environment,timeout=16)
        diagnostic=r.stdout+r.stderr
        if (good is not None and (r.returncode==0)!=good or len(diagnostic)>4096
            or str(directory).encode() in diagnostic or b'PRIVATE_ADMISSION_CANARY' in diagnostic
            or b'Traceback' in diagnostic or token(1).encode() in diagnostic or token(2).encode() in diagnostic):
            raise ValueError('Actual synthetic admission CLI control failed')
        if r.returncode:
            if r.returncode!=1 or r.stderr!=b'SYNTHETIC_ADMISSION_REFUSED\n' or r.stdout:
                raise ValueError('Unexpected synthetic admission refusal')
            return None
        return json.loads(r.stdout)
    def case(name):CASES.append({'case':name,'pass':True})
    def issue(n,slots=3):
        assert sql('SELECT metadata_dev.issue_invitation_synthetic('+digest(n)+','+str(slots)+',3600);','ait_metadata_maintenance')=='t'
    issue(1);original=call(request());assert call(request())==original
    assert sql('SELECT used FROM metadata_dev.invitations WHERE digest='+digest(1)+';')=='1'
    case('actual_private_cli_roundtrip_and_exact_duplicate')
    mutated=request();mutated['feedback']['feedback']='hard_to_use';call(mutated,False)
    for field in ('prompt','example','text','email','ip','timestamp','subject_hash','role'):
        mutated=request(withdraw=3);mutated[field]='PRIVATE_ADMISSION_CANARY';call(mutated,False)
        mutated=request(withdraw=3);mutated['feedback'][field]='PRIVATE_ADMISSION_CANARY';call(mutated,False)
    for raw in (b'{',b'null',b'\xff',b'{"format":1,"format":2}',b' '*4097):call(raw,False)
    assert sql('SELECT count(*) FROM metadata_dev.feedback;')=='1'
    assert sql('SELECT used FROM metadata_dev.invitations WHERE digest='+digest(1)+';')=='1'
    case('conflicts_private_fields_malformed_duplicates_oversize_leave_rows_and_quota_unchanged')
    call(request(invite=99,withdraw=3),False)
    issue(10);assert sql('SELECT metadata_dev.revoke_invitation_synthetic('+digest(10)+');','ait_metadata_maintenance')=='t';call(request(invite=10,withdraw=3),False)
    issue(11);sql("UPDATE metadata_dev.invitations SET expires_at=clock_timestamp()-interval '1 second' WHERE digest="+digest(11)+';','ait_metadata_owner');call(request(invite=11,withdraw=3),False)
    case('wrong_revoked_and_expired_bearer_capabilities_refuse')
    issue(12);call(request(invite=12,withdraw=2),False)
    case('withdrawal_capability_cannot_move_to_another_invitation')
    call(request(withdraw=3));call(request(withdraw=4));call(request(withdraw=5),False)
    assert call(request())==original
    case('capacity_exhaustion_refuses_new_records_and_keeps_duplicate_identity')
    withdrawal={'format':PROFILE,'synthetic':True,'operation':'withdraw','withdrawal_token':token(2)}
    assert call(withdrawal)['removed'] is True and call(withdrawal)['removed'] is False
    call(request(),False);call(request(withdraw=5),False)
    assert sql('SELECT used FROM metadata_dev.invitations WHERE digest='+digest(1)+';')=='3'
    case('actual_withdrawal_does_not_refund_or_resurrect')
    issue(20,2)
    def submit_concurrently(n):
        # Submit distinct private files; only the SQL result is judged.
        return call(request(invite=20,withdraw=n),good=None,name='concurrent-'+str(n)+'.json')
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:results=list(pool.map(submit_concurrently,range(30,36)))
    assert sum(r is not None for r in results)==2
    assert sql('SELECT used FROM metadata_dev.invitations WHERE digest='+digest(20)+';')=='2'
    case('six_real_cli_processes_cannot_exceed_two_slots')
    # A linked/public request never reaches SQL and cannot alter rows.
    file=inputs/'hostile.json';file.write_text(json.dumps(request(invite=12,withdraw=40)));file.chmod(0o644)
    count=sql('SELECT count(*) FROM metadata_dev.feedback;')
    def refused_file():
        r=subprocess.run([sys.executable,str(ROOT/'scripts/research-admission.py'),'--sandbox-dir',str(directory),
            '--request',str(file)],capture_output=True,env=environment,timeout=12)
        assert r.returncode==1 and r.stderr==b'SYNTHETIC_ADMISSION_REFUSED\n' and not r.stdout
    refused_file();file.unlink();file.symlink_to(inputs/'input-1.json');refused_file();file.unlink()
    assert sql('SELECT count(*) FROM metadata_dev.feedback;')==count
    case('public_and_linked_private_request_files_refuse_before_mutation')
    snapshot=sql('SELECT row_to_json(t) FROM metadata_dev.invitations t;')+sql('SELECT row_to_json(t) FROM metadata_dev.feedback t;')+sql('SELECT row_to_json(t) FROM metadata_dev.invitation_claims t;')
    assert token(1) not in snapshot and token(2) not in snapshot
    assert sql('SELECT encode(digest,\'hex\') FROM metadata_dev.invitations WHERE digest='+digest(1)+';')==digest_token(token(1))
    counts=sql('SELECT count(*) FROM metadata_dev.feedback;')
    assert before==inventory()
    return {'captured_at':datetime.now(timezone.utc).isoformat(),'pass':True,'cases':CASES,
        'case_count':len(CASES),'sources':before,'source_unchanged_during_execution':True,
        'actual_feedback_rows':int(counts),'only_synthetic_records':True,'database_tcp_listening':False,
        'plaintext_tokens_in_database_or_public_report':False,
        'production_login_authentication_verified':False,'participant_consent_verified':False,
        'research_service_running':False,'production_database_changed':False,'new_endpoints':0,
        'independent_accuracy_evidence':False,'requirements_closed':0}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--sandbox-dir',required=True);a=p.parse_args()
    try:print(json.dumps(verify(a.sandbox_dir),indent=2))
    except (ValueError,OSError,AssertionError,AttributeError,KeyError,TypeError,subprocess.SubprocessError):
        print(json.dumps({'pass':False,'completed_cases':[c['case'] for c in CASES]}))
        print('Synthetic admission controls failed; no production acceptance.',file=sys.stderr);raise SystemExit(1)
