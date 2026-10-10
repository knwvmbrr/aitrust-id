"""Real public timestamp verification; mocked transport tests are not independence evidence."""
import hashlib
import http.client
import json
import os
import runpy
from pathlib import Path
import subprocess
import sys
import urllib.request

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import independent_timestamp as ts

FIXTURE = ROOT / 'tests/fixtures/timestamp-freetsa-2026'


def inputs():
    return [FIXTURE / name for name in ['artifact.txt', 'request.tsq', 'response.tsr', 'ca.pem', 'tsa.pem']]


def test_public_token_binds_digest_nonce_and_exact_authority():
    result = ts.verify(*inputs())
    manifest = json.loads((FIXTURE / 'manifest.json').read_text())
    assert result['authority_time'] == manifest['authority_time']
    assert result['artifact_binding'] == result['nonce_binding'] == 'matched'
    assert result['revocation'] == 'unchecked'
    assert result['authorship'] == 'unestablished'
    assert result['certified_valid'] is result['tag_issuance'] is False


def test_public_evidence_exact_bytes():
    for name, expected in json.loads((FIXTURE / 'manifest.json').read_text())['files'].items():
        assert hashlib.sha256((FIXTURE / name).read_bytes()).hexdigest() == expected


def test_public_composition_receipt_and_independent_timestamp_are_both_reproducible():
    # Explicit historical test clock checks the original receipt window, not its
    # current validity. The detached timestamp never changes the signed receipt.
    script = """
const fs=require('node:fs'),r=require('./protocol/receipts.cjs');
const root=process.argv[1], envelope=r.parse(fs.readFileSync(root+'/composition-receipt.json'));
const key=fs.readFileSync(root+'/receipt-public.pem'),payload=r.verify(envelope,key);
const result=r.inspectReceipt(envelope,key,fs.readFileSync(root+'/artifact.txt'),payload.issued_at+1);
if(result.authorship!=='unestablished'||result.revocation!=='unchecked'||result.certified_valid!==false)process.exit(1);
"""
    subprocess.run(['node', '-e', script, str(FIXTURE)], cwd=ROOT, check=True, capture_output=True)
    result = ts.verify(FIXTURE / 'composition-receipt.json', FIXTURE / 'composition-request.tsq',
                       FIXTURE / 'composition-response.tsr', FIXTURE / 'ca.pem', FIXTURE / 'tsa.pem')
    assert result['authority_time'] == json.loads((FIXTURE / 'manifest.json').read_text())['composition_authority_time']
    assert result['authorship'] == 'unestablished' and result['revocation'] == 'unchecked'


@pytest.mark.parametrize('index', [0, 1, 2, 3, 4])
def test_altered_artifact_nonce_response_and_authority_refused(tmp_path, index):
    args = inputs()
    raw = args[index].read_bytes()
    altered = tmp_path / 'changed'
    at = len(raw) // 2
    altered.write_bytes(raw[:at] + bytes([raw[at] ^ 1]) + raw[at + 1:])
    args[index] = altered
    with pytest.raises(ValueError):
        ts.verify(*args)


def test_wrong_nonce_even_with_valid_artifact_refused(tmp_path):
    query = subprocess.check_output(['openssl', 'ts', '-query', '-digest',
                                      ts.digest(inputs()[0].read_bytes()), '-sha256', '-cert'])
    file = tmp_path / 'another-query'; file.write_bytes(query)
    args = inputs(); args[1] = file
    with pytest.raises(ValueError):
        ts.verify(*args)


def test_absent_nonce_refused(tmp_path):
    query = subprocess.check_output(['openssl', 'ts', '-query', '-digest',
                                      ts.digest(inputs()[0].read_bytes()), '-sha256', '-cert', '-no_nonce'])
    file = tmp_path / 'no-nonce'; file.write_bytes(query)
    args = inputs(); args[1] = file
    with pytest.raises(ValueError, match='nonce'):
        ts.verify(*args)


@pytest.mark.parametrize('index', [0, 1, 2, 3, 4])
def test_missing_inputs_refused(tmp_path, index):
    args = inputs(); args[index] = tmp_path / 'missing'
    with pytest.raises(OSError):
        ts.verify(*args)


def test_symlink_and_fifo_read_refused(tmp_path):
    link = tmp_path / 'link'; link.symlink_to(inputs()[0])
    with pytest.raises(OSError):
        ts.read(link)
    fifo = tmp_path / 'fifo'; os.mkfifo(fifo)
    with pytest.raises(ValueError):
        ts.read(fifo)


def test_size_bounds_precede_cryptographic_calls():
    def never(*args, **kwargs):
        pytest.fail('Must refuse before cryptographic command')
    for raw, query, response in [(b'x' * (ts.MAX_ARTIFACT + 1), b'a', b'b'),
                                  (b'a', b'x' * (ts.MAX_EVIDENCE + 1), b'b'),
                                  (b'a', b'b', b'x' * (ts.MAX_EVIDENCE + 1)),
                                  (b'a', b'', b'b')]:
        with pytest.raises(ValueError):
            ts.verify_bytes(raw, query, response, inputs()[3], inputs()[4], never)


@pytest.mark.parametrize('consent', [False, None, 1, 'yes'])
def test_no_network_without_exact_consent(tmp_path, consent):
    def never(query):
        pytest.fail('No permission to contact provider')
    with pytest.raises(ValueError):
        ts.issue(inputs()[0], tmp_path / 'new', inputs()[3], inputs()[4], consent, never)


