"""Declared-date controls and model refusal are distinct from real source freshness."""
import copy
from datetime import datetime, timedelta, timezone
import json
import importlib.util
from pathlib import Path
import pytest
from protocol import corpus
from tools import reference_review_window as window
from tools.reference_revision import POLICY, MAX_POLICY_BYTES
from test_nli_reference_cli import cli, packet, fake_runner

NOW = datetime(2026, 10, 13, 12, tzinfo=timezone.utc)


def policy(record):
    return {'profile': POLICY, 'manifest_sha256': record['manifest_sha256'], 'documents': [
        {'document_id': d['id'], 'document_sha256': d['sha256'],
         'opens_at': '2026-10-01T00:00:00Z', 'expires_at': '2026-11-01T00:00:00Z'}
        for d in record['documents']]}


def guarded_args(packet, value=None):
    folder, record, path, query, _ = packet
    review = folder/'review.json'
    review.write_bytes(corpus.encoded(value if value is not None else policy(record)))
    review.chmod(0o600)
    return ['--corpus', str(path), '--subject', str(query), '--review-windows', str(review)], review


def test_active_window_remains_only_a_caller_declaration(packet):
    record = packet[1]; value = policy(record)
    before = window.preflight(record, value, NOW)
    after = window.preflight(record, value, NOW + timedelta(microseconds=1))
    result = window.summary(before, after)
    assert result['checked_before_and_after_comparison']
    assert not result['source_freshness_established'] and not result['reviewer_authenticated']
    assert set(result) == {'state', 'documents_checked', 'checked_before_and_after_comparison',
                           'source_freshness_established', 'reviewer_authenticated'}
    assert before['policy_sha256'] == corpus.sha(corpus.encoded(value))


@pytest.mark.parametrize('at,reason', [
    (datetime(2026, 9, 30, 23, 59, 59, 999999, timezone.utc), 'review_window_not_open'),
    (datetime(2026, 11, 1, tzinfo=timezone.utc), 'review_window_expired'),
    (datetime(2026, 11, 2, tzinfo=timezone.utc), 'review_window_expired')])
def test_unopened_and_elapsed_boundaries(packet, at, reason):
    with pytest.raises(window.WindowFailure) as failure:
        window.preflight(packet[1], policy(packet[1]), at)
    assert failure.value.category == reason


@pytest.mark.parametrize('at', [datetime(2026, 10, 1, tzinfo=timezone.utc),
                               datetime(2026, 10, 31, 23, 59, 59, 999999, timezone.utc)])
def test_start_inclusive_expiry_exclusive(packet, at):
    assert window.preflight(packet[1], policy(packet[1]), at)['documents_checked'] == 1


@pytest.mark.parametrize('kind', ['missing', 'duplicate', 'unknown', 'changed-manifest',
                                  'changed-document', 'extra-field', 'wrong-profile',
                                  'impossible-date', 'non-utc-date', 'empty-window'])
def test_bad_binding_or_policy_refuses(packet, kind):
    record = packet[1]; value = policy(record)
    if kind == 'missing': value['documents'] = []
    if kind == 'duplicate': value['documents'].append(copy.deepcopy(value['documents'][0]))
    if kind == 'unknown': value['documents'][0]['document_id'] = 'unknown'
    if kind == 'changed-manifest': value['manifest_sha256'] = '0'*64
    if kind == 'changed-document': value['documents'][0]['document_sha256'] = '0'*64
    if kind == 'extra-field': value['private-canary'] = 'secret'
    if kind == 'wrong-profile': value['profile'] = 'other'
    if kind == 'impossible-date': value['documents'][0]['opens_at'] = '2026-02-30T00:00:00Z'
    if kind == 'non-utc-date': value['documents'][0]['opens_at'] = '2026-10-01T00:00:00+01:00'
    if kind == 'empty-window': value['documents'][0]['opens_at'] = value['documents'][0]['expires_at']
    with pytest.raises(window.WindowFailure): window.preflight(record, value, NOW)


