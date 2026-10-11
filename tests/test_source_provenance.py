"""Synthetic archive/policy tests; actual cryptographic checks have separate run evidence."""
import copy
import gzip
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tarfile

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import source_snapshot as source
import importlib.util
spec = importlib.util.spec_from_file_location('verify_source', ROOT / 'scripts/verify-source-provenance.py')
verifier = importlib.util.module_from_spec(spec)
spec.loader.exec_module(verifier)


@pytest.fixture
def repo(tmp_path):
    root = tmp_path / 'repo'
    root.mkdir()
    subprocess.run(['git', 'init', '-q', str(root)], check=True)
    (root / 'README.md').write_text('Synthetic public source.\n')
    (root / 'runner.sh').write_text('Not executed.\n')
    (root / 'runner.sh').chmod(0o755)
    commit(root)
    return root


def commit(root):
    subprocess.run(['git', '-C', str(root), 'add', '.'], check=True)
    subprocess.run(['git', '-C', str(root), '-c', 'user.name=Synthetic fixture',
                    '-c', 'user.email=fixture@example.invalid', 'commit', '-qm',
                    'Synthetic fixture'], check=True)
    return source.git(root, 'rev-parse', 'HEAD').decode().strip()


def snapshot(root):
    sha = source.git(root, 'rev-parse', 'HEAD').decode().strip()
    return source.build(root, sha), sha


def repack(raw, mutate):
    with tarfile.open(fileobj=io.BytesIO(raw), mode='r:gz') as archive:
        rows = [(copy.copy(member), archive.extractfile(member).read()) for member in archive]
    rows = mutate(rows)
    output = io.BytesIO()
    with gzip.GzipFile(fileobj=output, mode='wb', filename='', mtime=0) as compressed:
        with tarfile.open(fileobj=compressed, mode='w', format=tarfile.USTAR_FORMAT) as archive:
            for member, data in rows:
                member.size = len(data)
                archive.addfile(member, io.BytesIO(data))
    return output.getvalue()


def test_repeatable_source_and_working_input_excluded(repo):
    first, sha = snapshot(repo)
    (repo / 'README.md').write_text('Uncommitted private change.\n')
    (repo / '.env').write_text('SYNTHETIC_SECRET=not-a-real-secret\n')
    (repo / 'private.pem').write_text('Not a key.\n')
    second = source.build(repo, sha)
    assert first == second
    result = source.inspect(second, sha)
    assert result['source_files'] == 2
    assert result['tag_release_validated'] is False
    assert result['installed_dependencies_authenticated'] is False


def test_changed_commit_changes_bytes(repo):
    first, first_sha = snapshot(repo)
    (repo / 'README.md').write_text('Changed public source.\n')
    second_sha = commit(repo)
    second = source.build(repo, second_sha)
    assert first != second
    with pytest.raises(ValueError):
        source.inspect(first, second_sha)
    assert first_sha != second_sha


def test_local_replacement_ref_cannot_rewrite_named_source(repo):
    first, first_sha = snapshot(repo)
    (repo / 'README.md').write_text('Replacement object contents.\n')
    second_sha = commit(repo)
    subprocess.run(['git', '-C', str(repo), 'replace', first_sha, second_sha], check=True)
    assert source.build(repo, first_sha) == first


@pytest.mark.parametrize('name', ['.env', '.env.production', 'private.pem', '.git/config',
                                 'node_modules/package/a.js', '../escape', '/tmp/escape',
                                 'a//b', 'a/./b', 'a\\b', 'a:b', 'é.txt', source.META])
def test_unsafe_name_refused(name):
    with pytest.raises(ValueError):
        source.safe_name(name)


@pytest.mark.parametrize('name', ['.env', 'private.pem', source.META])
def test_private_committed_file_refused(repo, name):
    (repo / name).write_text('Synthetic forbidden input')
    sha = commit(repo)
    with pytest.raises(ValueError):
        source.build(repo, sha)


