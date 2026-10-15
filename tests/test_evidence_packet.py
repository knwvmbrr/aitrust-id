"""The downloadable evidence index must expose failures without granting release."""
import json
from pathlib import Path
import subprocess
import sys
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools import evidence_packet as module


def fixture(tmp_path):
    state = {'current_engineering_revalidation': {c: 'runs/'+c+'.json' for c in module.CAPABILITIES}}
    ledger = {'records': [{'id': 'F-'+str(i), 'percent_complete': 100 if i else 80,
                          'required_acceptance': [] if i else ['Independent human review.']}
                         for i in range(202)]}
    for name in module.BASE:
        path = tmp_path/name;path.parent.mkdir(parents=True, exist_ok=True)
        value = state if name == 'state.json' else ledger if name in ('docs/scope-progress.json', 'docs/master-scope.json') else {}
        path.write_text(json.dumps(value))
    for c in module.CAPABILITIES:
        path=tmp_path/('runs/'+c+'.json');path.parent.mkdir(exist_ok=True)
        path.write_text(json.dumps({'captured_at':'2026-10-10T10:00:00Z'}))
    return state


def controls(monkeypatch, fail=None):
    monkeypatch.setattr(module, 'assess', lambda receipt, c, root: {
        'pass': c != fail, 'failures': [] if c != fail else ['source_dependency_fixture_or_check_changed'],
        'release_approved': False, 'independent_accuracy_evidence': False})
    monkeypatch.setattr(module, 'fingerprint', lambda c, root: {'sources': {}})


def test_current_packet_keeps_human_gate_open(tmp_path, monkeypatch):
    fixture(tmp_path);controls(monkeypatch)
    result=module.build(tmp_path)
    assert result['packet_valid'] and result['engineering_checks_current']
    assert len(result['receipts'])==5 and len(result['open_records'])==1
    assert result['open_records'][0]['required_acceptance']==['Independent human review.']
    assert result['records_preserved']==202
    assert all(result[k] is False for k in ('release_assessed','release_approved',
        'independent_accuracy_evidence','certification'))


@pytest.mark.parametrize('failure',['stale','missing','malformed'])
def test_failed_or_missing_receipt_does_not_disappear(tmp_path, monkeypatch, failure):
    fixture(tmp_path);controls(monkeypatch,'PS' if failure=='stale' else None)
    path=tmp_path/'runs/PS.json'
    if failure=='missing':path.unlink()
    if failure=='malformed':path.write_text('{"private-canary":')
    result=module.build(tmp_path)
    assert result['packet_valid'] and result['engineering_checks_current'] is False
    assert len(result['receipts'])==5
    assert next(c for c in result['receipts'] if c['capability']=='PS')['pass'] is False
    assert 'private-canary' not in json.dumps(result)


@pytest.mark.parametrize('name',['../private.json','runs/../state.json','/tmp/private.json','runs/x.json?token=x'])
def test_unsafe_selected_reference_refused(tmp_path,monkeypatch,name):
    state=fixture(tmp_path);controls(monkeypatch)
    state['current_engineering_revalidation']['PS']=name
    (tmp_path/'state.json').write_text(json.dumps(state))
    with pytest.raises(ValueError, match='public execution receipts'):
        module.build(tmp_path)


def test_mid_inspection_source_change_refuses_packet(tmp_path,monkeypatch):
    fixture(tmp_path);controls(monkeypatch)
    original=module.assess
    def change(receipt,c,root):
        (tmp_path/'state.json').write_text('{}')
        return original(receipt,c,root)
    monkeypatch.setattr(module,'assess',change)
    result=module.build(tmp_path)
    assert result['packet_valid'] is False and result['engineering_checks_current'] is False


def test_actual_current_repository_packet_and_cli():
    result=module.build()
    assert result['packet_valid'] and result['records_preserved']==202
    assert len(result['receipts'])==5 and len(result['files'])>100
    cli=subprocess.run([sys.executable,str(ROOT/'scripts/build-evidence-packet.py'),'--require-current'],
                       capture_output=True,timeout=15)
    value=json.loads(cli.stdout)
    assert not cli.stderr
    assert cli.returncode==(0 if value['engineering_checks_current'] else 1)
    assert value['release_approved'] is False
