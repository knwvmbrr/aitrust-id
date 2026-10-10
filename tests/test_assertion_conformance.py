"""Actual offline CLI over synthetic third-party records; no outside-user claim."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import pytest

ROOT = Path(__file__).resolve().parents[1]


def record():
    return {'assertion_id': 'eadf909b-7723-4431-b200-1a4cb56c538b', 'spec_version': '0.1.0',
            'subject': {'sha256': 'a'*64, 'char_len': 100, 'origin_host': 'chatgpt.com',
                        'captured_at': '2026-10-10T10:00:00Z', 'modality': 'text'},
            'tags': [{'code': 'PS', 'state': 'asserted', 'confidence': .97, 'floor': .7,
                      'signals': [{'id': 'sig.piped_installer.v3', 'score': .97, 'spans': [[4, 20]]}]}],
            'abstentions': [], 'evaluator': {'models': [{'name': 'rules-only', 'sha256': 'b'*64}],
                                           'calibration_id': 'synthetic', 'latency_ms': 1}}


def run(raw, profile='schema', file=None):
    command = [sys.executable, str(ROOT/'scripts/check-assertion.py'), '--profile', profile]
    if file is not None: command.append(str(file))
    result = subprocess.run(command, input=raw if file is None else None, capture_output=True, timeout=15)
    report = json.loads(result.stdout)
    assert not result.stderr
    assert report['signature_verified'] is False and report['certification'] is False
    return result.returncode, report


@pytest.mark.parametrize('profile', ['schema', 'extension'])
def test_valid_record_stdin_and_file(profile, tmp_path):
    raw = json.dumps(record()).encode(); file = tmp_path/'record.json'; file.write_bytes(raw)
    assert run(raw, profile)[0] == 0
    assert run(None, profile, file)[0] == 0


@pytest.mark.parametrize('raw', [b'{"secret":"private-canary", "secret":2}', b'NaN', b'1e999',
    b'"\\ud800"', b'\xff', b'{', b'[]', b' '* (2*1024*1024+1)], ids=['duplicate','nan','overflow','surrogate','utf8','broken','array','oversize'])
def test_bad_input_has_fixed_safe_error(raw):
    code, report = run(raw)
    assert code == 1 and report['status'] == 'invalid'
    assert 'private-canary' not in json.dumps(report)


@pytest.mark.parametrize('change', ['date', 'id', 'confidence', 'extra'])
def test_schema_failures(change):
    a = record()
    if change == 'date': a['subject']['captured_at'] = '2026-02-31T00:00:00Z'
    elif change == 'id': a['assertion_id'] = 'not-uuid'
    elif change == 'confidence': a['tags'][0]['confidence'] = 2
    else: a['private-canary'] = 'never printed'
    assert run(json.dumps(a).encode())[0] == 1


def test_unknown_version_is_not_migrated_or_guessed():
    a = record(); a['spec_version'] = '1.0.0'
    assert all(run(json.dumps(a).encode(), p)[0] == 2 for p in ['schema', 'extension'])
    assert a['spec_version'] == '1.0.0' and a['tags'][0]['code'] == 'PS'


def test_unknown_version_with_a_different_layout_is_unsupported_not_falsely_invalid():
    raw=b'{"spec_version":"0.2.0","new_layout":{"private-canary":true}}'
    for profile in ['schema','extension']:
        code,report=run(raw,profile)
        assert code==2 and report['reason']=='unsupported_version'
        assert 'private-canary' not in json.dumps(report)


def test_schema_pass_is_not_signature_verification_or_runtime_support():
    a = record(); a['signature'] = {'alg': 'ed25519', 'key_id': 'untrusted', 'sig': 'unverified'}
    assert run(json.dumps(a).encode())[0] == 0
    assert run(json.dumps(a).encode(), 'extension')[0] == 2
    a.pop('signature'); a['subject']['modality'] = 'image'
    assert run(json.dumps(a).encode())[0] == 0
    assert run(json.dumps(a).encode(), 'extension')[0] == 2


@pytest.mark.parametrize('change', ['floor', 'span', 'duplicate'])
def test_current_profile_refuses_schema_valid_semantic_errors(change):
    a = record()
    if change == 'floor': a['tags'][0]['confidence'] = .6
    elif change == 'span': a['tags'][0]['signals'][0]['spans'] = [[0,101]]
    else: a['tags'].append(copy.deepcopy(a['tags'][0]))
    assert run(json.dumps(a).encode())[0] == 0
    assert run(json.dumps(a).encode(), 'extension')[0] == 1


def test_missing_file_and_symlink_never_echo_path(tmp_path):
    file = tmp_path/'private-canary'; link = tmp_path/'link'; link.symlink_to(file)
    for path in (file,link):
        code, report = run(None, file=path)
        assert code == 3 and 'private-canary' not in json.dumps(report)
