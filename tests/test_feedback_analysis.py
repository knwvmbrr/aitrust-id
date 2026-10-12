"""Descriptive record changes never become accuracy, people or training labels."""
import copy
import itertools
import json
import os
from pathlib import Path
import subprocess
import sys
import pytest
from tools import feedback_analysis as a
from tools.research_admission import CHOICES, FIXED

ROOT=Path(__file__).resolve().parents[1]
ROWS=[dict(FIXED,**dict(zip(CHOICES,values))) for values in itertools.product(*CHOICES.values())]

def batch(rows):return {'profile':a.PROFILE,'synthetic':True,'records':rows}

def test_all_eighty_accepted_metadata_combinations_and_denominators():
 out=a.compare(batch(ROWS),batch(ROWS*2))
 assert len(ROWS)==80 and len(out['comparisons'])==13
 assert not any(row['inspection_prompt'] or row['percentage_point_change'] for row in out['comparisons'])
 for state,n in [('before',80),('after',160)]:
  assert out[state]['records']==n and out[state]['unique_metadata_combinations']==80
  for counts in out[state]['categories'].values():assert sum(counts.values())==n
 assert out['after']['repeated_metadata_combinations']==80
 assert out['after']['records_in_repeated_combinations']==160
 assert not out['records_are_people'] and not out['repeated_metadata_establishes_duplicate_people']


def test_opposite_records_inspect_both_directions_at_exact_boundary():
 out=a.compare(batch([ROWS[0]]*20),batch([ROWS[-1]]*20),20,100)
 assert sum(row['inspection_prompt'] for row in out['comparisons'])==6
 assert {r['percentage_point_change'] for r in out['comparisons']}=={-100.,0.,100.}
 assert {r['direction'] for r in out['comparisons']}=={'increase','decrease','unchanged'}
 for key in ['accuracy_measured','anomaly_diagnosed','reports_are_verified_errors','independent_evidence','training_labels_created','network_used']:
  assert out[key] is False
 assert out['tags_asserted']==[]


def test_repeated_metadata_is_not_silently_deduplicated_or_counted_as_people():
 out=a.compare(batch([ROWS[0]]*30),batch([ROWS[0]]*20),1,1)
 assert out['before']['records']==30 and out['after']['records']==20
 assert out['before']['unique_metadata_combinations']==1
 assert out['before']['records_in_repeated_combinations']==30
 assert not any(row['inspection_prompt'] for row in out['comparisons'])


def test_fractional_rate_changes_use_exact_rule_before_display_rounding():
 out=a.compare(batch([ROWS[0],ROWS[-1],ROWS[-1]]),batch([ROWS[0],ROWS[0],ROWS[-1]]),1,33.333333)
 assert sum(r['inspection_prompt'] for r in out['comparisons'])==6
 assert {abs(r['percentage_point_change']) for r in out['comparisons']}=={0.,33.333333}
 stricter=a.compare(batch([ROWS[0],ROWS[-1],ROWS[-1]]),batch([ROWS[0],ROWS[0],ROWS[-1]]),1,33.333334)
 assert not any(r['inspection_prompt'] for r in stricter['comparisons'])


@pytest.mark.parametrize(('first','second'),[(19,20),(20,19),(1,5000)])
def test_selected_minimum_is_not_accuracy_or_a_release_gate(first,second):
 out=a.compare(batch([ROWS[0]]*first),batch([ROWS[-1]]*second),20,1)
 assert out['state']=='insufficient_records_for_selected_inspection_rule'
 assert not any(r['inspection_prompt'] for r in out['comparisons'])
 assert not out['accuracy_measured']


@pytest.mark.parametrize(('minimum','delta'),[(True,10),(0,10),(5001,10),(1.5,10),(None,10),
 (1,True),(1,0),(1,-1),(1,101),(1,float('nan')),(1,float('inf')),(1,10**1000),(1,None),(1,'10'),(1,0.123456789012345)])
def test_unknown_or_unbounded_inspection_rule_refuses(minimum,delta):
 with pytest.raises(a.AnalysisError):a.compare(batch(ROWS),batch(ROWS),minimum,delta)


@pytest.mark.parametrize('change',[
 lambda b:b.update(profile='unknown'),lambda b:b.update(synthetic=False),lambda b:b.update(synthetic=1),
 lambda b:b.update(records=[]),lambda b:b.update(records=ROWS*63),lambda b:b.update(records={}),
 lambda b:b.update(text='PRIVATE_CANARY'),lambda b:b.update(records=[None]),
 lambda b:b['records'][0].update(tag='PII_REDACTED'),lambda b:b['records'][0].update(method_version='context-v7'),
 lambda b:b['records'][0].update(schema_version=True),lambda b:b['records'][0].update(schema_version=1.),
 lambda b:b['records'][0].update(text='PRIVATE_CANARY'),lambda b:b['records'][0].update(withdrawal_token='PRIVATE_CANARY'),
 lambda b:b['records'][0].update(sharing='automatically_submitted'),lambda b:b['records'][0].update(feedback=[]),
 lambda b:b['records'][0].update(reported_result='unknown'),lambda b:b['records'][0].update(failure_category=None),
])
def test_mixed_real_unknown_or_private_payload_cannot_reach_analysis(change):
 value=batch([dict(ROWS[0])]);change(value)
 with pytest.raises(a.AnalysisError):a.parse(json.dumps(value).encode())
 with pytest.raises(a.AnalysisError):a.compare(value,batch(ROWS))