def test_policy_must_cover_all_attached_documents(packet):
    record = copy.deepcopy(packet[1]); other = {'id': 'other', 'text': 'An unrelated reference.'}
    other['sha256'] = corpus.sha(other['text'].encode()); record['documents'].append(other)
    record['manifest_sha256'] = corpus.sha(corpus.encoded({'format': record['format'], 'documents': record['documents']}))
    value = policy(record); value['documents'].pop()
    with pytest.raises(window.WindowFailure) as failure: window.preflight(record, value, NOW)
    assert failure.value.category == 'review_window_missing'


@pytest.mark.parametrize('at', [None, '2026-10-13T12:00:00Z', datetime(2026, 10, 13),
                               NOW.astimezone(timezone(timedelta(hours=1)))])
def test_clock_must_be_aware_utc(packet, at):
    with pytest.raises(window.WindowFailure): window.preflight(packet[1], policy(packet[1]), at)


@pytest.mark.parametrize('raw', [b'null', b'[]', b'{"x":1,"x":2}', b'{"x":NaN}',
                                b'{"x":Infinity}', b'\xff', b' '*(MAX_POLICY_BYTES+1)])
def test_bounded_strict_policy_decoder(raw):
    with pytest.raises(window.WindowFailure): window.capture(raw)


@pytest.mark.parametrize('kind', ['expired', 'unopened', 'missing', 'altered'])
def test_preflight_refusal_does_not_start_comparison_or_write_details(packet, monkeypatch, capsys, kind):
    value = policy(packet[1]); target = packet[0]/'details'
    if kind == 'expired': value['documents'][0]['expires_at'] = '2026-10-12T00:00:00Z'
    if kind == 'unopened': value['documents'][0]['opens_at'] = '2026-10-14T00:00:00Z'
    if kind == 'missing': value['documents'] = []
    if kind == 'altered': value['manifest_sha256'] = '0'*64
    args, _ = guarded_args(packet, value)
    monkeypatch.setattr(window, 'utc_now', lambda: NOW)
    monkeypatch.setattr(cli, 'check', lambda *a, **k: pytest.fail('refused policy started comparison'))
    assert cli.main(args+['--details', str(target)]) == 2
    output = capsys.readouterr(); assert not output.out and not target.exists()
    assert json.loads(output.err)['state'] == 'UNAVAILABLE'
    assert str(packet[0]) not in output.err and 'manual' not in output.err


def test_active_guard_keeps_existing_observation_and_saves_separate_private_record(packet, monkeypatch, capsys):
    args, _ = guarded_args(packet); target = packet[0]/'details'; actual = cli.check
    monkeypatch.setattr(window, 'utc_now', lambda: NOW)
    monkeypatch.setattr(cli, 'check', lambda record, subject, cache, threshold, maximum:
                        actual(record, subject, cache, threshold, maximum, runner=fake_runner()))
    assert cli.main(args+['--model-cache', str(packet[4]), '--threshold', '.4', '--details', str(target)]) == 0
    output = json.loads(capsys.readouterr().out)
    assert output['reference_freshness'] == 'unestablished' and not output['tag_asserted']
    assert output['declared_review_windows']['documents_checked'] == 1
    result = json.loads((target/'reference-observations.json').read_text())
    assert result['profile'] == 'retrieved-passage-nli-observation/1.0.0'
    assert 'declared_review_windows' not in result
    assert not target.stat().st_mode & 0o077
    for member in target.iterdir(): assert not member.stat().st_mode & 0o077
    before = {p.name: p.read_bytes() for p in target.iterdir()}
    assert cli.main(args+['--model-cache', str(packet[4]), '--threshold', '.4', '--details', str(target)]) == 2
    assert before == {p.name: p.read_bytes() for p in target.iterdir()}


