"""Original-offset and upstream-contract controls; these do not load a PII engine."""
import ast
from pathlib import Path
from types import SimpleNamespace

import pytest

SOURCE = Path(__file__).resolve().parents[1] / 'services/anonymizer/app.py'
NODE = next(n for n in ast.parse(SOURCE.read_text()).body
            if isinstance(n, ast.ClassDef) and n.name == 'OfflineEmailRecognizer')


class Upstream:
    def analyze(self, text, entities, nlp_artifacts=None):
        self.calls.append((text, entities, nlp_artifacts))
        response = self.responses[len(self.calls) - 1]
        if isinstance(response, BaseException):
            raise response
        return response


def finding(start, end, entity='EMAIL_ADDRESS', score=.5):
    return SimpleNamespace(entity_type=entity, start=start, end=end, score=score,
                           analysis_explanation=object(), recognition_metadata={'source': 'upstream'})


def recognizer(responses):
    def result(entity_type, start, end, score, **kwargs):
        return SimpleNamespace(entity_type=entity_type, start=start, end=end, score=score, **kwargs)
    scope = {'EmailRecognizer': Upstream, 'RecognizerResult': result,
             'tldextract': SimpleNamespace(TLDExtract=lambda **_: None)}
    exec(compile(ast.Module(body=[NODE], type_ignores=[]), str(SOURCE), 'exec'), scope)
    value = scope['OfflineEmailRecognizer'](); value.calls = []; value.responses = responses
    return value


def test_existing_bracketed_challenge_maps_whole_original_span():
    text = 'Contact pilot [at] example [dot] org.'
    projected = finding(0, 17)
    r = recognizer([[], [projected]]); marker = object()
    result = r.analyze(text, ['EMAIL_ADDRESS'], marker)
    assert len(result) == 1
    actual = result[0]
    assert (actual.start, actual.end) == (8, 36)
    assert text[actual.start:actual.end] == 'pilot [at] example [dot] org'
    assert actual.score == projected.score
    assert actual.analysis_explanation is projected.analysis_explanation
    assert actual.recognition_metadata == projected.recognition_metadata
    assert actual.recognition_metadata is not projected.recognition_metadata
    assert r.calls == [(text, ['EMAIL_ADDRESS'], marker), ('pilot@example.org', ['EMAIL_ADDRESS'], None)]


@pytest.mark.parametrize('value,projected', [
    ('PILOT[AT]EXAMPLE[DOT]ORG', 'PILOT@EXAMPLE.ORG'),
    ('pilot+review [at] mail [dot] example [dot] org', 'pilot+review@mail.example.org'),
    ('test.user   [aT]   example   [dOt]   org', 'test.user@example.org'),
])
def test_explicit_ascii_forms_preserve_unicode_context_and_punctuation(value, projected):
    prefix = 'Ω 😀 ('; text = prefix + value + '), next.'
    r = recognizer([[], [finding(0, len(projected))]])
    result = r.analyze(text, ['EMAIL_ADDRESS'])
    assert len(result) == 1
    assert (result[0].start, result[0].end) == (len(prefix), len(prefix) + len(value))
    assert r.calls[1][0] == projected


@pytest.mark.parametrize('text', [
    'An [at] sign and a [dot] marker explain syntax.',
    'pilot at example dot org',
    'pilot [at] example.org',
    'pilot@example [dot] org',
    'pilot [at] example [dot]',
    'pilot\n[at] example [dot] org',
    'pilot\t[at] example [dot] org',
    'pilot    [at] example [dot] org',
    'tést [at] example [dot] org',
    'x@pilot [at] example [dot] org',
    'pilot [at] example [dot] org_suffix',
    'pilot [at] example [dot] org.evil',
    'pilot [at] example [dot] org..',
    'pilot [at] example [dot] ' + 'x' * 64,
    'x' * 65 + ' [at] example [dot] org',
    'pilot [at] ' + ' [dot] '.join(['label'] * 9),
    'pilot [at] example [dot] org      [dot] evil',
    'pilot..review [at] example [dot] org',
])
def test_malformed_embedded_or_nonpaired_forms_do_not_invoke_projected_recognition(text):
    original = []; r = recognizer([original])
    assert r.analyze(text, ['EMAIL_ADDRESS']) == []
    assert len(r.calls) == 1


def test_packaged_upstream_rejection_is_preserved():
    text = 'pilot [at] example [dot] invalidsuffix'
    r = recognizer([[], []])
    assert r.analyze(text, ['EMAIL_ADDRESS']) == []
    assert r.calls[1][0] == 'pilot@example.invalidsuffix'


@pytest.mark.parametrize('bad', [finding(1, 17), finding(0, 16), finding(0, 18), finding(0, 17, 'PERSON')])
def test_partial_or_wrong_category_upstream_results_cannot_be_promoted(bad):
    r = recognizer([[], [bad]])
    assert r.analyze('pilot [at] example [dot] org', ['EMAIL_ADDRESS']) == []


def test_existing_results_and_unrequested_entities_keep_objects():
    text = 'pilot [at] example [dot] org'; original = [finding(0, len(text))]
    r = recognizer([original])
    assert r.analyze(text, ['IP_ADDRESS']) is original
    assert len(r.calls) == 1
    r = recognizer([original])
    assert r.analyze(text, ['EMAIL_ADDRESS']) == original
    assert len(r.calls) == 1


def test_two_addresses_have_separate_offsets_without_changing_existing_findings():
    text = 'one@example.org, two [at] example [dot] org; end.'
    first = finding(0, 15); other = finding(0, 15)
    r = recognizer([[first], [other]])
    results = r.analyze(text, ['EMAIL_ADDRESS'])
    assert results[0] is first
    start = text.index('two [at]')
    assert (results[1].start, results[1].end) == (start, start + len('two [at] example [dot] org'))
    assert r.calls[1][0] == 'two@example.org'


def test_ordinary_email_and_hidden_separator_contracts_remain_unchanged():
    rows = [finding(0, 17)]; r = recognizer([rows]); marker = object()
    assert r.analyze('pilot@example.org', ['EMAIL_ADDRESS'], marker) is rows
    assert r.calls == [('pilot@example.org', ['EMAIL_ADDRESS'], marker)]
    text = 'Contact pilot@exam\u200bple.org.'; r = recognizer([[], [finding(8, 25)]])
    actual = r.analyze(text, ['EMAIL_ADDRESS'])[0]
    assert text[actual.start:actual.end] == 'pilot@exam\u200bple.org'
    assert r.calls[1][0] == 'Contact pilot@example.org.'


def test_upstream_failure_is_not_silenced_as_zero_findings():
    r = recognizer([[], RuntimeError('Synthetic recognizer unavailable')])
    with pytest.raises(RuntimeError, match='Synthetic recognizer unavailable'):
        r.analyze('pilot [at] example [dot] org', ['EMAIL_ADDRESS'])


def test_maximum_input_malformed_tokens_do_not_create_a_suffix_candidate():
    text = ('x' * 65 + ' [at] example [dot] org ') * 2200
    text = text[:200_000]
    r = recognizer([[]])
    assert r.analyze(text, ['EMAIL_ADDRESS']) == []
    assert len(r.calls) == 1
