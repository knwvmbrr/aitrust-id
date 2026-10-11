"""Notice identity and truthful incomplete-coverage controls."""
import copy
import hashlib
import io
import json
from pathlib import Path
import shutil
import tarfile
import pytest
from scripts import license_notices as n
ROOT = Path(__file__).resolve().parents[1]

@pytest.fixture
def workspace(tmp_path):
    manifest = json.loads((ROOT / n.MANIFEST).read_text())
    paths = [n.MANIFEST, '.gitattributes', 'scripts/license_notices.py', 'scripts/verify-redistribution-notices.py',
             'scripts/collect-runtime-notices.py', 'protocol/evidence.py', 'protocol/corpus.py',
             *manifest['sources'], *['sbom/notices/'+h+'.txt' for h in manifest['notices']]]
    for relative in paths:
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, target)
    return tmp_path


def change(root, mutation):
    target = root / n.MANIFEST
    value = json.loads(target.read_text())
    mutation(value)
    target.write_text(json.dumps(value))


def test_real_notice_identity_is_not_license_clearance():
    value = n.verify()
    assert value['evidence_integrity_pass'] is True
    assert value['license_release_pass'] is False
    assert value['runtime_images'] == 3 and value['npm_artifacts'] == 205
    assert value['runtime_notice_occurrences'] == 449 and value['npm_notice_occurrences'] == 149
    assert value['unique_notice_blobs'] == 224
    assert value['source_unchanged_during_execution'] is True
    assert value['npm_packages_without_matched_notice_file']
    assert value['npm_archives_rechecked'] is False


@pytest.mark.parametrize('mutation', [
    lambda v: v.update(license_cleared=True),
    lambda v: v.update(independent_accuracy_evidence=True),
    lambda v: v.update(schema_version=True),
    lambda v: v.update(kind='cleared'),
    lambda v: v.update(captured_at='2999-01-01T00:00:00+00:00'),
    lambda v: v.update(captured_at='2026-10-01T00:00:00'),
    lambda v: v.update(runtime_observed_at='2999-01-01T00:00:00+00:00'),
    lambda v: v.update(npm_observed_at='2026-10-01T00:00:00'),
    lambda v: v.update(captured_at='2020-01-01T00:00:00+00:00'),
    lambda v: v.update(collected_by='independent certifier'),
    lambda v: v.update(unexpected='field'),
    lambda v: v['coverage'].update(source_offer_obligations=True),
    lambda v: v['coverage'].pop('all_declared_architectures'),
    lambda v: v['sources'].pop('site/package-lock.json'),
    lambda v: v['sources'].update({'../secret':'0'*64}),
    lambda v: v['runtime'].pop(),
    lambda v: v['runtime'].append(copy.deepcopy(v['runtime'][0])),
    lambda v: v['runtime'][0].update(image_id='0'*64),
    lambda v: v['runtime'][0]['notices'][0].update(source_path='/root/secret'),
    lambda v: v['runtime'][0]['notices'][0].update(notice='../../secret'),
    lambda v: v['runtime'][0]['notices'][0].update(bytes=True),
    lambda v: v['runtime'][0]['notices'].append(copy.deepcopy(v['runtime'][0]['notices'][0])),
    lambda v: v['runtime'][0]['python_distributions'].append(copy.deepcopy(v['runtime'][0]['python_distributions'][0])),
    lambda v: v['runtime'][0]['python_distributions'][0].update(license=123),
    lambda v: v['notices'].update({'0'*64: True}),
    lambda v: v['notices'].update({'bad': 42}),
    lambda v: v['npm'].pop(),
    lambda v: v['npm'].__setitem__(1,copy.deepcopy(v['npm'][0])),
    lambda v: v['npm'][0].update(version='0.0.0'),
    lambda v: v['npm'][0].update(license_declared='Proprietary'),
    lambda v: v['npm'][0].update(optional='false'),
    lambda v: v['npm'][0].update(package_path='node_modules/fake'),
    lambda v: v['npm'][0].update(resolved='http://registry.npmjs.org/fake'),
    lambda v: v['npm'][0].update(integrity='sha512-not_base64'),
    lambda v: v['npm'][0]['notices'][0].update(source_path='package/../../secret'),
])
def test_mutated_observation_is_refused(workspace, mutation):
    change(workspace, mutation)
    with pytest.raises((ValueError, KeyError, TypeError)):
        n.verify(workspace)


def test_changed_notice_is_refused(workspace):
    value=json.loads((workspace/n.MANIFEST).read_text())
    relative=value['runtime'][0]['notices'][0]['notice']
    (workspace/relative).write_text('Changed license')
    with pytest.raises(ValueError): n.verify(workspace)


@pytest.mark.parametrize('relative', ['site/package-lock.json', 'scripts/collect-runtime-notices.py'])
def test_dependency_or_collector_drift_is_refused(workspace,relative):
    path=workspace/relative
    path.write_bytes(path.read_bytes()+b'\n')
    with pytest.raises(ValueError): n.verify(workspace)


