"""Consumer drift and accidental proposal adoption must fail verification."""
import importlib.util,json,shutil
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]
s=importlib.util.spec_from_file_location('vocabulary',ROOT/'scripts/verify-vocabulary.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
@pytest.fixture
def snapshot(tmp_path):
    for f in ('spec/vocabulary.json','spec/assertion.schema.json','spec/taxonomy.md','services/gateway/app.py','services/evaluator/app.py'):
        (tmp_path/f).parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/f,tmp_path/f)
    return tmp_path
def test_adopted_vocabulary_is_shared_without_releasing_proposals():assert m.verify()['adopted_codes']==10
@pytest.mark.parametrize('key,value',[('codes',['UC']),('independently_released_codes',['PS']),('gateway_modalities',['code']),('disabled_known_code_behavior','floor_one')])
def test_unaccepted_vocabulary_change_fails(snapshot,key,value):
    p=snapshot/'spec/vocabulary.json';v=json.loads(p.read_text());v[key]=value;p.write_text(json.dumps(v))
    with pytest.raises(ValueError):m.verify(snapshot)
def test_gateway_cannot_silently_enable_proposal(snapshot):
    p=snapshot/'services/gateway/app.py';p.write_text(p.read_text().replace("PRODUCTION_TAGS=frozenset({'PS','PII_REDACTED'})","PRODUCTION_TAGS=frozenset({'UC','PII_REDACTED'})"))
    with pytest.raises(ValueError,match='capability drift'):m.verify(snapshot)
def test_schema_change_requires_explicit_vocabulary_update(snapshot):
    p=snapshot/'spec/assertion.schema.json';v=json.loads(p.read_text());v['$defs']['code']['enum'].append('BT');p.write_text(json.dumps(v))
    with pytest.raises(ValueError,match='Schema vocabulary drift'):m.verify(snapshot)
