"""Actual private dependency review, selective invalidation and ranking boundary."""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import pytest
from protocol import corpus, corpus_support
from tools import reference_revision as r

ROOT = Path(__file__).resolve().parents[1]
AT = '2026-10-12T12:00:00Z'


def envelope(documents):
    rows = [{'id': identity, 'sha256': corpus.sha(text.encode()), 'text': text}
            for identity, text in sorted(documents.items())]
    content = {'format': corpus.VERSION, 'documents': rows}
    return dict(content, manifest_sha256=corpus.sha(corpus.encoded(content)))


@pytest.fixture
def inputs():
    old = envelope({'manual': 'Water is safe.\nThe fee is 25 dollars.\n', 'policy': 'Use a blue bicycle.\n'})
    subject = 'Water is safe.\nUse a blue bicycle.'
    return old, subject, corpus_support.observe(old, subject, 1)


def policy(record, start='2026-10-01T00:00:00Z', end='2026-11-01T00:00:00Z'):
    return {'profile': r.POLICY, 'manifest_sha256': record['manifest_sha256'], 'documents': [
        {'document_id': doc['id'], 'document_sha256': doc['sha256'], 'opens_at': start, 'expires_at': end}
        for doc in record['documents']]}


def check(inputs, current=None, windows=None, at=AT):
    old, text, observation = inputs
    return r.review(old, current or old, text, observation, windows, at)


def test_one_changed_source_does_not_invalidate_unchanged_pair_but_ranking_is_stale(inputs):
    current = envelope({'manual': 'Water is unsafe.\nThe fee is 26 dollars.\n', 'policy': 'Use a blue bicycle.\n'})
    result = check(inputs, current)
    states = {row['reference']['document_id']: row['dependency_state'] for row in result['findings']}
    assert states == {'manual': 'document_changed', 'policy': 'pair_context_current'}
    assert result['global_retrieval_must_rerun'] and not result['global_retrieval_current']
    public = r.summary(result)
    assert public['unchanged_pair_contexts'] == public['changed_or_removed_pair_contexts'] == 1
    assert all(secret not in json.dumps(public) for secret in ('manual', 'policy', 'Water', inputs[0]['manifest_sha256']))


def test_unrelated_addition_can_change_top_rank_despite_same_selected_pair(inputs):
    old, subject, _ = inputs
    prior = corpus_support.observe(old, subject, 1, 1)
    new = envelope({'aaa': 'Water is safe.', **{d['id']: d['text'] for d in old['documents']}})
    result = r.review(old, new, subject, prior, None, AT)
    assert result['findings'][0]['pair_context_current']
    assert result['global_retrieval_must_rerun']
    fresh = corpus_support.observe(new, subject, 1, 1)
    assert prior['findings'][0]['reference']['document_id'] == 'manual'
    assert fresh['findings'][0]['reference']['document_id'] == 'aaa'


def test_removed_and_readded_source_identity(inputs):
    new = envelope({'renamed': 'Water is safe.', 'policy': 'Use a blue bicycle.\n'})
    result = check(inputs, new)
    assert {x['dependency_state'] for x in result['findings']} == {'document_removed', 'pair_context_current'}


def test_change_elsewhere_in_same_document_is_conservatively_invalid(inputs):
    new = envelope({'manual': 'Water is safe.\nThe fee is 26 dollars.\n', 'policy': 'Use a blue bicycle.\n'})
    result = check(inputs, new)
    assert result['findings'][0]['dependency_state'] == 'document_changed'


def test_identical_source_unknown_windows_is_no_truth_or_release(inputs):
    result = check(inputs)
    assert result['global_retrieval_current'] and not result['global_retrieval_must_rerun']
    assert all(row['pair_context_current'] and row['declared_review_window'] == 'unknown' for row in result['findings'])
    for key in ('truth_established', 'tag_asserted', 'release_approved', 'independent_accuracy_evidence', 'network_used', 'source_freshness_authenticated'):
        assert result[key] is False


@pytest.mark.parametrize(('at', 'expected'), [
    ('2026-09-30T23:59:59Z', 'not_yet_open'), ('2026-10-01T00:00:00Z', 'within_declared_window'),
    ('2026-10-31T23:59:59Z', 'within_declared_window'), ('2026-11-01T00:00:00Z', 'elapsed'),
    ('2027-01-01T00:00:00Z', 'elapsed')])
def test_explicit_half_open_windows(inputs, at, expected):
    result = check(inputs, windows=policy(inputs[0]), at=at)
    assert all(x['declared_review_window'] == expected for x in result['findings'])
    assert not result['source_freshness_authenticated']


def test_missing_document_window_remains_unknown(inputs):
    declared = policy(inputs[0]); declared['documents'] = declared['documents'][:1]
    out = check(inputs, windows=declared)
    assert {x['declared_review_window'] for x in out['findings']} == {'unknown', 'within_declared_window'}


