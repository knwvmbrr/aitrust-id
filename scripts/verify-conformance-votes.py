#!/usr/bin/env python3
"""Run the real offline ballot CLI on invented keys and scope, not actual governance."""
from datetime import datetime,timezone
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
from test_conformance_recusal import fixtures,canonical,encode,sha
from protocol.reports import write_report
SOURCES=('tools/conformance_recusal.py','scripts/check-conformance-votes.py','scripts/verify-conformance-votes.py',
         'tests/test_conformance_recusal.py','protocol/corpus.py','protocol/evidence.py','protocol/normalization.py',
         'protocol/unicode15-data.json','GOVERNANCE.md')


def verify():
    before={n:sha((ROOT/n).read_bytes()) for n in SOURCES};cases=[]
    with tempfile.TemporaryDirectory(prefix='aitrust-recusal-') as temporary:
        base=Path(temporary).resolve();base.chmod(0o700)
        def run(name,change=None,choice='approve',expected=0,raw_override=None):
            now,key,r,d,sign=fixtures()
            if change:change(r,d)
            ballot=sign(choice)
            values={'roster':canonical(r),'decision':canonical(d),'ballots':canonical([ballot])}
            files={n:base/n for n in values}
            for n,raw in values.items():
                files[n].unlink(missing_ok=True);files[n].write_bytes(raw);files[n].chmod(0o600)
            pins={n:sha(values[n]) for n in ['roster','decision']}
            if raw_override:raw_override(files,values,ballot)
            saved={n:p.read_bytes() for n,p in files.items() if p.is_file() and not p.is_symlink()}
            proc=subprocess.run([sys.executable,str(ROOT/'scripts/check-conformance-votes.py'),str(files['ballots']),
                '--roster',str(files['roster']),'--roster-sha256',pins['roster'],
                '--decision',str(files['decision']),'--decision-sha256',pins['decision']],capture_output=True,timeout=15,cwd=ROOT)
            result=json.loads(proc.stdout)
            assert proc.returncode==expected and not proc.stderr,name
            assert str(base).encode() not in proc.stdout and b'PRIVATE_CANARY' not in proc.stdout,name
            assert result['certification_granted'] is False and result['RFC_adoption_granted'] is False,name
            assert all(files[n].read_bytes()==raw for n,raw in saved.items()),name
            cases.append({'name':name,'pass':True,'exit_code':expected,'input_bytes_unchanged':True,
                          'output_sha256':sha(proc.stdout)})
        conflict=lambda r,d:r['members'][0].update(commercial_interests=['fixture-project'])
        run('unconflicted_approval');run('unconflicted_rejection',choice='reject')
        run('explicit_conflicted_recusal',conflict,'recuse')
        run('conflicted_approval_refused',conflict,expected=1)
        run('conflicted_abstention_refused',conflict,'abstain',1)
        run('unrelated_interest',lambda r,d:r['members'][0].update(commercial_interests=['other-project']))
        run('withheld_disclosure_refused',lambda r,d:r['members'][0].update(disclosure='withheld'),expected=1)
        run('unfilled_role_refused',lambda r,d:r['members'][0].update(assignment='unfilled'),expected=1)
        run('observer_refused',lambda r,d:r['members'][0].update(role='observer'),expected=1)
        run('voluntary_recusal_without_disclosure',lambda r,d:r['members'][0].update(disclosure='withheld'),'recuse')
        def alter_ballot(files,values,b):
            b['choice']='reject';files['ballots'].write_bytes(canonical([b]))
        run('tampered_signed_choice_refused',expected=2,raw_override=alter_ballot)
        run('decision_pin_tampering_refused',expected=2,raw_override=lambda f,v,b:f['decision'].write_bytes(v['decision']+b' '))
        run('roster_pin_tampering_refused',expected=2,raw_override=lambda f,v,b:f['roster'].write_bytes(v['roster']+b' '))
        run('duplicate_member_ballot_refused',expected=2,raw_override=lambda f,v,b:f['ballots'].write_bytes(canonical([b,b])))
        run('private_text_field_refused',expected=2,raw_override=lambda f,v,b:f['ballots'].write_bytes(canonical([dict(b,text='PRIVATE_CANARY')])))
        run('oversize_ballots_refused',expected=2,raw_override=lambda f,v,b:f['ballots'].write_bytes(b'x'*524289))
        run('duplicate_json_refused',expected=2,raw_override=lambda f,v,b:f['ballots'].write_bytes(b'[{"profile":"a","profile":"b"}]'))
        def linked(files,values,b):
            target=base/'link-target';target.write_bytes(values['ballots']);files['ballots'].unlink();files['ballots'].symlink_to(target)
        run('linked_ballots_refused',expected=2,raw_override=linked)
        def fifo(files,values,b):files['ballots'].unlink();os.mkfifo(files['ballots'])
        run('fifo_ballots_refused',expected=2,raw_override=fifo)
    assert before=={n:sha((ROOT/n).read_bytes()) for n in SOURCES}
    return {'captured_at':datetime.now(timezone.utc).isoformat(),'pass':True,'cases':cases,'sources':before,
            'platform':sys.platform,'python':sys.version.split()[0],'synthetic_keys_and_roles_only':True,
            'actual_cli_executed':True,'source_unchanged_during_execution':True,'private_directory_removed':not base.exists(),
            'real_role_assignments':False,'operating_institution':False,'certification_granted':False,
            'independent_people_verified':False,'independent_accuracy_evidence':False}


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',required=True);a=p.parse_args()
    try:r=verify()
    except (ValueError,AssertionError,OSError,subprocess.SubprocessError):
        r={'captured_at':datetime.now(timezone.utc).isoformat(),'pass':False,'reason':'conformance_recusal_controls_failed',
           'operating_institution':False,'certification_granted':False,'independent_accuracy_evidence':False}
    write_report(a.output,r);print(json.dumps(r));raise SystemExit(0 if r['pass'] else 1)
