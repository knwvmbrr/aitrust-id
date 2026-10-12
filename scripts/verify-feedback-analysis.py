#!/usr/bin/env python3
"""Execute invented metadata analysis and real CLI privacy controls, never accuracy."""
from datetime import datetime,timezone
import hashlib
import itertools
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import os
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tools import feedback_analysis as analysis
from tools.research_admission import CHOICES,FIXED
from protocol.reports import write_report

SOURCES=('tools/feedback_analysis.py','tools/research_admission.py','tools/blind_review_io.py',
 'scripts/analyze-feedback.py','scripts/prepare-feedback-analysis-demo.py','scripts/verify-feedback-analysis.py','tests/test_feedback_analysis.py')

def hashes():return {name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in SOURCES}

def verify():
 before=hashes();controls=[]
 rows=[dict(FIXED,**dict(zip(CHOICES,values))) for values in itertools.product(*CHOICES.values())]
 batch=lambda values:{'profile':analysis.PROFILE,'synthetic':True,'records':values}
 with tempfile.TemporaryDirectory(prefix='aitrust-feedback-analysis-') as temporary:
  base=Path(temporary).resolve();base.chmod(0o700)
  for name,records in [('before',[rows[0]]*20),('after',[rows[-1]]*20)]:
   f=base/(name+'.json');f.write_text(json.dumps(batch(records)));f.chmod(0o600)
  prepared=subprocess.run([sys.executable,str(ROOT/'scripts/prepare-feedback-analysis-demo.py'),'--output',str(base/'practice')],capture_output=True,timeout=15,cwd=ROOT)
  assert prepared.returncode==0 and not prepared.stderr and str(base).encode() not in prepared.stdout
  assert json.loads(prepared.stdout)['records_per_batch']==20
  controls.append({'case':'actual_private_practice_generator','pass':True,'exit_status':0})
  command=[sys.executable,str(ROOT/'scripts/analyze-feedback.py'),'--before',str(base/'before.json'),'--after',str(base/'after.json')]
  def run(name,extra=(),code=0):
   r=subprocess.run(command+list(extra),capture_output=True,timeout=15,cwd=ROOT)
   assert r.returncode==code and str(base).encode() not in r.stdout+r.stderr and b'PRIVATE_CANARY' not in r.stdout+r.stderr,name
   if code:assert not r.stdout and json.loads(r.stderr)['state']=='UNAVAILABLE',name
   else:assert not r.stderr and not json.loads(r.stdout)['accuracy_measured'] and json.loads(r.stdout)['synthetic_only'],name
   controls.append({'case':name,'pass':True,'exit_status':code});return r
  assert json.loads(run('actual_counts_and_explicit_inspection_prompts').stdout)['inspection_prompts']==6
  run('new_private_details',['--details',str(base/'details')]);f=base/'details/feedback-analysis.json';captured=f.read_bytes()
  run('existing_details_refused',['--details',str(base/'details')],2);assert captured==f.read_bytes()
  assert not f.stat().st_mode&0o077 and not f.parent.stat().st_mode&0o077
  assert json.loads(run('insufficient_count_rule',['--minimum-records','21']).stdout)['inspection_prompts']==0
  run('nonfinite_rule_refused',['--percentage-points','nan'],2)
  f=base/'after.json';saved=f.read_bytes();f.write_text(json.dumps(batch([dict(rows[0],text='PRIVATE_CANARY')])));run('extra_private_text_refused',code=2);f.write_bytes(saved)
  f.chmod(0o644);run('public_input_refused',code=2);f.chmod(0o600)
  link=base/'linked';os.link(f,link);run('hardlinked_input_refused',code=2);link.unlink()
  f.write_bytes(b'\xffPRIVATE_CANARY');run('invalid_utf8_refused',code=2)
  (base/'before.json').write_text(json.dumps(batch(rows)))
  (base/'after.json').write_text(json.dumps(batch(rows*2)))
  all_choices=json.loads(run('all_eighty_combinations_with_unequal_denominators').stdout)
  assert all_choices['before_records']==80 and all_choices['after_records']==160 and all_choices['inspection_prompts']==0
 assert before==hashes() and not base.exists()
 return {'captured_at':datetime.now(timezone.utc).isoformat(),'pass':True,'sources':before,
  'source_unchanged_during_execution':True,'controls':controls,'metadata_combinations_exercised':80,
  'synthetic_only':True,'actual_participant_data':False,'private_test_files_removed':True,
  'accuracy_measured':False,'people_counted':False,'anomaly_diagnosed':False,'training_labels_created':False,
  'new_endpoints':0,'production_changes':False,'requirements_closed':0}

if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 proof=verify();write_report(a.output,proof)
 print(json.dumps({'pass':True,'actual_cli_controls':len(proof['controls']),'requirements_closed':0}))