@pytest.mark.parametrize('raw',[b'',b'NaN',b'1e999',b'Infinity',b'\xff',b'{"a":1,"a":2}',b'['*1000,b' '*2000001])
def test_closed_bounded_bytes_contract(raw):
 with pytest.raises(a.AnalysisError):a.parse(raw)


def test_maximum_batch_supported_and_inputs_not_mutated_or_aliased():
 value=batch([dict(ROWS[0]) for _ in range(5000)]);before=json.dumps(value)
 result=a.compare(value,value,5000,100)
 assert result['before']['records']==5000 and json.dumps(value)==before
 captured=a.parse(json.dumps(value).encode());captured['records'][0]['feedback']=ROWS[-1]['feedback']
 assert value['records'][0]['feedback']==ROWS[0]['feedback']


@pytest.fixture
def private_cli(tmp_path):
 tmp_path.chmod(0o700)
 for name,records in [('before',[ROWS[0]]*20),('after',[ROWS[-1]]*20)]:
  f=tmp_path/(name+'.json');f.write_text(json.dumps(batch(records)));f.chmod(0o600)
 return tmp_path,[sys.executable,str(ROOT/'scripts/analyze-feedback.py'),'--before',str(tmp_path/'before.json'),'--after',str(tmp_path/'after.json')]


def invoke(command):return subprocess.run(command,capture_output=True,text=True,timeout=15,cwd=ROOT)


def test_actual_cli_counts_explicit_details_and_no_replacement(private_cli):
 base,command=private_cli;r=invoke(command);assert r.returncode==0 and not r.stderr
 public=json.loads(r.stdout);assert public['inspection_prompts']==6
 assert public['before_records']==public['after_records']==20
 assert not (base/'details').exists() and not public['accuracy_measured']
 r=invoke(command+['--details',str(base/'details')]);assert r.returncode==0
 f=base/'details/feedback-analysis.json';raw=f.read_bytes();details=json.loads(raw)
 assert len(details['comparisons'])==13 and not details['reports_are_verified_errors']
 assert f.stat().st_mode&0o777==0o600 and f.parent.stat().st_mode&0o777==0o700
 r=invoke(command+['--details',str(base/'details')]);assert r.returncode==2 and f.read_bytes()==raw
 assert str(base) not in r.stderr and not r.stdout


@pytest.mark.parametrize('unsafe',['public_file','public_parent','symlink','hardlink','fifo','invalid_utf8','oversize','duplicate_keys','private_text','real_batch'])
def test_actual_cli_refusal_does_not_echo_private_input(private_cli,unsafe):
 base,command=private_cli;f=base/'after.json'
 if unsafe=='public_file':f.chmod(0o644)
 elif unsafe=='public_parent':base.chmod(0o755)
 elif unsafe=='symlink':f.rename(base/'saved');f.symlink_to(base/'saved')
 elif unsafe=='hardlink':os.link(f,base/'linked')
 elif unsafe=='fifo':f.unlink();os.mkfifo(f,0o600)
 elif unsafe=='invalid_utf8':f.write_bytes(b'\xffPRIVATE_CANARY')
 elif unsafe=='oversize':f.write_bytes(b'PRIVATE_CANARY'+b'x'*2000000)
 elif unsafe=='duplicate_keys':f.write_text('{"records":"PRIVATE_CANARY","records":[]}')
 elif unsafe=='private_text':f.write_text(json.dumps(batch([dict(ROWS[0],text='PRIVATE_CANARY')])))
 elif unsafe=='real_batch':f.write_text(json.dumps(dict(batch([ROWS[0]]),synthetic=False)))
 r=invoke(command);assert r.returncode==2 and not r.stdout
 assert json.loads(r.stderr)['state']=='UNAVAILABLE'
 assert 'PRIVATE_CANARY' not in r.stderr and str(base) not in r.stderr


def test_argparse_refusal_has_no_value_echo(private_cli):
 _,command=private_cli;r=invoke(command+['--unknown','PRIVATE_CANARY'])
 assert r.returncode==2 and 'PRIVATE_CANARY' not in r.stderr


def test_real_practice_generation_then_actual_analyzer(tmp_path):
 tmp_path.chmod(0o700);target=tmp_path/'practice'
 command=[sys.executable,str(ROOT/'scripts/prepare-feedback-analysis-demo.py'),'--output',str(target)]
 created=invoke(command);assert created.returncode==0
 assert json.loads(created.stdout)['records_per_batch']==20 and not json.loads(created.stdout)['people_counted']
 captured={p.name:p.read_bytes() for p in target.iterdir()}
 analyzed=invoke([sys.executable,str(ROOT/'scripts/analyze-feedback.py'),'--before',str(target/'before.json'),'--after',str(target/'after.json')])
 assert analyzed.returncode==0 and json.loads(analyzed.stdout)['inspection_prompts']==6
 assert json.loads(analyzed.stdout)['synthetic_only']
 assert invoke(command).returncode==2
 assert {p.name:p.read_bytes() for p in target.iterdir()}==captured
 assert str(target) not in created.stdout+created.stderr+analyzed.stdout+analyzed.stderr


@pytest.mark.parametrize('unsafe',['public_parent','existing_symlink'])
def test_actual_practice_generation_refuses_unsafe_destination(tmp_path,unsafe):
 tmp_path.chmod(0o700);target=tmp_path/'practice'
 if unsafe=='public_parent':tmp_path.chmod(0o755)
 else:target.symlink_to(tmp_path/'elsewhere')
 result=invoke([sys.executable,str(ROOT/'scripts/prepare-feedback-analysis-demo.py'),'--output',str(target)])
 assert result.returncode==2 and not result.stdout
 assert not (tmp_path/'elsewhere').exists()