@pytest.mark.parametrize('kind', ['expired', 'backwards'])
def test_post_comparison_time_refusal_saves_no_partial_result(packet, monkeypatch, capsys, kind):
    args, _ = guarded_args(packet); target = packet[0]/'details'; moments = iter([NOW,
        datetime(2026, 11, 1, tzinfo=timezone.utc) if kind == 'expired' else NOW-timedelta(seconds=1)])
    monkeypatch.setattr(window, 'utc_now', lambda: next(moments))
    calls=[]; actual = cli.check
    def compare(record, subject, cache, threshold, maximum):
        calls.append(True); return actual(record, subject, cache, threshold, maximum, runner=fake_runner())
    monkeypatch.setattr(cli, 'check', compare)
    assert cli.main(args+['--model-cache', str(packet[4]), '--threshold', '.4', '--details', str(target)]) == 2
    output = capsys.readouterr(); assert calls == [True] and not output.out and not target.exists()
    assert json.loads(output.err)['reason'] == ('review_window_expired' if kind == 'expired' else 'review_clock_changed')


@pytest.mark.parametrize('kind', ['public', 'symlink', 'hardlink', 'corrupt', 'oversize'])
def test_private_policy_refusal_has_no_echo(packet, monkeypatch, capsys, kind):
    args, path = guarded_args(packet)
    if kind == 'public': path.chmod(0o644)
    if kind == 'symlink': link=path.with_name('link'); link.symlink_to(path); args[-1]=str(link)
    if kind == 'hardlink': path.with_name('hard').hardlink_to(path)
    if kind == 'corrupt': path.write_bytes(b'{"private-canary":"corrupt"}')
    if kind == 'oversize': path.write_bytes(b'private-canary'*(MAX_POLICY_BYTES//10))
    monkeypatch.setattr(cli, 'check', lambda *a, **k: pytest.fail('unsafe policy started comparison'))
    assert cli.main(args) == 2
    output=capsys.readouterr(); assert not output.out and 'private-canary' not in output.err and str(packet[0]) not in output.err


def preparer():
    path=Path(__file__).resolve().parents[1]/'scripts/prepare-reference-review-windows.py'
    spec=importlib.util.spec_from_file_location('window_preparer',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


def test_prepare_bound_private_policy_without_review_claim(packet,capsys):
    prepare=preparer();target=packet[0]/'prepared'
    args=['--corpus',str(packet[2]),'--opens-at','2026-10-01T00:00:00Z',
          '--expires-at','2026-11-01T00:00:00Z','--output',str(target)]
    assert prepare.main(args)==0
    output=capsys.readouterr();assert str(packet[0]) not in output.out
    assert json.loads(output.out)['source_freshness_established'] is False
    saved=(target/'review-windows.json').read_bytes()
    assert window.preflight(packet[1],window.capture(saved),NOW)['documents_checked']==1
    assert not target.stat().st_mode&0o077 and not (target/'review-windows.json').stat().st_mode&0o077
    assert prepare.main(args)==2 and (target/'review-windows.json').read_bytes()==saved


@pytest.mark.parametrize('start,end',[('private-canary','2026-11-01T00:00:00Z'),
    ('2026-10-01T00:00:00Z','2026-10-01T00:00:00Z'),
    ('2026-11-01T00:00:00Z','2026-10-01T00:00:00Z')])
def test_preparation_refuses_invalid_dates_before_writing(packet,capsys,start,end):
    target=packet[0]/'bad'
    assert preparer().main(['--corpus',str(packet[2]),'--opens-at',start,'--expires-at',end,'--output',str(target)])==2
    output=capsys.readouterr();assert not output.out and 'private-canary' not in output.err and not target.exists()


def test_inconsistent_binding_between_checks_refuses(packet):
    before=window.preflight(packet[1],policy(packet[1]),NOW);after=copy.deepcopy(before)
    after['policy_sha256']='0'*64
    with pytest.raises(window.WindowFailure):window.summary(before,after)