@pytest.mark.parametrize('bad', ['', None, True, 0, '2026-02-30T00:00:00Z', '2026-10-12',
    '2026-10-12T12:00:00+00:00', '2026-10-12T12:00:00', '2026-10-12T24:00:00Z',
    '2026-10-12T12:00:00.5Z', '2026-10-12T12:00:60Z', '2026-10-12T12:00:00Z\n'])
def test_ambiguous_or_impossible_clock_is_refused(inputs, bad):
    with pytest.raises(r.RevisionError): check(inputs, at=bad)


@pytest.mark.parametrize('change', [
    lambda d: d.update(profile='unknown'), lambda d: d.update(manifest_sha256='0'*64),
    lambda d: d.update(extra='PRIVATE_CANARY'), lambda d: d.update(documents={}),
    lambda d: d['documents'].append(copy.deepcopy(d['documents'][0])),
    lambda d: d['documents'][0].update(document_sha256='0'*64),
    lambda d: d['documents'][0].update(document_id='missing'),
    lambda d: d['documents'][0].update(expires_at=d['documents'][0]['opens_at']),
    lambda d: d['documents'][0].update(opens_at='2027-01-01T00:00:00Z'),
    lambda d: d['documents'][0].update(extra=True),
    lambda d: d.update(documents=[None]), lambda d: d['documents'][0].update(document_id=[]),
])
def test_invalid_or_wrong_hash_policy_cannot_borrow_a_window(inputs, change):
    declared = policy(inputs[0]); change(declared)
    with pytest.raises(r.RevisionError): check(inputs, windows=declared)


@pytest.mark.parametrize('change', [
    lambda d: d.update(subject_sha256='0'*64), lambda d: d.update(method_sha256='0'*64),
    lambda d: d.update(manifest_sha256='0'*64), lambda d: d.update(method='unknown'),
    lambda d: d.update(truth_established=True), lambda d: d.update(tags=['NF']),
    lambda d: d.update(extra='PRIVATE_CANARY'), lambda d: d.update(threshold=True),
    lambda d: d.update(threshold=float('nan')), lambda d: d.update(maximum_findings=True),
    lambda d: d['findings'][0]['reference'].update(source_span=[0, 999999]),
    lambda d: d['findings'][0]['reference'].update(document_id='policy'),
    lambda d: d['findings'][0].update(score=True), lambda d: d['findings'].reverse(),
    lambda d: d.update(findings=[]), lambda d: d['findings'][0].update(spans=[[1, 2]]),
])
def test_altered_prior_evidence_never_gets_reused(inputs, change):
    old, text, observation = inputs; observation = copy.deepcopy(observation); change(observation)
    with pytest.raises(r.RevisionError): r.review(old, old, text, observation, None, AT)


def test_prior_no_match_still_requires_new_selection_after_corpus_change(inputs):
    old, _, _ = inputs; text = 'Orange bicycle highway.'
    result = r.review(old, envelope({'new': text}), text, corpus_support.observe(old, text), None, AT)
    assert not result['findings'] and result['global_retrieval_must_rerun']


@pytest.mark.parametrize('target', ['old', 'new'])
def test_corrupt_corpus_refused_even_when_unreferenced(inputs, target):
    old, text, observation = inputs; changed = copy.deepcopy(old)
    changed['documents'][1]['text'] += 'PRIVATE_CANARY'
    with pytest.raises(r.RevisionError):
        r.review(changed if target == 'old' else old, changed if target == 'new' else old, text, observation, None, AT)


@pytest.mark.parametrize('raw', [b'', b'{"a":1,"a":2}', b'NaN', b'Infinity', b'1e999', b'\xff', b'['*1000, b' '*30001])
def test_bounded_json_refuses_duplicates_invalid_encoding_and_numbers(raw):
    with pytest.raises(r.RevisionError): r.decode(raw, r.MAX_OBSERVATION_BYTES)


@pytest.fixture
def private_cli(tmp_path, inputs):
    tmp_path.chmod(0o700)
    old, subject, observation = inputs
    new = envelope({'manual': 'Water is unsafe.\nThe fee is 25 dollars.\n', 'policy': 'Use a blue bicycle.\n'})
    files = {'old.json': corpus.encoded(old), 'new.json': corpus.encoded(new), 'subject.txt': subject.encode(),
             'observation.json': corpus.encoded(observation), 'windows.json': corpus.encoded(policy(new))}
    for name, raw in files.items():
        (tmp_path/name).write_bytes(raw); (tmp_path/name).chmod(0o600)
    command = [sys.executable, str(ROOT/'scripts/review-reference-revision.py'),
        '--previous-corpus', str(tmp_path/'old.json'), '--current-corpus', str(tmp_path/'new.json'),
        '--subject', str(tmp_path/'subject.txt'), '--observation', str(tmp_path/'observation.json'),
        '--review-windows', str(tmp_path/'windows.json'), '--at', AT]
    return tmp_path, command


def invoke(command):
    return subprocess.run(command, capture_output=True, text=True, timeout=15, cwd=ROOT)


