"""Check executable attack observations and refusal to accept invalid controls."""
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import pytest
from test_release_policy import module

assessment = module('scripts/assess-evidence-resistance.py')


def test_current_attack_assessment_inventories_versions_and_reports_observations():
    record = assessment.assess()
    assert record['pass'] and len(record['methods']) == 38
    assert len({r['signal_id'] for r in record['methods']}) == 38
    assert len(record['synthetic_lexical_trials']) == 8
    assert all(r['syntax_only_pass'] and r['shlex_token_sequence_equal']
               and r['baseline_found'] for r in record['synthetic_lexical_trials'])
    assert not record['commands_executed'] and record['network_requests'] == 0
    assert not record['release_approved'] and not record['independent_accuracy_evidence']
    assert record['method_sha256'] == hashlib.sha256(
        (assessment.ROOT/'services/evaluator/app.py').read_bytes()).hexdigest()
    assert 'smallest observed' in record['cost_interpretation']
    # Improvements may find future mutations; do not require permanent evasion.
    for row in record['methods']:
        if row['status'] == 'measured_synthetic_lexical_evasion':
            assert 0 <= row['misses'] <= row['trials']


def test_missing_baseline_cannot_be_presented_as_attack_measurement():
    method = SimpleNamespace(Doc=SimpleNamespace, signals=lambda doc: {'candidates': []})
    with pytest.raises(ValueError, match='baseline'):
        assessment.assess(method)


def test_invalid_syntax_control_refused(monkeypatch):
    monkeypatch.setattr(assessment, 'syntax_only', lambda text: False)
    with pytest.raises(ValueError, match='baseline'):
        assessment.assess()


def test_token_disagreement_refused(monkeypatch):
    monkeypatch.setattr(assessment, 'tokens', lambda text: [text])
    with pytest.raises(ValueError, match='syntax/token'):
        assessment.assess()


def test_source_changed_during_assessment_is_not_a_pass(tmp_path, monkeypatch):
    source = tmp_path/'services/evaluator/app.py'
    source.parent.mkdir(parents=True)
    source.write_text('before')
    monkeypatch.setattr(assessment, 'ROOT', tmp_path)
    monkeypatch.setattr(assessment, 'registry', lambda: {'signals': [
        {'id': 'synthetic.method.v1', 'status': 'synthetic_test_only'}]})
    def changed(doc):
        source.write_text('after')
        return {'candidates': [{'signals': [{'id': 'synthetic.method.v1'}]}]}
    method = SimpleNamespace(Doc=SimpleNamespace, signals=changed)
    result = assessment.assess(method)
    assert not result['pass'] and not result['source_unchanged']


def test_published_observations_are_bound_to_current_method():
    record = json.loads((assessment.ROOT/'runs/2026-10-10-evidence-resistance.json').read_text())
    assert record['method_sha256'] == hashlib.sha256(
        (assessment.ROOT/'services/evaluator/app.py').read_bytes()).hexdigest()
    assert record['independent_accuracy_evidence'] is False
