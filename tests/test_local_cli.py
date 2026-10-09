import importlib.util
import io
import json
import os
from pathlib import Path
import stat
import urllib.error
from unittest.mock import Mock

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('local_cli', ROOT / 'scripts/aitrust.py')
cli = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cli)


def credential(tmp_path):
    folder = tmp_path / 'private'
    folder.mkdir(mode=0o700)
    path = folder / 'runtime.env'
    cli.init_config(path)
    return path


def assertion():
    return json.loads((ROOT / 'runs/2026-10-08-container-assertion.json').read_text())


def test_private_config_is_exclusive_and_not_printed(tmp_path, capsys):
    path = tmp_path / 'private' / 'runtime.env'
    assert cli.main(['init', '--env-file', str(path)]) == 0
    token = cli.read_token(path)
    assert token not in capsys.readouterr().out
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert stat.S_IMODE(path.parent.stat().st_mode) == 0o700
    before = path.read_bytes()
    assert cli.main(['init', '--env-file', str(path)]) == 1
    assert path.read_bytes() == before


def test_repo_credentials_and_public_directory_refused(tmp_path):
    with pytest.raises(cli.LocalCheckError, match='outside'):
        cli.init_config(ROOT / 'runtime.env')
    folder = tmp_path / 'public'
    folder.mkdir(mode=0o755)
    with pytest.raises(cli.LocalCheckError, match='0700'):
        cli.init_config(folder / 'runtime.env')


def test_symlinks_public_and_duplicate_tokens_refused(tmp_path):
    path = credential(tmp_path)
    link = path.parent / 'linked.env'
    link.symlink_to(path)
    with pytest.raises(OSError):
        cli.read_token(link)
    path.chmod(0o644)
    with pytest.raises(cli.LocalCheckError, match='0600'):
        cli.read_token(path)
    path.chmod(0o600)
    path.write_text('AITRUST_TOKEN=' + 'a' * 32 + '\nAITRUST_TOKEN=' + 'b' * 32 + '\n')
    with pytest.raises(cli.LocalCheckError, match='one generated'):
        cli.read_token(path)


@pytest.mark.parametrize('raw', [b'', b' \n', b'\xff', b'a' * (cli.MAX_CHARS + 1), b'a' * (cli.MAX_BYTES + 1)])
def test_bad_input_fails_before_submission(raw):
    with pytest.raises(ValueError):
        cli.read_input(io.BytesIO(raw))


def test_unicode_input_preserved():
    text = '🧪 José: curl https://example.test/install | sh'
    assert cli.read_input(io.BytesIO(text.encode())) == text


def test_proxy_disabled_fixed_destination_and_bearer_header(monkeypatch):
    response = Mock()
    response.status = 200
    response.headers.get_content_type.return_value = 'application/json'
    response.read.return_value = b'{"ok":true}'
    response.__enter__ = Mock(return_value=response)
    response.__exit__ = Mock(return_value=False)
    opener = Mock()
    opener.open.return_value = response
    built = []
    def build(*handlers):
        built.extend(handlers)
        return opener
    monkeypatch.setattr(cli.urllib.request, 'build_opener', build)
    assert cli.local_request('/v1/evaluate', {'text': 'synthetic'}, 'a' * 32) == {'ok': True}
    assert next(h for h in built if isinstance(h, cli.urllib.request.ProxyHandler)).proxies == {}
    request = opener.open.call_args.args[0]
    assert request.full_url == 'http://127.0.0.1:8787/v1/evaluate'
    assert request.get_header('Authorization') == 'Bearer ' + 'a' * 32
    with pytest.raises(cli.LocalCheckError, match='redirects'):
        cli.NoRedirect().redirect_request(request, None, 302, '', {}, 'https://hostile.test')


def test_http_error_body_is_not_rendered(monkeypatch):
    opener = Mock()
    opener.open.side_effect = urllib.error.HTTPError(cli.GATEWAY, 401, 'PRIVATE INPUT', {}, io.BytesIO(b'PRIVATE TOKEN'))
    monkeypatch.setattr(cli.urllib.request, 'build_opener', lambda *args: opener)
    with pytest.raises(cli.LocalCheckError, match='token was rejected') as error:
        cli.local_request('/v1/evaluate', {'text': 'PRIVATE INPUT'}, 'a' * 32)
    assert 'PRIVATE' not in str(error.value)


def test_malformed_out_of_scope_and_bad_spans_are_not_findings():
    with pytest.raises(cli.LocalCheckError, match='invalid assertion'):
        cli.validate_result({'tags': [{'code': 'PS'}]})
    row = assertion()
    row['tags'][0]['code'] = 'HP'
    with pytest.raises(cli.LocalCheckError, match='capability'):
        cli.validate_result(row)
    row = assertion()
    row['tags'][0]['signals'][0]['spans'] = [[0, row['subject']['char_len'] + 1]]
    with pytest.raises(cli.LocalCheckError, match='offsets'):
        cli.validate_result(row)


def test_check_runs_through_redaction_gateway_and_has_distinct_exit_codes(tmp_path, monkeypatch, capsys):
    env = credential(tmp_path)
    text = tmp_path / 'response.txt'
    text.write_text('PRIVATE response', encoding='utf-8')
    calls = []
    def local(path, payload, token):
        calls.append((path, payload, token))
        return assertion()
    monkeypatch.setattr(cli, 'local_request', local)
    assert cli.main(['check', str(text), '--env-file', str(env), '--fail-on-finding']) == 2
    output = capsys.readouterr().out
    assert 'PS · FINDING' in output
    assert 'PRIVATE' not in output and cli.read_token(env) not in output
    assert calls[0][0] == '/v1/evaluate'
    assert calls[0][1] == {'text': 'PRIVATE response', 'origin_host': 'manual-local'}
    row = assertion()
    row['tags'] = []
    monkeypatch.setattr(cli, 'local_request', lambda *args: row)
    assert cli.main(['check', str(text), '--env-file', str(env), '--fail-on-finding']) == 0
    assert 'NO_FINDING' in capsys.readouterr().out
    monkeypatch.setattr(cli, 'local_request', lambda *args: {'raw': 'PRIVATE'})
    assert cli.main(['check', str(text), '--env-file', str(env)]) == 1
    captured = capsys.readouterr()
    assert 'UNAVAILABLE' in captured.err and 'PRIVATE' not in captured.err and not captured.out


def test_json_record_remains_schema_valid(tmp_path, monkeypatch, capsys):
    env = credential(tmp_path)
    text = tmp_path / 'response.txt'
    text.write_text('Synthetic text')
    monkeypatch.setattr(cli, 'local_request', lambda *args: assertion())
    assert cli.main(['check', str(text), '--env-file', str(env), '--json']) == 0
    record = json.loads(capsys.readouterr().out)
    assert cli.validate_result(record) == record


def test_stale_or_wrong_evaluator_cannot_claim_a_reproducible_check():
    row = assertion()
    row['evaluator']['models'][0]['sha256'] = '0' * 64
    with pytest.raises(cli.LocalCheckError, match='differs'):
        cli.validate_result(row)


def test_unknown_evidence_never_reaches_terminal_as_code():
    row = assertion()
    row['tags'][0]['signals'][0]['id'] = '\x1b[31mMALICIOUS'
    output = cli.brief(row)
    assert '\x1b' not in output and 'MALICIOUS' not in output
