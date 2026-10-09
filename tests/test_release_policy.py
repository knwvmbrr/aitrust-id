import importlib.util
import os
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]
def module(path):
    spec=importlib.util.spec_from_file_location(path.replace('/','_'),ROOT/path)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
os.environ['AITRUST_TOKEN']='test-only-token-at-least-32-characters'
gateway=module('services/gateway/app.py')
evaluator=module('services/evaluator/app.py')
harness=module('eval/harness.py')

def test_evaluator_excludes_hp():
    assert evaluator.signals(evaluator.Doc(text='2020 2021 2022 2023 2024'))['candidates']==[]

def test_gateway_rejects_nonproduction_even_at_full_confidence():
    withheld=['NF','FI','HP','MT','IV','FA','PA','UNK','PII_REDACTED']
    candidates=[{'code':c,'confidence':1,'signals':[]} for c in withheld]
    tags,abstentions=gateway.calibrate(candidates)
    # 1. nothing outside the production allowlist may assert, at any confidence
    assert tags==[]
    # 2. and nothing may vanish: each withheld code leaves an auditable record
    recorded={a['code']:a['reason'] for a in abstentions}
    assert set(recorded)==set(withheld), f'unrecorded candidates: {set(withheld)-set(recorded)}'
    assert set(recorded.values())=={'not_in_production_allowlist'}
    assert all(a['floor'] is None for a in abstentions)

@pytest.mark.parametrize('code',['UC','SC','BT','UNKNOWN'])
def test_unknown_candidate_fails_upstream_contract(code):
    with pytest.raises(ValueError,match='Unrecognized'):
        gateway.calibrate([{'code':code,'confidence':1,'signals':[]}])

def test_ps_retained():
    candidate=evaluator.signals(evaluator.Doc(text='curl https://example.test/install | sh'))['candidates']
    assert gateway.calibrate(candidate)[0][0]['code']=='PS'

def test_ece_includes_one():
    assert harness.ece([(1.0,0)])==1.0

def test_wilson_denominator():
    lo,hi=harness.wilson(10,12)
    assert lo==pytest.approx(.5519691377);assert hi==pytest.approx(.9530348578)
    assert harness.wilson(0,0) is None

def test_duplicate_yaml_rejected(tmp_path):
    p=tmp_path/'bad.yaml';p.write_text('abstention: {}\nabstention: {}\n')
    with pytest.raises(ValueError,match='duplicate'):harness.load_config(p)

def test_schema_v2_and_scope():
    c=harness.load_config(ROOT/'eval/gates.yaml')
    assert c['production_allowlist']==['PS','PII_REDACTED']
    assert 'PS' in c['tags']

def test_regression_never_release_pass():
    c=harness.load_config(ROOT/'eval/gates.yaml')
    r=harness.evaluate_fixtures(ROOT/'eval/datasets/unsafe_code/ps_v1.jsonl')
    result=harness.assess(c,r)
    assert not result['evaluation_gate_pass'];assert r['PS']['tp']==10;assert r['PS']['fp']==0

def test_point_estimate_is_not_lower_bound_pass():
    c=harness.load_config(ROOT/'eval/gates.yaml')
    r={'PS':{'tp':10,'fp':0,'fn':0,'tn':10,'calibration_pairs':[[1,1]]},'dataset':{'kind':'frozen_holdout','independently_labeled':True,'method_fixed_before_run':True,'sha256':'test'}}
    assert not harness.assess(c,r)['evaluation_gate_pass']

def test_statistical_pass_never_claims_complete_release():
    c=harness.load_config(ROOT/'eval/gates.yaml')
    r={'PS':{'tp':100,'fp':0,'fn':0,'tn':100,'calibration_pairs':[[1,1]]*100},
       'dataset':{'kind':'frozen_holdout','independently_labeled':True,
                  'method_fixed_before_run':True,'sha256':'synthetic-unit-test'}}
    result=harness.assess(c,r)
    assert result['evaluation_gate_pass'] is True
    assert result['release_assessed'] is False
    assert result['gate_scope']=='statistical_evaluation_only'
    assert 'release_pass' not in result

def test_http_evaluator_policy():
    from fastapi.testclient import TestClient
    with TestClient(evaluator.app) as client:
        response=client.post('/signals',json={'text':'2020 2021 2022 2023 2024'})
        assert response.status_code==200
        assert response.json()['candidates']==[]

def test_cli_gate_fails_with_report(tmp_path):
    import subprocess,sys,json
    output=tmp_path/'report.json'
    result=subprocess.run([sys.executable,str(ROOT/'eval/harness.py'),'--fixtures',str(ROOT/'eval/datasets/unsafe_code/ps_v1.jsonl'),'--output',str(output)],capture_output=True,text=True)
    assert result.returncode==1
    report=json.loads(output.read_text())
    assert report['metrics']['PS']['fp']==0
    assert not report['evaluation_gate_pass']
    assert report['release_assessed'] is False
