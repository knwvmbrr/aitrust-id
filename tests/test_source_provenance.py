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
