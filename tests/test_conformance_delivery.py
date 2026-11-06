"""Keep F-119 software completion bounded to actual complete current execution."""
import copy
import importlib.util
import json
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('conformance_delivery',ROOT/'scripts/verify-conformance-delivery.py')
gate=importlib.util.module_from_spec(spec);spec.loader.exec_module(gate)
def receipt():return json.loads((ROOT/gate.EVIDENCE).read_bytes())
def test_current_bounded_software_execution():
 row=gate.verify(receipt());assert row['reference_checks']==28 and row['focused_tests']==12
 assert row['outside_person_acceptance'] is row['independent_accuracy_evidence'] is row['release_approved'] is False
@pytest.mark.parametrize('change',[
 lambda r:r['sources'].update({'tools/conformance_vectors.py':'0'*64}),
 lambda r:r['reference']['checks'].pop(),
 lambda r:r['reference']['checks'][0].update({'exit':9}),
 lambda r:r['reference']['checks'][0].update({'pass':False}),
 lambda r:r['reference'].update({'outside_person_acceptance':True}),
 lambda r:r.update({'independent_accuracy_evidence':True}),
 lambda r:r.update({'release_approved':True}),
 lambda r:r['focused'].update({'skipped':1}),
 lambda r:r['focused'].update({'exit':False}),
 lambda r:r.update({'captured_at':'2999-01-01T00:00:00+00:00'}),
])
def test_stale_incomplete_failed_and_overclaimed_evidence_refused(change):
 row=receipt();change(row)
 with pytest.raises(ValueError):gate.verify(row)

def test_owner_decision_preserves_external_acceptance_instead_of_waiving_it():
 decision=json.loads((ROOT/'runs/2026-11-06-conformance-software-owner-decision.json').read_bytes())
 assert decision['answer']=='Yes — separate software and human acceptance'
 assert decision['retained_under']=='F-142' and decision['independent_accuracy_under']=='F-108'
 rows={r['id']:r for r in json.loads((ROOT/'docs/scope-progress.json').read_bytes())['records']}
 # A later defect may reopen the software requirement. The retained human
 # criterion must survive that too; the decision is not a permanent 100% lock.
 if rows['F-142']['percent_complete']<100:
  assert set(decision['original_required_acceptance'])<=set(rows['F-142']['required_acceptance'])
 assert 'F-057 or F-120 acceptance reallocation' in decision['not_authorized']
 assert receipt()['outside_person_acceptance'] is receipt()['independent_accuracy_evidence'] is False
