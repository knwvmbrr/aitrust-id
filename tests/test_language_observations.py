"""English observation controls, never a surrogate for HP/MT accuracy."""
import copy
import json
from pathlib import Path
import socket
import subprocess
import sys
import pytest
from protocol.corpus import CorpusError
from protocol.normalization import normalize_nfc
from tools import language_observations as o

ROOT = Path(__file__).resolve().parents[1]


def context(subject, uncertainty=None, sources=None):
    return {'format': 'language-context-annotations/v1',
            'subject_sha256': o.digest(normalize_nfc(subject)),
            'uncertainty': uncertainty or [], 'sources': sources or []}


def assert_boundaries(result):
    assert result['tags'] == []
    assert result['truth_established'] is False and result['intent_established'] is False
    assert result['independent_accuracy_evidence'] is False and result['network_used'] is False
    assert result['score_is_probability'] is False and result['context_inferred'] is False


@pytest.mark.parametrize('phrase', ['It might rain.', 'It is not likely.', 'Perhaps it will rise.',
                                    'The fee is approximately 25 dollars.', 'It may not work.'])
def test_supported_hedges_in_declared_context(phrase):
    result = o.observe('hedge', phrase, context=context(phrase, [[0, len(phrase)]]))
    assert result['state'] == 'NO_SUPPORTED_PATTERN' and not result['findings']
    assert result['measurements']['contexts'][0]['hedge_spans']
    assert_boundaries(result)


def test_hedge_absence_is_bound_to_explicit_expectation():
    subject = 'The market will rise. It might rain.'
    result = o.observe('hedge', subject, context=context(subject, [[0, 21], [22, len(subject)]]))
    assert result['findings'][0]['spans'] == [[0, 21]] and len(result['findings']) == 1
    assert result['findings'][0]['expectation_source'] == 'explicit_caller_annotation'
    assert result['measurements']['expected_uncertainty_inferred'] is False
    assert_boundaries(result)


def test_calendar_may_not_misread_as_uncertainty():
    subject = 'The launch will be May 1.'
    result = o.observe('hedge', subject, context=context(subject, [[0, len(subject)]]))
    assert result['findings'] and not result['measurements']['contexts'][0]['hedge_spans']


def test_hedge_missing_expectation_is_unavailable():
    with pytest.raises(CorpusError): o.observe('hedge', 'The market will rise.')


def test_urgency_exact_positions_and_density():
    subject = 'Buy now. Send payment immediately. This is an offer.'
    result = o.observe('urgency', subject)
    measurement = result['measurements']
    assert measurement['sentence_units'] == 3 and measurement['directive_units'] == 2
    assert measurement['directive_density'] == pytest.approx(2/3)
    assert [subject[a:b] for a,b in measurement['directive_spans']] == ['Buy', 'Send']
    assert [subject[a:b] for a,b in measurement['time_pressure_spans']] == ['now', 'immediately']
    assert result['findings'][0]['id'] == 'sig.urgency_frame.v1'
    assert o.observe('urgency', subject, minimum_density=1)['state'] == 'NO_SUPPORTED_PATTERN'
    assert_boundaries(result)


@pytest.mark.parametrize('subject', ['The deadline is today.', 'Read the guide.', 'There is no supported phrase.',
                                     'Snow arrives today. The sky is grey.'])
def test_both_parts_needed_for_composite_urgency(subject):
    assert o.observe('urgency', subject)['state'] == 'NO_SUPPORTED_PATTERN'


@pytest.mark.parametrize('subject', ['Leave now. Call emergency services immediately.',
                                     'Submit your ordinary application today.',
                                     'Buy today. This is a normal sale.',
                                     'Act now! This is a quoted scam example.'])
def test_legitimate_urgency_and_mentions_are_not_called_manipulative(subject):
    result = o.observe('urgency', subject)
    assert result['findings'] and result['quoted_or_recommended_context_classified'] is False
    assert_boundaries(result)


@pytest.mark.parametrize('subject', ['Experts agree that it works.', 'Studies show a benefit.',
                                     'Research proves that this is useful.', 'Everyone knows this already.'])
def test_unmarked_authority_phrase_has_only_lexical_meaning(subject):
    result = o.observe('authority', subject)
    assert len(result['findings']) == 1
    finding = result['findings'][0]
    assert finding['id'] == 'sig.authority_appeal.v1' and finding['source_marker_spans'] == []
    assert subject[slice(*finding['spans'][0])]
    assert_boundaries(result)