def test_committed_link_refused(repo):
    (repo / 'link').symlink_to('README.md')
    sha = commit(repo)
    with pytest.raises(ValueError):
        source.build(repo, sha)


def test_exact_reviewed_public_template_only(repo):
    (repo / 'deploy').mkdir()
    target = repo / source.PUBLIC_TEMPLATE
    target.write_bytes((ROOT / source.PUBLIC_TEMPLATE).read_bytes())
    sha = commit(repo)
    assert source.inspect(source.build(repo, sha), sha)['source_files'] == 3
    target.write_text('AITRUST_TOKEN=synthetic-private-value\n')
    sha = commit(repo)
    with pytest.raises(ValueError, match='template changed'):
        source.build(repo, sha)


@pytest.mark.parametrize('sha', ['HEAD', '-x', 'a'*39, 'A'*40, 'a'*40+'\n'])
def test_only_exact_commit_accepted(repo, sha):
    with pytest.raises(ValueError):
        source.build(repo, sha)


@pytest.mark.parametrize('field,value', [('name', 'aitrust-id/../escape'),
                                       ('name', 'different/README.md'),
                                       ('mode', 0o777), ('uid', 12), ('mtime', 100),
                                       ('type', tarfile.SYMTYPE)])
def test_hostile_archive_members_refused(repo, field, value):
    raw, sha = snapshot(repo)
    def change(rows):
        setattr(rows[1][0], field, value)
        return rows
    with pytest.raises((ValueError, tarfile.TarError)):
        source.inspect(repack(raw, change), sha)


def test_duplicate_archive_member_refused(repo):
    raw, sha = snapshot(repo)
    with pytest.raises(ValueError):
        source.inspect(repack(raw, lambda rows: rows + [rows[-1]]), sha)


def test_changed_bytes_and_duplicate_metadata_refused(repo):
    raw, sha = snapshot(repo)
    def change(rows):
        rows[1] = (rows[1][0], b'Altered source')
        return rows
    with pytest.raises(ValueError):
        source.inspect(repack(raw, change), sha)
    def duplicate(rows):
        text = rows[0][1].decode()
        rows[0] = (rows[0][0], ('{"profile":"wrong",' + text[1:]).encode())
        return rows
    with pytest.raises(ValueError):
        source.inspect(repack(raw, duplicate), sha)


def test_small_configured_limits_refuse_build_and_decompression(repo, monkeypatch):
    raw, sha = snapshot(repo)
    monkeypatch.setattr(source, 'MAX_TOTAL', 5)
    monkeypatch.setattr(source, 'MAX_FILES', 1)
    with pytest.raises(ValueError):
        source.build(repo, sha)
    with pytest.raises(ValueError):
        source.inspect(raw, sha)


@pytest.fixture
def inputs(repo, tmp_path):
    raw, sha = snapshot(repo)
    artifact = tmp_path / 'source.tar.gz'
    artifact.write_bytes(raw)
    bundle = tmp_path / 'bundle.json'
    bundle.write_text('Synthetic policy test only; not a signature')
    root = tmp_path / 'root.json'
    root.write_text('Synthetic policy test only; not a trust anchor')
    return artifact, bundle, root, sha


def policy_reply(artifact):
    return [{'verificationResult': {'verifiedTimestamps': [{'synthetic': True}],
             'statement': {'predicateType': verifier.PREDICATE,
                           'subject': [{'digest': {'sha256': hashlib.sha256(artifact.read_bytes()).hexdigest()}}]}}}]


def test_policy_pins_cryptographic_identity_and_source(inputs):
    artifact, bundle, root, sha = inputs
    def runner(argv, **kwargs):
        assert argv[argv.index('--repo')+1] == 'knwvmbrr/aitrust-id'
        assert argv[argv.index('--source-digest')+1] == sha
        assert argv[argv.index('--source-ref')+1] == 'refs/heads/main'
        assert argv[argv.index('--cert-identity')+1] == verifier.IDENTITY
        # gh's identity selectors are mutually exclusive. Exact SAN pins the workflow/ref.
        assert '--signer-workflow' not in argv and '--signer-repo' not in argv
        assert '--cert-identity-regex' not in argv
        assert '--deny-self-hosted-runners' in argv
        assert '--bundle' in argv and '--custom-trusted-root' in argv
        assert kwargs['timeout'] == 120 and kwargs['capture_output'] is True
        return subprocess.CompletedProcess(argv, 0, json.dumps(policy_reply(artifact)).encode(), b'')
    result = verifier.verify(*inputs, runner=runner)
    assert result['pass'] and not result['license_cleared']
    assert not result['independent_tag_accuracy_evidence']


