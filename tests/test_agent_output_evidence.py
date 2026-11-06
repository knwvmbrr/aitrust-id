"""Refuse stale, incomplete and overclaimed agent software acceptance."""
import importlib.util
import json
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('agent_evidence',ROOT/'scripts/verify-agent-output.py')
gate=importlib.util.module_from_spec(spec);spec.loader.exec_module(gate)
def receipt():return json.loads((ROOT/'runs/2026-11-06-agent-output-macos.json').read_bytes())
def test_current_actual_software_execution():
    assert gate.verify(receipt(),'darwin')['tests']==33
@pytest.mark.parametrize('change',[
 lambda r:r['sources'].update({'tools/agent_output.py':'0'*64}),
 lambda r:r.update({'source_unchanged':False}),
 lambda r:r.update({'tests':32}),
 lambda r:r.update({'skipped':1}),
 lambda r:r.update({'exit':True}),
 lambda r:r.update({'platform':'linux'}),
 lambda r:r.update({'non_root':False}),
 lambda r:r.update({'outside_person_acceptance':True}),
 lambda r:r.update({'independent_accuracy_evidence':True}),
 lambda r:r.update({'captured_at':'2999-01-01T00:00:00+00:00'}),
])
def test_stale_failed_incomplete_or_overclaimed_receipts_refused(change):
    row=receipt();change(row)
    with pytest.raises((ValueError,TypeError,KeyError)):gate.verify(row,'darwin')

def test_full_scope_closure_requires_actual_current_os_and_view_evidence():
    row=next(r for r in json.loads((ROOT/'docs/scope-progress.json').read_bytes())['records'] if r['id']=='F-158')
    if row['percent_complete']==100:
        for label,host in [('macos','darwin'),('linux','linux')]:
            gate.verify(json.loads((ROOT/('runs/2026-11-06-agent-output-'+label+'.json')).read_bytes()),host)
        view=json.loads((ROOT/'runs/2026-11-06-agent-output-view-current.json').read_bytes())
        assert view['pass'] is view['source_unchanged'] is True
        assert set(view['sources'])==set(gate.a.SOURCES)|{'scripts/verify-agent-output-view.cjs','package-lock.json'}
        assert len(view['checks'])==2 and {r['theme'] for r in view['checks']}=={'light','dark'}
        for r in view['checks']:
            for field in ('mobile320','text200','keyboardDetails','answerDefaultOmitted','explicitAnswerEscaped'):assert r[field] is True
        assert view['axe_violations']==view['external_requests']==view['script_errors']==0
        assert view['human_accessibility_verified'] is view['independent_accuracy_evidence'] is False
        assert view['production_CSP_verified'] is view['axe_injection_only_CSP_bypass'] is True
        for name,expected in view['sources'].items():assert gate.a.sha((ROOT/name).read_bytes())==expected
    else:
        assert row['completed_at'] is None and row['required_acceptance']