def test_unregistered_store_file_is_refused(workspace):
    (workspace/'sbom/notices/hidden.txt').write_text('Unregistered license')
    with pytest.raises(ValueError):n.verify(workspace)


def test_notice_symlink_is_refused(workspace,tmp_path):
    value=json.loads((workspace/n.MANIFEST).read_text());path=workspace/value['runtime'][0]['notices'][0]['notice']
    original=path.read_bytes();path.unlink();other=tmp_path/'other.txt';other.write_bytes(original);path.symlink_to(other)
    with pytest.raises(ValueError):n.verify(workspace)


def test_duplicate_manifest_key_is_refused(workspace):
    path=workspace/n.MANIFEST
    path.write_text(path.read_text().replace('{', '{"license_cleared": false,', 1))
    with pytest.raises(ValueError):n.verify(workspace)


def test_archive_digest_is_checked_before_tar_parser(tmp_path,monkeypatch):
    path=tmp_path/'fake.tgz';path.write_bytes(b'not an archive')
    row={'integrity':'sha256-'+'A'*43+'=','artifact_sha256':'0'*64}
    monkeypatch.setattr(n.tarfile,'open',lambda *a,**kw:pytest.fail('Unverified archive was parsed'))
    with pytest.raises(ValueError):n.archive_notices(path,row)


def test_archive_notices_are_parsed_from_verified_memory(tmp_path,monkeypatch):
    import base64
    buffer=io.BytesIO()
    with tarfile.open(fileobj=buffer,mode='w:gz') as tar:
        data=b'Licensed sample';info=tarfile.TarInfo('package/LICENSE');info.size=len(data);tar.addfile(info,io.BytesIO(data))
    raw=buffer.getvalue();path=tmp_path/'notice.tgz';path.write_bytes(raw)
    row={'integrity':'sha256-'+base64.b64encode(hashlib.sha256(raw).digest()).decode(),
         'artifact_sha256':hashlib.sha256(raw).hexdigest(),'package_path':'node_modules/sample',
         'notices':[{'source_path':'package/LICENSE','sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)}]}
    original=n.tarfile.open
    def only_verified_bytes(*a,**kw):
        assert not a and isinstance(kw['fileobj'],io.BytesIO)
        path.write_bytes(b'replaced after read')
        return original(*a,**kw)
    monkeypatch.setattr(n.tarfile,'open',only_verified_bytes)
    n.archive_notices(path,row)


def test_collector_change_during_verification_is_refused(workspace,monkeypatch):
    original=n.refs
    def alter_after_check(*args,**kwargs):
        result=original(*args,**kwargs)
        path=workspace/'scripts/collect-runtime-notices.py'
        if not path.read_bytes().endswith(b'# changed\n'):
            path.write_bytes(path.read_bytes()+b'# changed\n')
        return result
    monkeypatch.setattr(n,'refs',alter_after_check)
    with pytest.raises(ValueError):n.verify(workspace)


@pytest.mark.parametrize('strict,code', [(False,0),(True,1)])
def test_cli_distinguishes_integrity_from_clearance(strict,code):
    import subprocess,sys
    args=[sys.executable,str(ROOT/'scripts/verify-redistribution-notices.py')]
    if strict:args.append('--require-clearance')
    run=subprocess.run(args,capture_output=True,text=True,timeout=20)
    assert run.returncode==code and not run.stderr
    output=json.loads(run.stdout)
    assert output['evidence_integrity_pass'] is True
    assert output['license_release_pass'] is False


def test_notice_store_disables_line_ending_conversion():
    attributes=(ROOT/'.gitattributes').read_text().splitlines()
    assert 'sbom/notices/*.txt -text -whitespace' in attributes


@pytest.mark.parametrize('conversion', ['true','input'])
def test_git_checkout_preserves_all_evidence_bytes(tmp_path,conversion):
    import subprocess
    source=tmp_path/'source';source.mkdir()
    data={'.gitattributes':(ROOT/'.gitattributes').read_bytes(),
          'source.py':b'# Fixture source\n', 'package-lock.json':b'{}\n',
          'runtime.wasm':b'\x00asm\x01\x00\x00\x00',
          'sbom/notices/sample.txt':b'Original upstream notice\r\n'}
    for name,raw in data.items():
        target=source/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
    def git(*args):
        result=subprocess.run(['git','-c','commit.gpgsign=false','-c','core.hooksPath=/dev/null',
                               '-c','user.name=Fixture','-c','user.email=fixture@example.invalid',*args],
                              cwd=source,capture_output=True,timeout=20)
        assert result.returncode==0,result.stderr.decode()
    git('init','--quiet');git('add','--',*data);git('commit','--quiet','-m','Synthetic byte preservation fixture')
    target=tmp_path/'clone'
    git('-c','core.autocrlf='+conversion,'clone','--quiet','--no-local','--no-hardlinks',str(source),str(target))
    assert all((target/name).read_bytes()==raw for name,raw in data.items())
