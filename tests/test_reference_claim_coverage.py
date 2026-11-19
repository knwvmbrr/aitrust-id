"""Claim bookkeeping with controlled scores; these fixtures do not measure accuracy."""
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import pytest
from protocol import corpus
from research.nli import references
from research.nli.pairs import PairError

ROOT = Path(__file__).resolve().parents[1]
SUBJECT = 'The room is empty.\nThe door is closed.'
spec = importlib.util.spec_from_file_location('coverage_reference_cli', ROOT/'scripts/check-nli-references.py')
cli = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cli)


def envelope(documents):
    docs = [{'id': identity, 'sha256': corpus.sha(text.encode()), 'text': text}
            for identity, text in sorted(documents.items())]
    content = {'format': corpus.VERSION, 'documents': docs}
    return dict(content, manifest_sha256=corpus.sha(corpus.encoded(content)))


@pytest.fixture
def result():
    record = envelope({'manual': 'The room is empty.\nThe door is closed.'})
    return references.observe(record, 'The room is empty.\nThe door is closed.',
                              lambda a, b: ([0., 4., -2.], 12), {}, 1, 1)


def test_global_pair_limit_leaves_an_explicit_unevaluated_claim():
    record = envelope({'manual': 'The room is empty.\nThe door is closed.'})
    seen = []
    def backend(premise, hypothesis):
        seen.append((premise, hypothesis))
        return [0., 4., -2.], 12
    observed = references.observe(record, 'The room is empty.\nThe door is closed.', backend, {}, 1, 1)
    assert len(seen) == len(observed['observations']) == 1
    assert observed['profile'] == 'retrieved-passage-nli-observation/1.0.0'
    assert observed['claim_coverage']['units'] == [
        {'claim_span': [0, 18], 'observation_indices': [0], 'state': 'observed_model_outputs'},
        {'claim_span': [19, 38], 'observation_indices': [], 'state': 'not_evaluated'}]
    assert references.coverage_summary(observed, SUBJECT) == {
        'claim_coverage_obtained': True, 'claim_units': 2,
        'claim_units_evaluated': 1, 'claim_units_not_evaluated': 1}
    assert not observed['truth_established'] and not observed['tag_asserted']


def test_identical_lines_keep_distinct_exact_spans():
    record = envelope({'manual': 'The room is empty.'})
    observed = references.observe(record, 'The room is empty.\nThe room is empty.',
                                  lambda a, b: ([0., 4., -2.], 12), {}, 1, 1)
    assert observed['claim_coverage']['units'][0]['observation_indices'] == [0]
    assert observed['claim_coverage']['units'][1] == {
        'claim_span': [19, 37], 'observation_indices': [], 'state': 'not_evaluated'}


def test_crlf_blank_and_trimmed_lines_use_the_current_normalized_offsets():
    record = envelope({'manual': 'The room is empty.'})
    subject = '\r\n  The room is empty. \r\n\n\tThe room is empty.\t\n'
    observed = references.observe(record, subject, lambda a, b: ([0., 4., -2.], 12), {}, 1, 1)
    units = observed['claim_coverage']['units']
    assert len(units) == 2
    assert all(subject[slice(*unit['claim_span'])] == 'The room is empty.' for unit in units)
    assert references.coverage_summary(observed, subject)['claim_units_not_evaluated'] == 1


def test_two_references_to_one_claim_do_not_count_as_two_evaluated_claims():
    record = envelope({'one': 'The room is empty.', 'two': 'The room is empty.'})
    observed = references.observe(record, 'The room is empty.', lambda a, b: ([0., 4., -2.], 12), {}, 1, 2)
    assert observed['claim_coverage']['units'][0]['observation_indices'] == [0, 1]
    assert references.coverage_summary(observed, 'The room is empty.')['claim_units_evaluated'] == 1


def test_every_unmatched_claim_is_accounted_for_without_invoking_model():
    record = envelope({'manual': 'The room is empty.'})
    def forbidden(*args):
        pytest.fail('No-match claim coverage invoked the model')
    observed = references.observe(record, 'Orange bicycle highway.\nPurple boat river.', forbidden, None)
    assert observed['observations'] == []
    assert [row['state'] for row in observed['claim_coverage']['units']] == ['not_evaluated', 'not_evaluated']
    assert references.coverage_summary(observed, 'Orange bicycle highway.\nPurple boat river.')['claim_units_not_evaluated'] == 2


def test_maximum_supported_claim_count_stays_bounded():
    record = envelope({'manual': 'word'})
    observed = references.observe(record, '\n'.join(['word']*32), lambda a, b: ([0., 4., -2.], 12), {}, 1, 5)
    assert len(observed['claim_coverage']['units']) == 32
    assert references.coverage_summary(observed, '\n'.join(['word']*32))['claim_units_evaluated'] == 5


def test_legacy_output_does_not_invent_coverage(result):
    del result['claim_coverage']
    result['network_control'] = 'injected_test_control'
    summary = cli.summary(result, False)
    assert summary['claim_coverage_obtained'] is False
    assert not any(key in summary for key in ('claim_units', 'claim_units_evaluated', 'claim_units_not_evaluated'))


