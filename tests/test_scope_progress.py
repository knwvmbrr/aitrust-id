"""Reject unsupported completion claims and missing execution accountability."""
import copy
import importlib.util
import json
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('scope_progress',ROOT/'scripts/scope-progress.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
def ledger():return json.loads((ROOT/'docs/scope-progress.json').read_text())
def test_scope_ledger_preserves_every_record_and_separates_open_work():
    result=m.verify(ledger());assert result['records']==202 and result['completed_records']==sum(r['percent_complete']==100 for r in ledger()['records']) and result['all_open_items_have_fix_and_owner']
def test_false_completion_without_acceptance_or_credit_is_rejected():
    d=ledger();r=next(r for r in d['records'] if r['percent_complete']==100);r['completed_by']=[]
    with pytest.raises(ValueError,match='Unsupported 100%'):m.verify(d)
def test_missing_fix_or_scope_record_is_rejected():
    d=ledger();r=next(r for r in d['records'] if r['percent_complete']<100);r['next_fix']=''
    with pytest.raises(ValueError,match='Open item'):m.verify(d)
    d=ledger();d['records'].pop()
    with pytest.raises(ValueError,match='Missing/duplicate/orphan'):m.verify(d)
def test_package_cannot_inherit_completion_from_one_good_component():
    d=ledger();p=d['packages'][0];p.update(percent_complete=100,milestones_passed=m.MILESTONES,completed_by=['Fake'],implemented_by=['Fake'],completed_at=p['audited_at'],next_fix=None,next_owner=None,required_acceptance=[],queue='completed')
    with pytest.raises(ValueError,match='inflates child'):m.verify(d)


@pytest.mark.parametrize('field',['implemented_by','completed_by','planning_contributors','evidence','required_acceptance'])
def test_attribution_and_acceptance_lists_cannot_be_scalar(field):
    data=json.loads((ROOT/'docs/scope-progress.json').read_text())
    data['records'][0][field]='malformed scalar'
    with pytest.raises(ValueError,match='Invalid list field'):
        m.verify(data)
