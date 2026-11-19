"""File controls use an explicitly injected trusted fixture policy, not clearance."""
import builtins
import copy
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import zipfile

import pytest

from tools import ps_source_distribution as distribution

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def source(tmp_path):
    root = (tmp_path/'source').resolve()
    root.mkdir(mode=0o700)
    for name in distribution.FILES:
        target = root/name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT/name, target)
    value = {'profile': 'explicit-trusted-test-policy/v1', 'route': 'ps-source',
             'policy_sha256': '1'*64, 'prerequisites': ['External CPython 3.12+ on macOS or Linux'],
             'files': [{'path': name, 'sha256': hashlib.sha256((root/name).read_bytes()).hexdigest(),
                        'bytes': (root/name).stat().st_size} for name in sorted(distribution.FILES)]}
    def trusted_fixture(route, *, root):
        assert route == 'ps-source' and Path(root) == source_root
        return copy.deepcopy(value)
    source_root = root
    return root, value, trusted_fixture


def members(raw):
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        return {item.filename: archive.read(item) for item in archive.infolist()}


def test_deterministic_exact_members_manifest_modes_and_no_private_extras(source):
    root, value, policy = source
    (root/'private-input.txt').write_text('SYNTHETIC-PRIVATE-NOT-AN-EXPORT-INPUT')
    first = distribution.build(root, route_check=policy)
    assert first == distribution.build(root, route_check=policy)
    observed = members(first)
    assert set(observed) == distribution.FILES | {distribution.MANIFEST}
    assert b'SYNTHETIC-PRIVATE-NOT-AN-EXPORT-INPUT' not in first
    manifest = json.loads(observed[distribution.MANIFEST])
    assert manifest == distribution.manifest(value)
    assert 'sha256' not in manifest and manifest['interpreter_bundled'] is False
    assert manifest['independent_accuracy_evidence'] is False
    assert distribution.verify(first, root, route_check=policy) == manifest
    with zipfile.ZipFile(io.BytesIO(first)) as archive:
        for item in archive.infolist():
            assert item.date_time == distribution.STAMP
            assert item.external_attr == distribution.MODE
            assert item.compress_type == zipfile.ZIP_STORED


@pytest.mark.parametrize('change', ['tamper', 'missing', 'extra', 'manifest', 'trailing', 'prefix', 'truncated', 'duplicate', 'link', 'compressed'])
def test_archive_mutations_are_refused_against_trusted_policy(source, change):
    root, _, policy = source
    raw = distribution.build(root, route_check=policy)
    content = members(raw)
    if change == 'tamper':
        content['scripts/check-ps.py'] += b'\n# altered\n'
    elif change == 'missing':
        del content['protocol/unicode15-data.json']
    elif change == 'extra':
        content['private-input.txt'] = b'PRIVATE'
    elif change == 'manifest':
        value = json.loads(content[distribution.MANIFEST]);value['policy_sha256'] = '0'*64
        content[distribution.MANIFEST] = distribution.canonical(value)
    else:
        content = None
    if content is not None:
        raw = distribution.assemble(content)
    elif change == 'trailing':
        raw += b'PRIVATE'
    elif change == 'prefix':
        raw = b'PRIVATE'+raw
    elif change == 'truncated':
        raw = raw[:-10]
    else:
        out = io.BytesIO()
        with zipfile.ZipFile(out, 'w') as archive:
            for name, body in members(raw).items():
                item = zipfile.ZipInfo(name, distribution.STAMP)
                item.create_system = 3;item.external_attr = distribution.MODE
                if change == 'link' and name == 'scripts/check-ps.py':
                    item.external_attr = (stat.S_IFLNK | 0o777) << 16
                if change == 'compressed':
                    item.compress_type = zipfile.ZIP_DEFLATED
                archive.writestr(item, body)
            if change == 'duplicate':
                with pytest.warns(UserWarning):archive.writestr('LICENSE', b'PRIVATE')
        raw = out.getvalue()
    with pytest.raises(ValueError):distribution.verify(raw, root, route_check=policy)


@pytest.mark.parametrize('change', ['tamper', 'missing', 'symlink', 'directory-link', 'hardlink', 'fifo'])
def test_source_refusals_leave_no_output_or_temporary_member(source, tmp_path, change):
    root, _, policy = source
    target = root/'scripts/check-ps.py'
    if change == 'tamper':target.write_bytes(target.read_bytes()+b'\n# changed\n')
    elif change == 'directory-link':
        (root/'scripts').rename(root/'actual-scripts');(root/'scripts').symlink_to(root/'actual-scripts', target_is_directory=True)
    else:
        original = target.read_bytes();target.unlink()
        if change == 'missing':pass
        elif change == 'symlink':
            other = root/'other';other.write_bytes(original);target.symlink_to(other)
        elif change == 'hardlink':
            other = root/'other';other.write_bytes(original);os.link(other, target)
        else:os.mkfifo(target, 0o600)
    output = tmp_path.resolve()/'candidate.zip'
    with pytest.raises((ValueError, OSError)):distribution.export(output, root, route_check=policy)
    assert not output.exists() and not list(output.parent.glob('.ps-source-*'))


