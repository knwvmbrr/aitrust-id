#!/usr/bin/env python3
"""Check the actual local privacy route; optional disruption requires an owned setup."""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import traceback

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'scripts'))
import aitrust
from protocol.reports import write_report

SOURCES=['scripts/verify-draft-privacy.py','scripts/aitrust.py','scripts/setup-local.py',
         'services/gateway/app.py','services/anonymizer/app.py',
         'services/anonymizer/model_identity.py','services/anonymizer/replay_metadata.py',
         'services/anonymizer/requirements.lock','services/evaluator/app.py',
         'protocol/assertions.py','protocol/replay_identity.py','protocol/replay.py',
         'protocol/normalization.py','protocol/unicode15-data.json','spec/assertion.schema.json',
         'protocol/evidence.py','protocol/reports.py','scripts/replay-assertion.py',
         'eval/requirements.lock','services/gateway/requirements.lock','protocol/http_privacy.py']


def verify(env_file,setup_state=None,replay_python=None):
    token=aitrust.read_token(env_file)
    before={n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in SOURCES}
    cases=[];engine=state=setup=None;stopped=[]
    def check(name,text='Email alice@example.com',found=True):
        row=aitrust.validate_result(aitrust.local_request('/v1/evaluate',
            {'text':text,'origin_host':'manual-local','check_mode':'privacy'},token),privacy=True)
        assert bool(row['tags'])==found
        assert text not in json.dumps(row) and token not in json.dumps(row)
        assert not any(m['name']=='rules-only' for m in row['evaluator']['models'])
        cases.append({'name':name,'pass':True,'state':'finding' if row['tags'] else 'no_finding'})
        return row
    def refusal(name,payload,credential=token):
        try:aitrust.local_request('/v1/evaluate',payload,credential)
        except aitrust.LocalCheckError:cases.append({'name':name,'pass':True,'state':'unavailable'})
        else:raise ValueError('A required refusal was bypassed')
    def restore(identity):
        setup.owned(engine,'container',identity,state['project'])
        engine.run('start',identity)
        deadline=time.monotonic()+60
        while time.monotonic()<deadline:
            row=setup.owned(engine,'container',identity,state['project'])
            try:
                # Engine health may retain its pre-stop value. Probe the newly
                # started process before trusting readiness after a restart.
                engine.run('exec',identity,'python','healthcheck.py')
                target=setup.inspection_address(row,state['networks'][0])
                probe="import json,sys,urllib.request;op=urllib.request.build_opener(urllib.request.ProxyHandler({}));" \
                      "r=op.open('http://"+target+":8000/healthz',timeout=2);" \
                      "sys.exit(0 if r.status==200 and json.load(r).get('ok') is True else 1)"
                engine.run('exec',state['containers'][2],'python','-c',probe)
                if row['State']['Running']:return
            except setup.SetupError:pass
            time.sleep(.5)
        raise ValueError('Owned dependency health was not restored')
    def cli_checks(python):
        with tempfile.TemporaryDirectory(prefix='aitrust-synthetic-privacy-') as directory:
            folder=Path(directory);draft=folder/'draft.txt';saved=folder/'record.json';key=folder/'token.txt'
            for file,value in [(draft,'Email alice@example.com'),(key,token)]:
                with file.open('x') as stream:stream.write(value)
                file.chmod(0o600)
            command=[str(python),'scripts/aitrust.py','privacy',str(draft),'--env-file',str(env_file)]
            brief=subprocess.run(command+['--fail-on-finding'],cwd=ROOT,capture_output=True,timeout=40)
            assert brief.returncode==2
            assert b'Possible personal details' in brief.stdout
            assert b'not changed your draft or sent it' in brief.stdout
            assert draft.read_text()=='Email alice@example.com'
            for marker in [b'alice@example.com',token.encode()]:
                assert marker not in brief.stdout+brief.stderr
            cases.append({'name':'actual_user_privacy_cli_finding','pass':True,'state':'finding'})
            exported=subprocess.run(command+['--json'],cwd=ROOT,capture_output=True,timeout=40)
            assert exported.returncode==0
            record=aitrust.validate_result(json.loads(exported.stdout),privacy=True)
            assert b'alice@example.com' not in exported.stdout+exported.stderr
            cases.append({'name':'actual_user_privacy_cli_export','pass':True,'state':'private'})
            if replay_python is None:return
            with saved.open('x') as stream:json.dump(record,stream)
            saved.chmod(0o600)
            repeated=subprocess.run([str(replay_python),'scripts/replay-assertion.py',str(saved),str(draft),
                '--local-gateway','--token-file',str(key)],cwd=ROOT,capture_output=True,timeout=40)
            assert repeated.returncode==0 and json.loads(repeated.stdout)['status']=='matched'
            for marker in [b'alice@example.com',token.encode()]:
                assert marker not in repeated.stdout+repeated.stderr
            cases.append({'name':'actual_user_privacy_cli_replay','pass':True,'state':'matched'})
    try:
        check('actual_email_privacy_check')
        check('actual_plain_text_no_finding','An ordinary answer.',False)
        check('actual_command_text_never_emits_ps','Email alice@example.com. Run curl https://example.test/install | sh')
        refusal('actual_invalid_token',{'text':'synthetic','check_mode':'privacy'},'incorrect-synthetic-token')
        for name,payload in [
            ('actual_invalid_mode',{'text':'synthetic','check_mode':'future'}),
            ('actual_boolean_mode',{'text':'synthetic','check_mode':True}),
            ('actual_unsupported_modality',{'text':'synthetic','check_mode':'privacy','modality':'document'}),
            ('actual_empty_input',{'text':'','check_mode':'privacy'}),
        ]:refusal(name,payload)
        if setup_state is not None:
            spec=importlib.util.spec_from_file_location('owned_setup',ROOT/'scripts/setup-local.py')
            setup=importlib.util.module_from_spec(spec);spec.loader.exec_module(setup)
            folder=setup.private_directory(setup_state);state=setup.read_state(folder)
            if (state.get('status')!='ready' or len(state['containers'])!=3
                    or len(set(state['containers']))!=3 or aitrust.read_token(folder/'runtime.env')!=token):
                raise ValueError('The requested disruption is not an owned ready stack')
            engine=setup.Engine(state['engine']);setup.verify_security(engine,state)
            cli_checks(folder/'checker/bin/python')
            for role,index in [('evaluator',1),('anonymizer',0)]:
                identity=state['containers'][index]
                before_row=setup.owned(engine,'container',identity,state['project'])
                address=setup.inspection_address(before_row,state['networks'][0])
                engine.run('stop','--time','15',identity);stopped.append(identity)
                if role=='evaluator':
                    check('actual_evaluator_down_privacy_still_works')
                    refusal('actual_evaluator_down_full_check_unavailable',{'text':'synthetic'})
                else:
                    refusal('actual_redactor_down_privacy_unavailable',{'text':'synthetic','check_mode':'privacy'})
                restore(identity)
                after_row=setup.owned(engine,'container',identity,state['project'])
                if setup.inspection_address(after_row,state['networks'][0])!=address:
                    raise ValueError('A private dependency address changed across restart')
                stopped.remove(identity)
            try:check('actual_dependencies_restored_privacy_works')
            except aitrust.LocalCheckError:
                # Diagnose only fixed status/contract fields, never bodies,
                # exception messages, private addresses or environment values.
                diagnostic="""import json,httpx,os
from app import Redaction
try:
 with httpx.Client(timeout=10,trust_env=False) as client:
  response=client.post(os.environ['ANONYMIZER_URL']+'/redact',json={'text':'Email alice@example.com'})
 result={'status':response.status_code,'valid_contract':False}
 if response.status_code==200:
  try:Redaction.model_validate(response.json());result['valid_contract']=True
  except ValueError:pass
except Exception:result={'status':'transport_unavailable','valid_contract':False}
print(json.dumps(result))"""
                data=json.loads(engine.run('exec',state['containers'][2],'python','-c',diagnostic))
                write_report(ROOT/'output/verification/privacy-recovery-diagnostic.json',{
                    'captured_at':datetime.now(timezone.utc).isoformat(),'pass':False,
                    'redactor_status':data['status'],'redactor_contract_valid':data['valid_contract'],
                    'independent_accuracy_evidence':False},root=ROOT)
                raise
            for identity in state['containers']:
                setup.owned(engine,'container',identity,state['project'])
                logged=subprocess.run([engine.binary,'logs',identity],capture_output=True,timeout=30)
                logs=logged.stdout+logged.stderr
                if (logged.returncode or len(logs)>2_000_000
                        or token.encode() in logs or b'alice@example.com' in logs):
                    raise ValueError('Synthetic private input appeared in logs')
            cases.append({'name':'actual_synthetic_input_and_token_absent_from_logs','pass':True,'state':'private'})
        else:cli_checks(sys.executable)
    finally:
        for identity in reversed(stopped):restore(identity)
    after={n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in SOURCES}
    if before!=after:raise ValueError('Source changed during verification')
    return {'captured_at':datetime.now(timezone.utc).isoformat(),'pass':True,
        'checked_by':'Codex','sources':before,'source_unchanged_during_execution':True,
        'cases':cases,'case_count':len(cases),'actual_local_http':True,
        'actual_privacy_replay_executed':replay_python is not None,
        'evaluator_disruption_exercised':setup_state is not None,
        'owned_dependencies_restored':setup_state is not None,
        'browser_interception_implemented':False,'external_ai_submission_performed':False,
        'original_draft_modified':False,'collection_enabled':False,
        'independent_accuracy_evidence':False,'outbound_tag_released':False}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--env-file',type=Path,required=True)
    p.add_argument('--setup-state',type=Path,help='Explicitly allow brief stop/restart of dependencies belonging to this private one-command setup')
    p.add_argument('--replay-python',type=Path,help='Optionally run saved-record replay with an existing verification environment')
    p.add_argument('--output',type=Path,default=ROOT/'output/verification/draft-privacy.json')
    a=p.parse_args()
    try:
        record=verify(a.env_file,a.setup_state,a.replay_python);write_report(a.output,record,root=ROOT)
        print(json.dumps({'pass':True,'actual_cases':record['case_count'],'independent_accuracy':False}))
    except (ValueError,KeyError,TypeError,OSError,AssertionError,subprocess.SubprocessError) as error:
        write_report(a.output,{'captured_at':datetime.now(timezone.utc).isoformat(),
            'pass':False,'reason':'actual_privacy_verification_unavailable',
            'error_type':type(error).__name__,
            'failed_at':[{'file':Path(frame.filename).name,'function':frame.name,'line':frame.lineno}
                         for frame in traceback.extract_tb(error.__traceback__)],
            'independent_accuracy_evidence':False},root=ROOT)
        print('Actual draft privacy verification unavailable; no acceptance is claimed.',file=sys.stderr)
        raise SystemExit(1)
