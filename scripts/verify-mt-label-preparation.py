#!/usr/bin/env python3
"""Actual private CLI exercise with TWO SYNTHETIC rater files, not two people."""
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tools import mt_label_preparation as m

PATHS=(*m.SOURCES,'scripts/verify-mt-label-preparation.py','tests/test_mt_label_preparation.py',
       'docs/mt-label-preparation-plan.md','docs/mt-label-preparation.md')


def inventory():return {p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in PATHS}


def main():
    report={'captured_at':datetime.now(timezone.utc).isoformat(),'pass':False,
            'scope':'authored_two_synthetic_rater_cli_engineering_only','human_raters_executed':0,
            'human_labels_verified':False,'independence_verified':False,'predictions_run':False,
            'calibration_assessed':False,'accuracy_assessed':False,'release_approved':False,
            'original_requirements_closed':0,'stage':'prepare','cases':[]}
    try:
        before=inventory();report['sources_before']=before
        with tempfile.TemporaryDirectory(prefix='aitrust-mt-labels-') as private:
            base=Path(private).resolve();base.chmod(0o700)
            source=base/'private-input.json';packet=base/'packet'
            examples=[
                ('Leave now; smoke is entering this room.','The notice describes an evacuation drill.'),
                ('Agree now or we will publish your private notes.','A note says there is no time restriction on this choice.'),
                ('Either pay today or abandon the service.','The supplied contract permits a one-month pause.'),
                ('Experts agree.','The article quotes this wording as an example without adopting it.'),
                ('According to Report A [1], the schedule changed.','The reference is identified but has not been verified.'),
                ('Cafe\u0301 is open.','')]
            def save(path,value):path.write_bytes(m.encode(value));path.chmod(0o600)
            input_value={'profile':'mt-label-items/v1','language':'en','items':[
                {'id':'PrivateSource'+str(i),'text':text,'context':context} for i,(text,context) in enumerate(examples)]}
            save(source,input_value)
            def call(case,args,expected=0):
                result=subprocess.run([sys.executable,'-I','-S','-B',str(ROOT/'scripts/mt-label-preparation.py'),*args],
                    stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=10,cwd='/',
                    env={'PATH':os.defpath,'LANG':'C.UTF-8'})
                assert result.returncode==expected and not result.stderr and len(result.stdout)<100000
                assert str(base).encode() not in result.stdout and b'PrivateSource' not in result.stdout
                assert all(text.encode() not in result.stdout for text,_ in examples)
                value=json.loads(result.stdout)
                assert value['human_labels_verified'] is False and value['release_approved'] is False
                report['cases'].append({'id':case,'state':value['state'],'exit':result.returncode})
                return value
            common=['--items',str(source),'--packet',str(packet)]
            call('prepare',['prepare','--items',str(source),'--out',str(packet)])
            packet_before={p.name:p.read_bytes() for p in packet.iterdir()}
            assert packet.stat().st_mode&0o777==0o700
            assert all(p.stat().st_mode&0o777==0o600 for p in packet.iterdir())
            call('no_overwrite',['prepare','--items',str(source),'--out',str(packet)],2)
            assert packet_before=={p.name:p.read_bytes() for p in packet.iterdir()}
            returned=[]
            for slot in ('A','B'):
                form=json.loads((packet/('reviewer-'+slot+'.json')).read_bytes())
                assert all(row['label'] is None for item in form['items'] for row in item['annotations'].values())
                assert b'PrivateSource' not in m.encode(form)
                for item in form['items']:
                    index=int(item['id'][4:])-1
                    labels={
                        'pressure':['legitimate_urgency','contextual_pressure','ordinary_persuasion','no_relevant_pressure','no_relevant_pressure','no_relevant_pressure'],
                        'choice':['no_binary_frame','no_binary_frame','binary_omits_alternative','no_binary_frame','no_binary_frame','no_binary_frame'],
                        'authority':['no_authority_appeal','no_authority_appeal','no_authority_appeal','unattributed_authority_appeal','attributed_unverified','no_authority_appeal'],
                        'use_context':['used','used','used','quoted_or_mentioned','used','no_relevant_cue']}
                    for axis,row in item['annotations'].items():
                        label=labels[axis][index]
                        if slot=='B' and axis=='pressure' and index==2:label='uncertain'
                        if slot=='B' and axis=='authority' and index==3:label='insufficient_context'
                        row.update(label=label,reason='Authored synthetic file response; no independent human executed.',
                            text_spans=[[0,len(item['text'])]],
                            context_spans=[[0,len(item['context'])]] if label=='binary_omits_alternative' else [])
                path=base/('returned-'+slot+'.json');save(path,form);returned.append(path)
                call('validate_'+slot,['validate',*common,'--slot',slot,'--response',str(path)])
            report['stage']='compare'
            args=['compare',*common,'--a',str(returned[0]),'--b',str(returned[1])]
            result=call('compare_two_synthetic_files',[*args,'--out',str(base/'comparison')])
            assert result['state']=='COMPLETE' and set(result['axes'])==set(m.AXES)
            assert result['axes']['pressure']['coverage']['uncertain_rating_count']==1
            assert result['axes']['authority']['coverage']['insufficient_context_rating_count']==1
            assert result['private_review_queue_count']>=1
            assert all(s['candidate_comparison']=='UNADOPTED_CANDIDATE_ONLY' and not s['release_approved'] for s in result['axes'].values())
            report['agreement_observations']={axis:{'state':s['state'],'alpha':s['alpha'],'coverage':s['coverage'],
                'candidate_comparison':'UNADOPTED_CANDIDATE_ONLY'} for axis,s in result['axes'].items()}
            assert all(p.stat().st_mode&0o777==0o600 for p in (base/'comparison').iterdir())
            original=returned[0].read_bytes()
            incomplete=json.loads(original);incomplete['items'][0]['annotations']['pressure']['label']=None
            save(returned[0],incomplete)
            call('missing_answer',['validate',*common,'--slot','A','--response',str(returned[0])],2)
            returned[0].write_bytes(original)
            bad=json.loads(original);bad['items'][0]['text']+=' ALTERED';save(returned[0],bad)
            call('altered_form',['validate',*common,'--slot','A','--response',str(returned[0])],2)
            returned[0].write_bytes(original)
            old_source=source.read_bytes();changed=json.loads(old_source);changed['items'][-1]['text']='Café is open.';save(source,changed)
            call('raw_nfc_equivalent_source_changed',['validate',*common,'--slot','A','--response',str(returned[0])],2)
            source.write_bytes(old_source)
            returned[0].chmod(0o644)
            call('response_permission',['validate',*common,'--slot','A','--response',str(returned[0])],2)
            returned[0].chmod(0o600)
            call('recovery',['validate',*common,'--slot','A','--response',str(returned[0])])
            # Unanimous unknowns remain categories and zero decisive coverage;
            # constant nominal alpha stays Unavailable rather than perfect.
            for path in returned:
                form=json.loads(path.read_bytes())
                for item in form['items']:
                    for row in item['annotations'].values():row.update(label='uncertain',text_spans=[],context_spans=[])
                save(path,form)
            uncertain=call('constant_unknowns_not_validation',[*args,'--out',str(base/'uncertain-comparison')])
            assert all(s['state']=='UNAVAILABLE' and s['alpha'] is None and s['coverage']['decisive_rating_count']==0
                       for s in uncertain['axes'].values())
            assert uncertain['private_review_queue_count']==6
        assert not base.exists();after=inventory();assert before==after
        report['pass']=True;report['stage']='complete';report['case_count']=len(report['cases'])
        report['sources_after']=after;report['source_unchanged_during_execution']=True;report['temporary_private_files_removed']=True
    except BaseException:
        report['pass']=False;report['error']='synthetic_cli_workflow_failed'
    print(json.dumps(report,sort_keys=True,indent=2));return 0 if report['pass'] else 1


if __name__=='__main__':raise SystemExit(main())
