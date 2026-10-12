import importlib.util
import json
from pathlib import Path
import pytest
from tools import private_policy as tool

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('policy_cli', ROOT / 'scripts/check-private-policy.py')
cli = importlib.util.module_from_spec(spec); spec.loader.exec_module(cli)
spec = importlib.util.spec_from_file_location('policy_demo', ROOT / 'scripts/prepare-private-policy-demo.py')
demo = importlib.util.module_from_spec(spec); spec.loader.exec_module(demo)


@pytest.fixture
def packet(tmp_path, capsys):
    tmp_path.chmod(0o700); packet = tmp_path / 'practice'
    assert demo.main(['--output', str(packet)]) == 0
    output = capsys.readouterr(); assert json.loads(output.out)['synthetic_only']
    return packet


def test_explicit_local_review_required_before_reading_any_packet(packet, capsys):
    assert cli.main(['--packet', str(packet)]) == 2
    output = capsys.readouterr(); assert not output.out and str(packet) not in output.err
    assert json.loads(output.err)['state'] == 'UNAVAILABLE'


def test_short_result_and_optional_owner_private_details(packet, capsys):
    args = ['--packet', str(packet), '--reviewed-policy']
    assert cli.main(args) == 0
    summary = json.loads(capsys.readouterr().out)
    assert summary['literal_occurrences'] == 1 and not summary['compliance_established']
    assert not summary['public_tag_asserted'] and not summary['standard_namespace_adopted']
    assert not any(key in summary for key in ['subject_sha256', 'policy_sha256', 'observations', 'namespace'])
    assert 'confidential draft' not in json.dumps(summary)
    target = packet.parent / 'details'; assert cli.main(args + ['--details', str(target)]) == 0
    item = target / 'private-policy-observations.json'; original = item.read_bytes()
    assert json.loads(original)['observations'][0]['qualified_code'] == 'example-team:DRAFT'
    assert target.stat().st_mode & 0o077 == 0 and item.stat().st_mode & 0o077 == 0
    assert cli.main(args + ['--details', str(target)]) == 2 and item.read_bytes() == original
    output = capsys.readouterr(); assert str(packet) not in output.out + output.err


@pytest.mark.parametrize('name', ['subject.txt', 'policy.json', 'selection.json'])
@pytest.mark.parametrize('kind', ['public', 'symlink', 'hardlink'])
def test_unsafe_private_files_refuse_without_echo(packet, capsys, name, kind):
    path = packet / name
    if kind == 'public': path.chmod(0o644)
    if kind == 'symlink':
        moved = packet / 'original'; path.rename(moved); path.symlink_to(moved)
    if kind == 'hardlink': (packet / 'additional').hardlink_to(path)
    assert cli.main(['--packet', str(packet), '--reviewed-policy']) == 2
    output = capsys.readouterr(); assert not output.out and str(packet) not in output.err
    assert 'confidential draft' not in output.err


@pytest.mark.parametrize('kind', ['duplicate', 'bad-utf8', 'over-limit', 'changed-subject', 'changed-policy', 'wrong-namespace', 'nonfinite', 'hidden-threshold'])
def test_invalid_or_stale_packet_never_returns_partial_observations(packet, capsys, kind):
    subject = packet / 'subject.txt'; policy = packet / 'policy.json'; selection = packet / 'selection.json'
    if kind == 'duplicate': selection.write_text('{"private-canary":1,"private-canary":2}')
    if kind == 'bad-utf8': subject.write_bytes(b'private-canary\xff')
    if kind == 'over-limit': subject.write_text('a' * 20001)
    if kind == 'changed-subject': subject.write_text('Other confidential draft.')
    if kind == 'changed-policy': policy.write_text(policy.read_text() + ' ')
    if kind == 'wrong-namespace':
        record = json.loads(selection.read_text()); record['namespace'] = 'other-team'; selection.write_text(json.dumps(record))
    if kind == 'nonfinite': policy.write_text('{"private-canary":NaN}')
    if kind == 'hidden-threshold':
        record = json.loads(policy.read_text()); record['public_thresholds'] = {'PS': 0}; policy.write_text(json.dumps(record))
        context = json.loads(selection.read_text()); context['policy_sha256'] = tool.sha(policy.read_bytes()); selection.write_text(json.dumps(context))
    assert cli.main(['--packet', str(packet), '--reviewed-policy']) == 2
    output = capsys.readouterr(); assert not output.out and str(packet) not in output.err and 'private-canary' not in output.err


def test_demo_never_overwrites_and_does_not_require_account_or_detector(packet, capsys):
    original = {p.name: p.read_bytes() for p in packet.iterdir()}
    assert demo.main(['--output', str(packet)]) == 2
    assert {p.name: p.read_bytes() for p in packet.iterdir()} == original
    assert set(original) == {'subject.txt', 'policy.json', 'selection.json'}
    assert all(p.stat().st_mode & 0o077 == 0 for p in packet.iterdir())
    output = capsys.readouterr(); assert str(packet) not in output.out + output.err


def test_argument_parser_never_echoes_a_private_value(capsys):
    with pytest.raises(SystemExit) as failure:
        cli.main(['--private-canary'])
    assert failure.value.code == 2 and 'private-canary' not in capsys.readouterr().err