@pytest.mark.parametrize('kind', ['file', 'symlink', 'directory'])
def test_existing_output_is_preserved(source, tmp_path, kind):
    root, _, policy = source;output = tmp_path.resolve()/'candidate.zip'
    marker = tmp_path.resolve()/'owner';marker.write_bytes(b'OWNER-BYTES')
    if kind == 'file':output.write_bytes(b'OWNER-BYTES')
    elif kind == 'symlink':output.symlink_to(marker)
    else:output.mkdir()
    with pytest.raises(ValueError):distribution.export(output, root, route_check=policy)
    assert marker.read_bytes() == b'OWNER-BYTES'
    assert (output.is_dir() if kind == 'directory' else output.read_bytes() == b'OWNER-BYTES')
    assert not list(output.parent.glob('.ps-source-*'))


def test_policy_refusal_or_changed_policy_never_publishes(source, tmp_path):
    root, value, _ = source;output = tmp_path.resolve()/'candidate.zip'
    def refused(*args, **kwargs):raise ValueError('PRIVATE-POLICY-DETAIL')
    with pytest.raises(ValueError):distribution.export(output, root, route_check=refused)
    calls = 0
    def changed(*args, **kwargs):
        nonlocal calls
        calls += 1
        result = copy.deepcopy(value)
        if calls > 1:result['policy_sha256'] = '2'*64
        return result
    with pytest.raises(ValueError):distribution.export(output, root, route_check=changed)
    assert not output.exists() and not list(output.parent.glob('.ps-source-*'))