def test_actual_cli_summary_and_explicit_private_details(private_cli):
    directory, command = private_cli
    first = invoke(command); assert first.returncode == 0
    public = json.loads(first.stdout); assert public['unchanged_pair_contexts'] == 1 and public['global_retrieval_must_rerun']
    assert not first.stderr and not public['details_saved'] and not (directory/'details').exists()
    second = invoke(command + ['--details', str(directory/'details')]); assert second.returncode == 0
    detailed = json.loads((directory/'details/reference-revision.json').read_text())
    assert len(detailed['findings']) == 2 and json.loads(second.stdout)['details_saved']
    assert (directory/'details').stat().st_mode & 0o777 == 0o700
    assert (directory/'details/reference-revision.json').stat().st_mode & 0o777 == 0o600
    third = invoke(command + ['--details', str(directory/'details')]); assert third.returncode == 2
    assert json.loads((directory/'details/reference-revision.json').read_text()) == detailed
    for value in ('Water', 'bicycle', str(directory), 'manual', 'document_sha256'):
        assert value not in first.stdout + first.stderr + second.stdout + second.stderr + third.stdout + third.stderr


@pytest.mark.parametrize('unsafe', ['public_file', 'public_directory', 'symlink', 'hardlink', 'fifo', 'invalid_utf8', 'oversize'])
def test_actual_cli_unsafe_private_input_refused_without_leaking(private_cli, unsafe):
    directory, command = private_cli; target = directory/'subject.txt'
    if unsafe == 'public_file': target.chmod(0o644)
    elif unsafe == 'public_directory': directory.chmod(0o755)
    elif unsafe == 'symlink': target.rename(directory/'saved'); target.symlink_to(directory/'saved')
    elif unsafe == 'hardlink': os.link(target, directory/'linked')
    elif unsafe == 'fifo': target.unlink(); os.mkfifo(target, 0o600)
    elif unsafe == 'invalid_utf8': target.write_bytes(b'\xffPRIVATE_CANARY')
    elif unsafe == 'oversize': target.write_bytes(b'PRIVATE_CANARY' + b'x'*8000)
    result = invoke(command)
    assert result.returncode == 2 and not result.stdout
    assert json.loads(result.stderr)['state'] == 'UNAVAILABLE'
    assert 'PRIVATE_CANARY' not in result.stderr and str(directory) not in result.stderr


def test_argparse_failure_does_not_echo_user_value(private_cli):
    _, command = private_cli
    result = invoke(command + ['--unknown', 'PRIVATE_CANARY'])
    assert result.returncode == 2 and 'PRIVATE_CANARY' not in result.stderr


@pytest.mark.parametrize('bad', ['null', '[]', 'true', '{"profile":"unknown"}'])
def test_actual_cli_explicit_window_file_cannot_silently_disappear(private_cli, bad):
    directory, command = private_cli
    (directory/'windows.json').write_text(bad)
    result = invoke(command)
    assert result.returncode == 2 and not result.stdout
    assert json.loads(result.stderr)['state'] == 'UNAVAILABLE'


def test_review_does_not_modify_any_captured_inputs(inputs):
    old, subject, observation = inputs
    declared = policy(old)
    before = corpus.encoded([old, observation, declared])
    check(inputs, windows=declared)
    assert corpus.encoded([old, observation, declared]) == before


def test_actual_practice_generator_and_full_review_workflow(tmp_path):
    tmp_path.chmod(0o700); target = tmp_path/'practice'
    command = [sys.executable, str(ROOT/'scripts/prepare-reference-revision-demo.py'), '--output', str(target)]
    created = invoke(command); assert created.returncode == 0
    assert json.loads(created.stdout)['files'] == 6 and str(target) not in created.stdout
    captured = {p.name: p.read_bytes() for p in target.iterdir()}
    review = [sys.executable, str(ROOT/'scripts/review-reference-revision.py'),
        '--previous-corpus', str(target/'old.json'), '--current-corpus', str(target/'new.json'),
        '--subject', str(target/'subject.txt'), '--observation', str(target/'observation.json'),
        '--review-windows', str(target/'windows.json'), '--at', AT]
    result = invoke(review); assert result.returncode == 0
    summary = json.loads(result.stdout)
    assert summary['unchanged_pair_contexts'] == summary['changed_or_removed_pair_contexts'] == 1
    assert summary['global_retrieval_must_rerun'] and not summary['tag_asserted']
    assert invoke(command).returncode == 2
    assert {p.name: p.read_bytes() for p in target.iterdir()} == captured


@pytest.mark.parametrize('unsafe', ['public_parent', 'output_symlink'])
def test_practice_generator_refuses_unsafe_or_existing_destination(tmp_path, unsafe):
    tmp_path.chmod(0o700); target = tmp_path/'practice'
    if unsafe == 'public_parent': tmp_path.chmod(0o755)
    else: target.symlink_to(tmp_path/'elsewhere')
    result = invoke([sys.executable, str(ROOT/'scripts/prepare-reference-revision-demo.py'), '--output', str(target)])
    assert result.returncode == 2 and not result.stdout
    assert not (tmp_path/'elsewhere').exists()