def test_missing_original_subject_keeps_exported_coverage_unavailable(result):
    assert references.coverage_summary(result) == {'claim_coverage_obtained': False}


def test_different_original_subject_cannot_validate_exported_coverage(result):
    with pytest.raises(PairError):
        references.coverage_summary(result, 'The room is occupied.\nThe door is closed.')


@pytest.mark.parametrize('alter', [
    lambda r: r.update(profile='unsupported'),
    lambda r: r.update(claim_coverage=None),
    lambda r: r['claim_coverage'].update(profile='unknown'),
    lambda r: r['claim_coverage'].update(method_sha256='0'*64),
    lambda r: r['claim_coverage'].update(subject_sha256='0'*64),
    lambda r: r['claim_coverage'].update(manifest_sha256='0'*64),
    lambda r: r['claim_coverage'].update(normalization_id='unknown'),
    lambda r: r['claim_coverage'].update(span_units='bytes'),
    lambda r: r['claim_coverage'].update(extra=True),
    lambda r: r['claim_coverage'].update(units=[]),
    lambda r: r['claim_coverage']['units'].pop(),
    lambda r: r['claim_coverage']['units'].reverse(),
    lambda r: r['claim_coverage']['units'][0].update(state='not_evaluated'),
    lambda r: r['claim_coverage']['units'][0].update(claim_span=[False,18]),
    lambda r: r['claim_coverage']['units'][0].update(claim_span=[0,18.0]),
    lambda r: r['claim_coverage']['units'][0].update(observation_indices=[False]),
    lambda r: r['claim_coverage']['units'][0].update(observation_indices=[0,0]),
    lambda r: r['claim_coverage']['units'][0].update(observation_indices=[1]),
    lambda r: r['claim_coverage']['units'][0].update(observation_indices=[]),
    lambda r: r['claim_coverage']['units'][0].update(extra=True),
    lambda r: r['observations'][0].update(claim_span=[19,38]),
    lambda r: r.update(model_evaluation_obtained=False),
])
def test_malformed_or_rebound_coverage_is_refused(result, alter):
    changed = copy.deepcopy(result)
    alter(changed)
    with pytest.raises((PairError, KeyError, TypeError)):
        references.coverage_summary(changed, SUBJECT)


def test_corrupted_reference_never_obtains_claim_coverage_or_model_output():
    record = envelope({'manual': 'The room is empty.'})
    record['documents'][0]['text'] = 'The room is occupied.'
    def forbidden(*args):
        pytest.fail('Changed reference reached the model')
    with pytest.raises(corpus.CorpusError):
        references.observe(record, 'The room is empty.', forbidden, {})


def test_actual_private_cli_covers_no_match_and_keeps_details_private(tmp_path):
    tmp_path.chmod(0o700)
    record = envelope({'manual': 'The room is empty.'})
    for name, raw in {'corpus.json': corpus.encoded(record), 'subject.txt': b'Orange bicycle highway.\nPurple boat river.'}.items():
        path = tmp_path/name
        path.write_bytes(raw)
        path.chmod(0o600)
    details = tmp_path/'details'
    command = [sys.executable, '-B', str(ROOT/'scripts/check-nli-references.py'),
               '--corpus', str(tmp_path/'corpus.json'), '--subject', str(tmp_path/'subject.txt'),
               '--details', str(details)]
    process = subprocess.run(command, capture_output=True, timeout=5)
    assert process.returncode == 0 and process.stderr == b''
    summary = json.loads(process.stdout)
    assert summary['claim_coverage_obtained'] is True
    assert summary['claim_units'] == summary['claim_units_not_evaluated'] == 2
    assert summary['claim_units_evaluated'] == 0
    saved = json.loads((details/'reference-observations.json').read_bytes())
    assert len(saved['claim_coverage']['units']) == 2
    assert not details.stat().st_mode & 0o077
    assert not (details/'reference-observations.json').stat().st_mode & 0o077
    assert not any(raw in process.stdout for raw in [str(tmp_path).encode(), b'Orange', b'Purple', b'claim_span', record['manifest_sha256'].encode()])
    before = (details/'reference-observations.json').read_bytes()
    second = subprocess.run(command, capture_output=True, timeout=5)
    assert second.returncode == 2 and not second.stdout
    assert (details/'reference-observations.json').read_bytes() == before


def test_invalid_coverage_is_checked_before_creating_private_details(tmp_path, result, monkeypatch, capsys):
    tmp_path.chmod(0o700)
    record = envelope({'manual': 'The room is empty.'})
    for name, raw in {'corpus.json': corpus.encoded(record), 'subject.txt': b'The room is empty.'}.items():
        path = tmp_path/name
        path.write_bytes(raw)
        path.chmod(0o600)
    result['claim_coverage']['subject_sha256'] = '0'*64
    monkeypatch.setattr(cli, 'check', lambda *args, **kwargs: result)
    details = tmp_path/'details'
    code = cli.main(['--corpus', str(tmp_path/'corpus.json'), '--subject', str(tmp_path/'subject.txt'), '--details', str(details)])
    assert code == 2 and not details.exists()
    output = capsys.readouterr()
    assert not output.out and json.loads(output.err)['state'] == 'UNAVAILABLE'