@pytest.mark.parametrize('subject', ['Studies show a benefit [12].', 'Experts agree: https://example.invalid/paper.',
                                     'https://example.invalid/paper says experts agree.'])
def test_explicit_source_markers_retained_separately_not_resolved(subject):
    result = o.observe('authority', subject)
    assert not result['findings'] and result['measurements']['marked_appeals']
    assert result['measurements']['citation_resolution_performed'] is False


def test_source_markers_in_other_sentence_do_not_claim_local_attribution():
    subject = 'A citation [1]. Experts agree.'
    result = o.observe('authority', subject)
    assert result['findings'] and result['measurements']['sources_elsewhere_checked'] is False


def test_explicit_source_annotation_bound_to_subject():
    subject = 'Experts agree according to the committee report.'
    annotation = context(subject, sources=[[27, len(subject)]])
    result = o.observe('authority', subject, context=annotation)
    assert not result['findings']
    assert result['measurements']['marked_appeals'][0]['selected_source_spans'] == annotation['sources']


def test_unicode_normalization_positions_and_determinism():
    original = 'Cafe\u0301 says experts agree.'
    subject = normalize_nfc(original)
    result = o.observe('authority', original)
    assert result['subject_sha256'] == o.digest(subject)
    assert subject[slice(*result['findings'][0]['spans'][0])] == 'experts agree'
    assert result == o.observe('authority', original)


@pytest.mark.parametrize('mutation', [
    lambda c: c.update(format='future'), lambda c: c.update(subject_sha256='a'*64),
    lambda c: c.update(extra=True), lambda c: c.update(uncertainty='string'),
    lambda c: c.update(sources=[[0, True]]), lambda c: c.update(sources=[[-1, 1]]),
    lambda c: c.update(sources=[[0, 100]]), lambda c: c.update(sources=[[0, 0]]),
    lambda c: c.update(sources=[[2, 4], [0, 1]]), lambda c: c.update(sources=[[0, 3], [2, 4]]),
    lambda c: c.update(sources=[[0, 1]]*33),
])
def test_invalid_or_foreign_context_refused(mutation):
    subject = 'Experts agree.'; annotation = context(subject); mutation(annotation)
    with pytest.raises(CorpusError): o.observe('authority', subject, context=annotation)


@pytest.mark.parametrize('subject', ['', ' ', '\x00', '\ud800', 'x'*8001, None, 1])
def test_invalid_subject_refused(subject):
    with pytest.raises(CorpusError): o.observe('urgency', subject)


@pytest.mark.parametrize('threshold', [True, False, 0, 1.01, None, float('nan'), float('inf')])
def test_invalid_density_refused(threshold):
    with pytest.raises(CorpusError): o.observe('urgency', 'Buy now.', minimum_density=threshold)


def test_unsupported_language_or_observer_refused():
    with pytest.raises(CorpusError): o.observe('authority', 'Experts agree.', language='unknown')
    with pytest.raises(CorpusError): o.observe('unknown', 'Experts agree.')


def test_actual_cli_private_annotations_and_failure_no_input_echo(tmp_path):
    tmp_path.chmod(0o700); subject = 'This will happen.'; annotation = tmp_path/'context.json'
    annotation.write_text(json.dumps(context(subject, [[0, len(subject)]]))); annotation.chmod(0o600)
    command = [sys.executable, str(ROOT/'scripts/language-observations.py'), 'hedge', '--language', 'en', '--annotations', str(annotation)]
    good = subprocess.run(command, input=subject, text=True, capture_output=True)
    assert good.returncode == 0 and json.loads(good.stdout)['findings']
    assert subject not in good.stdout + good.stderr
    bad = subprocess.run(command, input='PRIVATE_QUERY_CANARY', text=True, capture_output=True)
    assert bad.returncode == 2 and json.loads(bad.stdout)['state'] == 'UNAVAILABLE'
    assert 'PRIVATE_QUERY_CANARY' not in bad.stdout + bad.stderr
    annotation.chmod(0o644)
    assert subprocess.run(command, input=subject, text=True, capture_output=True).returncode == 2


def test_no_network_and_full_supported_size(monkeypatch):
    monkeypatch.setattr(socket, 'socket', lambda *a, **kw: (_ for _ in ()).throw(AssertionError('Network forbidden')))
    subject = 'Buy now. '*888
    assert len(subject) <= 8000
    result = o.observe('urgency', subject)
    assert result['findings'] and result['measurements']['directive_density'] == 1
    assert_boundaries(result)