@pytest.mark.parametrize('kind', ['failure', 'empty', 'no-witness', 'digest', 'predicate'])
def test_verifier_result_refusals(inputs, kind):
    def runner(argv, **kwargs):
        reply = policy_reply(inputs[0])
        if kind == 'empty': reply = []
        if kind == 'no-witness': reply[0]['verificationResult']['verifiedTimestamps'] = []
        if kind == 'digest': reply[0]['verificationResult']['statement']['subject'][0]['digest']['sha256'] = '0'*64
        if kind == 'predicate': reply[0]['verificationResult']['statement']['predicateType'] = 'wrong'
        return subprocess.CompletedProcess(argv, int(kind == 'failure'), json.dumps(reply).encode(), b'')
    with pytest.raises(ValueError):
        verifier.verify(*inputs, runner=runner)


@pytest.mark.parametrize('index', [0, 1, 2])
def test_missing_or_linked_inputs_refused_before_invoking_gh(inputs, index, tmp_path):
    values = list(inputs)
    path = values[index]
    moved = tmp_path / ('moved-'+str(index))
    path.rename(moved)
    def forbidden(*args, **kwargs):
        pytest.fail('Verifier invoked without trust inputs')
    with pytest.raises(ValueError):
        verifier.verify(*values, runner=forbidden)
    path.symlink_to(moved)
    with pytest.raises(ValueError):
        verifier.verify(*values, runner=forbidden)


def test_main_only_signing_after_all_required_contexts():
    workflow = yaml.safe_load((ROOT / '.github/workflows/ci.yml').read_text())
    assert workflow['permissions'] == {'contents': 'read'}
    job = workflow['jobs']['source-provenance']
    assert job['if'] == "github.event_name == 'push' && github.ref == 'refs/heads/main' && github.repository == 'knwvmbrr/aitrust-id'"
    assert set(job['needs']) == {'change-records','host-config','scope-plan','spec','no-egress',
                                'regressions','accessibility','device-builder','site'}
    assert job['permissions'] == {'contents':'read','id-token':'write','attestations':'write'}
    uses = [step['uses'] for step in job['steps'] if 'uses' in step]
    assert uses == ['actions/checkout@11d5960a326750d5838078e36cf38b85af677262',
                    'actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065',
                    'actions/attest@1e69f48acb82d1966a394da916b4c1698aa569d6',
                    'actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02']
    assert job['steps'][0]['with']['persist-credentials'] is False
    attest = next(step for step in job['steps'] if step.get('id') == 'provenance')
    assert attest['with'] == {'subject-path':'output/provenance/aitrust-id-source.tar.gz'}
    assert workflow['jobs']['gates']  # No independent release gate deleted or signed away.


@pytest.mark.parametrize('index', [0, 1, 2])
def test_original_paths_are_not_reopened_by_tool(inputs, index):
    original = [p.read_bytes() for p in inputs[:3]]
    stages = []
    def runner(argv, **kwargs):
        paths = [Path(argv[3]), Path(argv[argv.index('--bundle')+1]),
                 Path(argv[argv.index('--custom-trusted-root')+1])]
        stages.extend(paths)
        inputs[index].write_bytes(b'changed after capture')
        assert all(path != inputs[i] for i,path in enumerate(paths))
        assert [p.read_bytes() for p in paths] == original
        assert all(p.stat().st_mode & 0o777 == 0o400 for p in paths)
        assert paths[0].parent.stat().st_mode & 0o777 == 0o700
        return subprocess.CompletedProcess(argv, 0, json.dumps(policy_reply(paths[0])).encode(), b'')
    result = verifier.verify(*inputs, runner=runner)
    assert result['pass'] and result['captured_inputs_verified']
    assert result['bundle_sha256'] == hashlib.sha256(original[1]).hexdigest()
    assert result['trusted_root_sha256'] == hashlib.sha256(original[2]).hexdigest()
    assert all(not p.exists() for p in stages)


