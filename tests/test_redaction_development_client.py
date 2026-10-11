"""Development diagnostic rejects stale sources and corrupt engine results."""
import copy,importlib.util,json,hashlib,sys
from pathlib import Path
from unittest.mock import patch
import pytest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
spec=importlib.util.spec_from_file_location('client',ROOT/'scripts/measure-redaction-development.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
fixture=json.loads((ROOT/m.FIXTURE).read_text())
observed=json.loads((ROOT/'runs/2026-10-11-pii-labels-recognition.json').read_text())
INSPECTION=[{'Config':{'User':'10001:10001','Labels':{'com.docker.compose.project':'aitrust-staging'}},'State':{'Running':True}}]
def engine_result():return {k:copy.deepcopy(observed[k]) for k in ['captured_at','pass','kind','rows','redactor_identity','sources','fixture_sha256','source_unchanged','independent_accuracy_evidence','real_user_data','production_services_modified']}
def test_actual_development_fixture_recomputes_baseline_error():
 result=m.summarize_observations(engine_result(),fixture,observed['sources'])
 assert result['slices']['en']['fn']==0
 assert result['redaction_coverage'][0]['masking_is_not_privacy_clearance']
 assert result['slices']['out_of_coverage']['fn']==2
 assert not result['privacy_clearance']
def test_engine_call_is_fixed_staging_only_no_user_file_argument():
 with patch.object(m,'invoke',side_effect=[copy.deepcopy(INSPECTION),engine_result()]) as invoke:
  result=m.measure('podman')
 assert invoke.call_args_list[0].args[0]==['podman','inspect','aitrust-staging_anonymizer_1']
 assert invoke.call_args_list[1].args[0][:5]==['podman','exec','-i','aitrust-staging_anonymizer_1','python']
 assert not result['http_route_tested'] and not result['candidate_recognizer_override']
@pytest.mark.parametrize('mutate',[
 lambda r:r.update(real_user_data=True),lambda r:r.update(pass_=True),
 lambda r:r.update(independent_accuracy_evidence=True),lambda r:r.update(source_unchanged=False),
 lambda r:r.update(production_services_modified=True),lambda r:r['sources'].update(app='a'*64),
 lambda r:r.update(fixture_sha256='a'*64),lambda r:r['redactor_identity'].update(sha256='a'*64),
 lambda r:r['rows'].pop(),lambda r:r['rows'].append(copy.deepcopy(r['rows'][0])),
 lambda r:r['rows'].__setitem__(0,copy.deepcopy(r['rows'][1])),
 lambda r:r['rows'][0].update(text='private'),lambda r:r['rows'][0].update(redaction_changed=1),
 lambda r:r['rows'][0].update(expected_literal_values_still_present=True),
 lambda r:r['rows'][0].update(expected_literal_values_still_present=-1),
 lambda r:r['rows'][0]['predicted'].append({'entity':'EMAIL_ADDRESS','start':True,'end':1}),
 lambda r:r['rows'][0]['applied'].append({'entity':'PERSON','start':0,'end':2001}),
 lambda r:r['rows'].__setitem__(0,'private'),
])
def test_corrupt_engine_observations_cannot_produce_chart(mutate):
 r=engine_result();mutate(r)
 with patch.object(m,'invoke',side_effect=[copy.deepcopy(INSPECTION),r]),pytest.raises((ValueError,TypeError)):
  m.measure('podman')
@pytest.mark.parametrize('mutate',[
 lambda d:d['Config'].update(User='0:0'),lambda d:d['State'].update(Running=False),
 lambda d:d['Config']['Labels'].update({'com.docker.compose.project':'production'}),
 lambda d:d['Config'].update(Labels=None),lambda d:d.update(Config=None),lambda d:d.update(State=None),
])
def test_wrong_project_or_privileges_refused_before_engine_execution(mutate):
 d=copy.deepcopy(INSPECTION);mutate(d[0])
 with patch.object(m,'invoke',return_value=d) as invoke,pytest.raises(ValueError):m.measure('podman')
 assert invoke.call_count==1
def test_source_symlink_is_refused(tmp_path):
 (tmp_path/'link').symlink_to(ROOT/'scripts/measure-redaction-development.py')
 with patch.object(m,'ROOT',tmp_path),pytest.raises(ValueError):m.source_bytes('link')
def test_source_directory_refused(tmp_path):
 (tmp_path/'directory').mkdir()
 with patch.object(m,'ROOT',tmp_path),pytest.raises(ValueError):m.source_bytes('directory')
def test_source_size_bounded(tmp_path):
 (tmp_path/'big').write_bytes(b'x'*2_000_001)
 with patch.object(m,'ROOT',tmp_path),pytest.raises(ValueError):m.source_bytes('big')

def test_inspection_array_uses_bounded_unique_json_not_object_only_reader():
 assert m.invoke([sys.executable,'-c','print("[]")'])==[]
@pytest.mark.parametrize('raw',['{"a":1,"a":2}','{"a":NaN}','{"a":1e999}','"\\ud800"','['*70+'0'+']'*70,'not json'])
def test_actual_child_parser_refuses_duplicate_nonfinite_nonscalar_deep_or_invalid_json(raw):
 with pytest.raises((ValueError,UnicodeError)):
  m.invoke([sys.executable,'-c','import sys;sys.stdout.write(sys.argv[1])',raw])
def test_actual_child_nonzero_is_refused_without_stdout_or_error_reflection():
 with pytest.raises(ValueError,match='^Staging diagnostic unavailable$'):
  m.invoke([sys.executable,'-c','import sys;print("synthetic_private_marker");sys.exit(1)'])
def test_actual_child_output_limit_is_enforced():
 with pytest.raises(ValueError,match='^Staging diagnostic unavailable$'):
  m.invoke([sys.executable,'-c','import sys;sys.stdout.write("x"*2000001)'])


@pytest.mark.parametrize('profile',['private.json','../../other-corpus',''])
def test_unregistered_profile_is_refused_before_any_engine_call(monkeypatch,profile):
    monkeypatch.setattr(m,'invoke',lambda *a,**k:pytest.fail('Engine must not run for an unregistered profile'))
    with pytest.raises(ValueError):m.measure('podman',profile)