def test_wrong_authority_refuses_before_contact(tmp_path):
    def never(query):
        pytest.fail('Untrusted authority must not be contacted')
    bad = tmp_path / 'bad.pem'; bad.write_text('Not a trusted certificate')
    with pytest.raises(ValueError):
        ts.issue(inputs()[0], tmp_path / 'new', bad, inputs()[4], True, never)


def test_existing_output_refuses_before_contact(tmp_path):
    def never(query):
        pytest.fail('Must not contact provider for an unusable destination')
    with pytest.raises(ValueError):
        ts.issue(inputs()[0], tmp_path, inputs()[3], inputs()[4], True, never)


@pytest.mark.parametrize('parent_kind', ['missing', 'file', 'symlink'])
def test_unusable_parent_refuses_before_query_or_contact(tmp_path, parent_kind):
    parent = tmp_path / 'parent'
    if parent_kind == 'file':
        parent.write_text('not a directory')
    elif parent_kind == 'symlink':
        parent.symlink_to(tmp_path, target_is_directory=True)
    def never(*args, **kwargs):
        pytest.fail('Unusable output must refuse before query generation or provider contact')
    with pytest.raises(ValueError):
        ts.issue(inputs()[0], parent / 'new', inputs()[3], inputs()[4], True, never, never)


@pytest.mark.parametrize('error', [http.client.BadStatusLine('malformed'),
                                 http.client.IncompleteRead(b'partial')])
def test_malformed_provider_http_uses_cli_refusal(monkeypatch, capsys, tmp_path, error):
    def broken(*args, **kwargs):
        raise error
    monkeypatch.setattr(ts, 'issue', broken)
    monkeypatch.setattr(sys, 'argv', ['timestamp-artifact.py', 'request', str(inputs()[0]),
                        '--ca-file', str(inputs()[3]), '--tsa-file', str(inputs()[4]),
                        '--output-dir', str(tmp_path / 'new'), '--send-digest'])
    with pytest.raises(SystemExit) as exit:
        runpy.run_path(str(ROOT / 'scripts/timestamp-artifact.py'), run_name='__main__')
    captured = capsys.readouterr()
    assert exit.value.code == 2 and not captured.out
    assert 'Timestamp refused:' in captured.err and 'Traceback' not in captured.err
    assert not (tmp_path / 'new').exists()


def test_redirect_refused():
    with pytest.raises(ValueError):
        ts.NoRedirect().redirect_request(None, None, 302, '', {}, 'https://another.invalid/')


def test_missing_openssl_refuses():
    def missing(*args, **kwargs):
        raise FileNotFoundError('Missing openssl')
    with pytest.raises(FileNotFoundError):
        ts.verify(*inputs(), runner=missing)


def test_authority_and_imprint_checks_cannot_be_omitted():
    calls = []
    def recording(argv, **kwargs):
        calls.append(argv)
        return subprocess.run(argv, **kwargs)
    ts.verify(*inputs(), runner=recording)
    verify = [args for args in calls if args[1:3] == ['ts', '-verify']]
    assert len(verify) == 2
    assert '-queryfile' in verify[0] and '-digest' in verify[1]
    assert all('-CAstore' in args and '-CApath' in args and '-CAfile' in args for args in verify)
    cms = next(args for args in calls if args[1:3] == ['cms', '-verify'])
    assert '-nointern' in cms and '-certfile' in cms and '-no-CApath' in cms and '-no-CAstore' in cms


def test_mock_transport_output_transaction_keeps_only_evidence(tmp_path):
    # Reusing this public request is a mocked transport control, not a fresh token.
    def runner(argv, **kwargs):
        if argv[1:3] == ['ts', '-query'] and '-in' not in argv:
            return subprocess.CompletedProcess(argv, 0, inputs()[1].read_bytes(), b'')
        return subprocess.run(argv, **kwargs)
    seen = []
    def transport(query):
        seen.append(query)
        return inputs()[2].read_bytes()
    out = tmp_path / 'new'
    result = ts.issue(inputs()[0], out, inputs()[3], inputs()[4], True, transport, runner)
    assert result['pass']
    assert len(seen) == 1 and inputs()[0].read_bytes() not in seen[0]
    assert {file.name for file in out.iterdir()} == {'request.tsq', 'response.tsr', 'verification.json'}
    assert out.stat().st_mode & 0o777 == 0o700
    assert all(file.stat().st_mode & 0o777 == 0o600 for file in out.iterdir())


def test_invalid_response_creates_no_accepted_bundle(tmp_path):
    out = tmp_path / 'new'
    with pytest.raises(ValueError):
        ts.issue(inputs()[0], out, inputs()[3], inputs()[4], True, lambda _: b'not a timestamp')
    assert not out.exists()


def test_cli_offline_success_and_failure(tmp_path):
    artifact, query, response, ca, tsa = inputs()
    argv = [sys.executable, str(ROOT / 'scripts/timestamp-artifact.py'), 'verify', str(artifact),
            '--query', str(query), '--response', str(response), '--ca-file', str(ca), '--tsa-file', str(tsa)]
    r = subprocess.run(argv, capture_output=True)
    assert r.returncode == 0 and json.loads(r.stdout)['pass']
    bad = tmp_path / 'bad'; bad.write_bytes(b'changed')
    argv[3] = str(bad)
    r = subprocess.run(argv, capture_output=True)
    assert r.returncode == 2 and not r.stdout
