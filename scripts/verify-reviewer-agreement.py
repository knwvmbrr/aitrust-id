#!/usr/bin/env python3
"""Execute actual bounded agreement CLI cases; no labels are invented for a release."""
import argparse,hashlib,json,os,socket,subprocess,sys,tempfile
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from protocol.reports import write_report
SOURCES=['tools/reviewer_agreement.py','scripts/reviewer-agreement.py','scripts/verify-reviewer-agreement.py','protocol/evidence.py','protocol/reports.py']
PROGRESS={'current_case':'namespace_boundary','completed_cases':[]}
OUTPUT=None

def main():
    global OUTPUT
    PROGRESS.update(current_case='namespace_boundary',completed_cases=[])
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--require-isolated-linux',action='store_true');p.add_argument('--output');a=p.parse_args();OUTPUT=a.output
    isolated=False
    if a.require_isolated_linux:
        if sys.platform!='linux' or os.geteuid()==0:raise ValueError('Isolated ordinary-user Linux required')
        devices={s.split(':')[0].strip() for s in Path('/proc/net/dev').read_text().splitlines() if ':' in s}
        if devices!={'lo'} or len(Path('/proc/net/route').read_text().splitlines())>1:raise ValueError('Separate network namespace required')
        try:
            with socket.create_connection(('1.1.1.1',443),timeout=.5):raise ValueError('Unexpected egress')
        except OSError:isolated=True
    inventory=lambda:{n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in SOURCES};before=inventory();cases=[]
    data={'schema_version':1,'kind':'nominal_agreement_ratings','target_tag':'MT','reviewers':['PRIVATE_REVIEWER_CANARY','OtherReviewer'],
        'categories':['First','Second'],'units':[{'id':'PRIVATE_UNIT_CANARY'+str(i),'ratings':{'PRIVATE_REVIEWER_CANARY':v,'OtherReviewer':v}} for i,v in enumerate(['First','Second','First','Second'])]}
    with tempfile.TemporaryDirectory(prefix='aitrust-agreement-private-') as folder:
        folder=Path(folder).resolve();source=folder/'ratings.json'
        def check(name,raw,code,state,extra=()):
            PROGRESS['current_case']=name;source.write_bytes(raw)
            r=subprocess.run([sys.executable,str(ROOT/'scripts/reviewer-agreement.py'),str(source),*extra],capture_output=True,timeout=5)
            assert r.returncode==code and not r.stderr and b'PRIVATE_' not in r.stdout
            result=json.loads(r.stdout);assert result['state']==state and result['release_approved'] is False and result['independence_verified'] is False
            cases.append({'case':name,'pass':True});PROGRESS['completed_cases'].append(name);return result
        raw=json.dumps(data).encode();result=check('perfect_nominal_not_release',raw,0,'AVAILABLE');assert result['alpha']['exact_fraction']=='1/1' and result['candidate_is_adopted'] is False
        constant=json.loads(raw)
        for u in constant['units']:u['ratings']={k:'First' for k in constant['reviewers']}
        check('constant_undefined_not_perfect',json.dumps(constant).encode(),2,'UNAVAILABLE')
        solo=json.loads(raw)
        for u in solo['units']:u['ratings']['OtherReviewer']=None
        check('one_reviewer_cannot_create_agreement',json.dumps(solo).encode(),2,'UNAVAILABLE')
        extra=json.loads(raw);extra['example_text']='PRIVATE_EXAMPLE_CANARY';check('unexpected_content_field_refused',json.dumps(extra).encode(),2,'UNAVAILABLE')
        duplicate=raw[:-1]+b',"target_tag":"MT"}';check('duplicate_json_refused',duplicate,2,'UNAVAILABLE')
        check('invalid_utf8_refused',b'\xff PRIVATE_SECRET_CANARY',2,'UNAVAILABLE')
        check('input_limit_refused',b'x'*2_000_001,2,'UNAVAILABLE')
        check('deep_invalid_structure_refused',b'{"units":'+b'['*100+b'null'+b']'*100+b'}',2,'UNAVAILABLE')
        source.write_bytes(raw);link=folder/'ratings-link.json';link.symlink_to(source);PROGRESS['current_case']='symlink_input_refused'
        r=subprocess.run([sys.executable,str(ROOT/'scripts/reviewer-agreement.py'),str(link)],capture_output=True,timeout=5);assert r.returncode==2 and not r.stderr and b'PRIVATE_' not in r.stdout;cases.append({'case':'symlink_input_refused','pass':True});PROGRESS['completed_cases'].append('symlink_input_refused')
        report=ROOT/'output/verification'/('agreement-'+os.urandom(12).hex()+'.json');PROGRESS['current_case']='explicit_aggregate_report'
        try:
            check('explicit_aggregate_report',raw,0,'AVAILABLE',('--output',str(report)));saved=json.loads(report.read_text());assert saved['alpha']['value']==1 and 'PRIVATE_' not in report.read_text()
        finally:report.unlink(missing_ok=True)
        result=check('unsafe_output_destination_refused',raw,2,'UNAVAILABLE',('--output','../private-report.json'));assert result['reason']=='aggregate_report_not_saved'
        retained=ROOT/'runs'/('agreement-control-'+os.urandom(12).hex()+'.json');PROGRESS['current_case']='retained_report_cannot_be_overwritten'
        try:
            check('retained_report_first_write',raw,0,'AVAILABLE',('--output',str(retained)))
            saved=retained.read_bytes()
            result=check('retained_report_cannot_be_overwritten',raw,2,'UNAVAILABLE',('--output',str(retained)))
            assert result['reason']=='aggregate_report_not_saved' and retained.read_bytes()==saved
        finally:retained.unlink(missing_ok=True)
    assert before==inventory()
    result={'captured_at':datetime.now(timezone.utc).isoformat(),'pass':True,'kind':'synthetic_agreement_cli_controls','case_count':len(cases),'cases':cases,'sources':before,'source_unchanged_during_execution':True,'isolated_linux':isolated,'external_canary_blocked':True if isolated else None,'nonroot_execution':os.geteuid()!=0,'only_authored_synthetic_inputs':True,'human_ratings_used':False,'independent_accuracy_evidence':False,'release_approved':False}
    if a.output:write_report(a.output,result)
    print(json.dumps(result,indent=2))
if __name__=='__main__':
    try:main()
    except (ValueError,OSError,AssertionError,subprocess.SubprocessError) as exc:
        result={'captured_at':datetime.now(timezone.utc).isoformat(),'pass':False,**PROGRESS,'failure_kind':type(exc).__name__,'independent_accuracy_evidence':False,'release_approved':False}
        if OUTPUT:write_report(OUTPUT,result)
        print('Agreement CLI controls failed; no release acceptance.',file=sys.stderr);raise SystemExit(1)