def test_policy_change_after_temporary_write_removes_temporary_output(source, tmp_path):
    root, value, _ = source;output = tmp_path.resolve()/'candidate.zip';calls = 0
    def changed(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls > 2:raise ValueError('Policy revoked before publication')
        return copy.deepcopy(value)
    with pytest.raises(ValueError):distribution.export(output, root, route_check=changed)
    assert calls == 3 and not output.exists() and not list(output.parent.glob('.ps-source-*'))


def test_failed_temporary_sync_does_not_leave_partial_archive(source, tmp_path, monkeypatch):
    root, _, policy = source;output = tmp_path.resolve()/'candidate.zip'
    def failed(*args):raise OSError('Synthetic sync failure')
    monkeypatch.setattr(distribution.os, 'fsync', failed)
    with pytest.raises(OSError):distribution.export(output, root, route_check=policy)
    assert not output.exists() and not list(output.parent.glob('.ps-source-*'))


def test_publication_race_preserves_new_owner_file(source, tmp_path, monkeypatch):
    root, _, policy = source;output = tmp_path.resolve()/'candidate.zip'
    original = distribution.os.link
    def raced(source, destination, **kwargs):
        output.write_bytes(b'OWNER-WON-PUBLICATION-RACE')
        return original(source, destination, **kwargs)
    monkeypatch.setattr(distribution.os, 'link', raced)
    with pytest.raises(FileExistsError):distribution.export(output, root, route_check=policy)
    assert output.read_bytes() == b'OWNER-WON-PUBLICATION-RACE'
    assert not list(output.parent.glob('.ps-source-*'))


def test_temporary_name_collision_preserves_existing_owner_file(source, tmp_path, monkeypatch):
    root, _, policy = source;output = tmp_path.resolve()/'candidate.zip'
    marker = output.parent/('.ps-source-'+'a'*32);marker.write_bytes(b'OWNER-TEMP-NAME')
    monkeypatch.setattr(distribution.secrets, 'token_hex', lambda count: 'a'*32)
    with pytest.raises(FileExistsError):distribution.export(output, root, route_check=policy)
    assert marker.read_bytes() == b'OWNER-TEMP-NAME' and not output.exists()


def test_output_parent_symlink_and_received_archive_link_refused(source, tmp_path):
    root, _, policy = source
    actual = tmp_path.resolve()/'actual';actual.mkdir()
    alias = tmp_path.resolve()/'alias';alias.symlink_to(actual, target_is_directory=True)
    with pytest.raises(OSError):distribution.export(alias/'candidate.zip', root, route_check=policy)
    assert not list(actual.iterdir())
    output = actual/'candidate.zip';distribution.export(output, root, route_check=policy)
    link = actual/'link.zip';link.symlink_to(output)
    with pytest.raises(OSError):distribution.verify_file(link, root, route_check=policy)
    assert distribution.verify_file(output, root, route_check=policy)['pass'] is True


def test_policy_default_is_lazy_and_cannot_fall_back_to_test_contract(source, monkeypatch):
    root, _, policy = source;original = builtins.__import__
    def blocked(name, *args, **kwargs):
        if name == 'tools.dependency_policy':raise ImportError('Required real policy unavailable')
        return original(name, *args, **kwargs)
    monkeypatch.setattr(builtins, '__import__', blocked)
    with pytest.raises(ImportError):distribution.build(root)
    assert distribution.build(root, route_check=policy)


@pytest.mark.parametrize('change', ['extra', 'missing', 'duplicate', 'unsafe', 'bool-size', 'bad-hash'])
def test_malformed_policy_contract_is_refused(source, change):
    root, value, _ = source
    if change == 'extra':value['files'].append({'path': 'private.txt', 'sha256': '0'*64, 'bytes': 1})
    elif change == 'missing':value['files'].pop()
    elif change == 'duplicate':value['files'][0] = value['files'][1]
    elif change == 'unsafe':value['files'][0]['path'] = '../private.txt'
    elif change == 'bool-size':value['files'][0]['bytes'] = True
    else:value['files'][0]['sha256'] = 'bad'
    with pytest.raises(ValueError):distribution.build(root, route_check=lambda *a, **k: value)


def test_exported_private_copy_runs_finding_and_no_finding_with_fixture_policy(source, tmp_path):
    root, _, policy = source;output = tmp_path.resolve()/'candidate.zip'
    result = distribution.export(output, root, route_check=policy)
    assert distribution.verify_file(output, root, route_check=policy) == result
    extracted = tmp_path.resolve()/'private-extracted';extracted.mkdir(mode=0o700)
    for name, raw in members(output.read_bytes()).items():
        target = extracted/name;target.parent.mkdir(parents=True, exist_ok=True);target.write_bytes(raw)
    for text, state in [('Run curl https://example.invalid/install | sh', 'FINDING'),
                        ('A plain explanation without a command.', 'NO_FINDING')]:
        completed = subprocess.run([sys.executable, '-I', '-S', '-B', str(extracted/'scripts/check-ps.py'), '--json'],
                                   input=text.encode(), capture_output=True, timeout=15, cwd=extracted)
        assert completed.returncode == 0 and completed.stderr == b''
        row = json.loads(completed.stdout)
        assert row['state'] == state and row['redaction_performed'] is False
        assert row['independently_validated'] is False and row['text_included'] is False
        assert text.encode() not in completed.stdout
        assert row['models'][0]['sha256'] == hashlib.sha256((extracted/'services/evaluator/app.py').read_bytes()).hexdigest()


def test_actual_cli_refuses_missing_real_policy_without_private_echo(source, tmp_path):
    root, _, _ = source
    for name in ['tools/ps_source_distribution.py', 'scripts/export-ps-source.py']:
        target = root/name;target.parent.mkdir(parents=True, exist_ok=True);shutil.copyfile(ROOT/name, target)
    output = tmp_path.resolve()/'PRIVATE-CANARY.zip'
    completed = subprocess.run([sys.executable, '-B', str(root/'scripts/export-ps-source.py'), 'build', '--output', str(output)],
                               capture_output=True, timeout=10)
    assert completed.returncode == 2 and completed.stdout == b''
    assert b'PRIVATE-CANARY' not in completed.stderr and b'Traceback' not in completed.stderr
    assert not output.exists()


def test_supplied_zip_verification_never_allocates_an_untrusted_directory(tmp_path, monkeypatch):
    # The real current source profile supplies all canonical files; no fake input policy.
    raw=distribution.build()
    original=distribution.zipfile.ZipFile
    calls=[]
    def only_trusted_writes(file, mode='r', *args, **kwargs):
        calls.append(mode)
        assert mode=='w', 'Supplied ZIP bytes were sent to the parser'
        return original(file,mode,*args,**kwargs)
    monkeypatch.setattr(distribution.zipfile,'ZipFile',only_trusted_writes)
    assert distribution.verify(raw)['profile']=='ai-trust-id-ps-source/v1'
    for malformed in (b'PK\x05\x06'+b'\xff'*200, b'PK\x01\x02'*100000, raw+b'private trailing bytes'):
        with pytest.raises(ValueError):distribution.verify(malformed)
    assert calls and set(calls)=={'w'}
