"""Authored MT urgency association controls, not an accuracy sample."""
import json
from pathlib import Path
import subprocess
import sys

import pytest

from protocol.corpus import CorpusError
from protocol.normalization import normalize_nfc
from tools import language_observations as o

ROOT = Path(__file__).resolve().parents[1]


def snippets(subject, spans):
    text = normalize_nfc(subject)
    return [text[start:end] for start, end in spans]


def unasserted(result):
    assert result['tags'] == []
    assert result['intent_established'] is False
    assert result['truth_established'] is False
    assert result['context_inferred'] is False
    assert result['quoted_or_recommended_context_classified'] is False
    assert result['independent_accuracy_evidence'] is False


@pytest.mark.parametrize('subject', [
    'The committee met today. Read the archived minutes.',
    'Install the patch. The news was published today.',
    'Call the archivist. The archive was updated immediately.',
    'The meeting is today. Read the records. Install the viewer.',
])
def test_unrelated_unit_cannot_supply_time_association(subject):
    result = o.observe('urgency', subject)
    measured = result['measurements']
    assert result['state'] == 'NO_SUPPORTED_PATTERN' and not result['findings']
    assert measured['directive_density'] >= .5
    assert measured['time_pressure_spans'] and measured['directive_spans']
    assert measured['paired_units'] == []
    assert measured['unpaired_time_pressure_spans'] == measured['time_pressure_spans']
    unasserted(result)


@pytest.mark.parametrize('subject', [
    'Read the evacuation notice now.',
    'Leave now. Call emergency services immediately.',
    'Submit your application today.',
    'Please check the records right away.',
    'Act now! This is an example, not advice.',
])
def test_within_unit_measurements_do_not_establish_bad_intent(subject):
    result = o.observe('urgency', subject)
    assert result['state'] == 'OBSERVATIONS'
    assert result['measurements']['association_scope'] == 'same_sentence_unit'
    for unit in result['measurements']['paired_units']:
        start, end = unit['unit_span']
        for a, b in [unit['directive_span'], *unit['time_pressure_spans']]:
            assert start <= a < b <= end
    unasserted(result)


def test_finding_does_not_borrow_unrelated_directives_or_time_words():
    subject = 'Install the viewer. Buy the pass now. The workshop is today.'
    result = o.observe('urgency', subject)
    measured = result['measurements']
    assert snippets(subject, measured['directive_spans']) == ['Install', 'Buy']
    assert snippets(subject, measured['time_pressure_spans']) == ['now', 'today']
    assert snippets(subject, measured['unpaired_time_pressure_spans']) == ['today']
    assert snippets(subject, result['findings'][0]['spans']) == ['Buy', 'now']
    assert measured['sentence_units'] == 3 and measured['directive_units'] == 2
    assert measured['directive_density'] == pytest.approx(2/3)


@pytest.mark.parametrize('subject', [
    'Buy the guide. Last chance today.',
    'Today is the deadline. Please submit your application.',
    'Call emergency services. Immediately.',
])
def test_cross_sentence_association_stays_unresolved_not_clearance(subject):
    result = o.observe('urgency', subject)
    assert result['state'] == 'NO_SUPPORTED_PATTERN'
    assert result['measurements']['time_pressure_spans']
    assert result['measurements']['directive_spans']
    assert not result['measurements']['paired_units']
    unasserted(result)


def test_global_density_threshold_does_not_silently_become_local_density():
    subject = 'Buy now. This is an offer. The page has terms.'
    result = o.observe('urgency', subject)
    assert result['state'] == 'NO_SUPPORTED_PATTERN'
    assert result['measurements']['paired_units']
    assert result['measurements']['directive_density'] == pytest.approx(1/3)
    assert o.observe('urgency', subject, minimum_density=.3)['state'] == 'OBSERVATIONS'


def test_normalized_positions_and_raw_measurements_remain_exact():
    original = 'Read Cafe\u0301 details now. The event is today. Install the viewer.'
    subject = normalize_nfc(original)
    result = o.observe('urgency', original)
    assert result['subject_sha256'] == o.digest(subject)
    assert snippets(original, result['findings'][0]['spans']) == ['Read', 'now']
    assert result['measurements']['time_pressure_spans'] == [[m.start(), m.end()] for m in o.PRESSURE.finditer(subject)]
    assert result == o.observe('urgency', original)
    assert json.loads(json.dumps(result))['measurements']['paired_units']


def test_method_revision_does_not_claim_hedge_or_authority_semantic_change():
    assert o.observe('urgency', 'Buy now.')['method'] == 'english-context-observations/1.1.0'
    assert o.observe('authority', 'Experts agree.')['method'] == 'english-context-observations/1.0.0'
    subject = 'It might rain.'
    context = {'format': 'language-context-annotations/v1', 'subject_sha256': o.digest(subject),
               'uncertainty': [[0, len(subject)]], 'sources': []}
    assert o.observe('hedge', subject, context=context)['method'] == 'english-context-observations/1.0.0'


def test_limit_and_language_refusal_not_changed():
    with pytest.raises(CorpusError): o.observe('urgency', 'Read now. ' * 801)
    with pytest.raises(CorpusError): o.observe('urgency', 'Read now.', language='und')


def test_actual_cli_keeps_unrelated_measurements_but_not_subject_text():
    subject = 'The private committee met today. Read the private archived minutes.'
    completed = subprocess.run([sys.executable, str(ROOT/'scripts/language-observations.py'),
                                'urgency', '--language', 'en'],
                               input=subject, text=True, capture_output=True, timeout=5)
    assert completed.returncode == 0
    result = json.loads(completed.stdout)
    assert result['state'] == 'NO_SUPPORTED_PATTERN'
    assert result['measurements']['unpaired_time_pressure_spans']
    assert subject not in completed.stdout + completed.stderr
    assert 'private committee' not in completed.stdout + completed.stderr
    unasserted(result)