@pytest.mark.parametrize('index', [0, 1, 2])
@pytest.mark.parametrize('change', ['bytes', 'link', 'remove', 'directory', 'hardlink'])
def test_staged_input_changes_refuse_and_cleanup(inputs, index, change):
    import os
    stages = []
    def runner(argv, **kwargs):
        paths = [Path(argv[3]), Path(argv[argv.index('--bundle')+1]),
                 Path(argv[argv.index('--custom-trusted-root')+1])]
        stages.extend(paths)
        reply = policy_reply(paths[0])
        path = paths[index]
        if change == 'bytes':
            path.chmod(0o600); path.write_bytes(b'changed bytes')
        else:
            path.unlink()
            if change == 'link': path.symlink_to(inputs[index])
            if change == 'directory': path.mkdir()
            if change == 'hardlink': os.link(inputs[index], path)
        return subprocess.CompletedProcess(argv, 0, json.dumps(reply).encode(), b'')
    with pytest.raises(ValueError): verifier.verify(*inputs, runner=runner)
    assert all(not p.exists() for p in stages)
    assert all(p.is_file() for p in inputs[:3])


@pytest.mark.parametrize('failure', ['timeout', 'oserror', 'returncode', 'empty', 'text', 'invalid-json', 'duplicate'])
def test_tool_failure_cleans_owned_inputs(inputs, failure):
    stages=[]
    def runner(argv, **kwargs):
        stages.append(Path(argv[3]).parent)
        if failure == 'timeout': raise subprocess.TimeoutExpired(argv, 120)
        if failure == 'oserror': raise OSError('synthetic tool unavailable')
        out = json.dumps(policy_reply(Path(argv[3]))).encode()
        if failure == 'empty': out = b''
        if failure == 'text': out = 'not binary stdout'
        if failure == 'invalid-json': out = b'not JSON'
        if failure == 'duplicate': out = b'[{' + b'"verificationResult":{},"verificationResult":{}' + b'}]'
        return subprocess.CompletedProcess(argv, int(failure == 'returncode'), out, b'')
    with pytest.raises((ValueError, OSError, subprocess.SubprocessError)):
        verifier.verify(*inputs, runner=runner)
    assert all(not p.exists() for p in stages)


@pytest.mark.parametrize('kind', ['fifo', 'directory', 'empty', 'oversize', 'hardlink', 'parent-link'])
def test_descriptor_read_refuses_unsafe_shape(tmp_path, kind):
    import os
    path = tmp_path / 'input'
    if kind == 'fifo': os.mkfifo(path)
    elif kind == 'directory': path.mkdir()
    else:
        path.write_bytes(b'' if kind == 'empty' else b'abc')
        if kind == 'hardlink': os.link(path, tmp_path / 'other')
        if kind == 'parent-link':
            parent=tmp_path/'alias';parent.symlink_to(tmp_path,target_is_directory=True);path=parent/'input'
    with pytest.raises(ValueError): source.read_file(path, 2 if kind=='oversize' else 3)


def test_exact_read_limit_and_midread_mutation(tmp_path, monkeypatch):
    import os
    path=tmp_path/'input';path.write_bytes(b'abc')
    assert source.read_file(path,3)==b'abc'
    original=os.read;changed=False
    def read(fd,size):
        nonlocal changed
        result=original(fd,size)
        if not changed:
            changed=True;path.write_bytes(b'xyz')
        return result
    monkeypatch.setattr(source.os,'read',read)
    with pytest.raises(ValueError,match='changed'):source.read_file(path,3)
