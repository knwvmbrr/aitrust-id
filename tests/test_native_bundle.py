"""Exercise exact native-engine resource packaging, without installing a phone app."""
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile
import hashlib
import runpy
import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('ios_builder', ROOT / 'scripts/native_bundle.py')
builder = importlib.util.module_from_spec(spec); spec.loader.exec_module(builder)


@pytest.fixture
def prepared_assets():
    if not (ROOT / 'site/node_modules/pyodide/package.json').is_file() or not (ROOT / 'site/public/device/runtime-314.0.7/pyodide.mjs').is_file():
        pytest.skip('Requires the separately built public device assets; required site CI exercises this path after its build.')


def test_actual_package_can_be_inspected_without_credentials(tmp_path, prepared_assets):
    tmp_path.chmod(0o700); destination = tmp_path / 'package'
    result = subprocess.run([sys.executable, str(ROOT / 'scripts/prepare-native-bundle.py'), '--output', str(destination)], capture_output=True, timeout=30)
    assert result.returncode == 0
    summary = json.loads(result.stdout); assert not summary['credentials_generated'] and not summary['phone_signing_configured']
    assert str(tmp_path).encode() not in result.stdout + result.stderr
    assert summary['installable_app'] is False
    archive = destination / 'AI-Trust-ID-native-assets.zip'
    before = archive.read_bytes()
    assert archive.stat().st_mode & 0o077 == 0
    with zipfile.ZipFile(archive) as package:
        config = json.loads(package.read('Assets/native-assets.json'))
        for name, expected in config['hashes'].items():
            assert hashlib.sha256(package.read('Assets' + name)).hexdigest() == expected
        assert len(config['hashes']) == 9
        assert 'LICENSE' in package.namelist()
        assert {n for n in package.namelist() if n.startswith('Notices/')} == {'Notices/pyodide-MPL-2.0.txt', 'Notices/python-license.txt', 'Notices/source.txt', 'Notices/unicode-license.txt'}
        assert package.read('Notices/unicode-license.txt') == (ROOT / 'eval/vectors/unicode/LICENSE.txt').read_bytes()
        assert all(name == 'LICENSE' or name.startswith(('Assets/', 'Notices/')) for name in package.namelist())
    again = subprocess.run([sys.executable, str(ROOT / 'scripts/prepare-native-bundle.py'), '--output', str(destination)], capture_output=True, timeout=30)
    assert again.returncode == 2
    assert archive.read_bytes() == before


def test_package_is_deterministic_for_identical_selected_sources(prepared_assets):
    assert builder.assets() == builder.assets()


def test_module_archive_keeps_exact_source_identity(prepared_assets):
    payload=builder.assets()
    assert not any(name.endswith(('.py', '.py.txt')) for name in payload)
    raw=payload['Assets/detector-source.zip']
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        assert archive.namelist()==['method.py']
        source=archive.read('method.py')
    manifest=json.loads(payload['Assets/device-manifest.json'])
    config=json.loads(payload['Assets/native-assets.json'])
    assert config['format']=='ai-trust-id-native-assets/v2'
    assert source==(ROOT/'site/public'/manifest['path'].lstrip('/')).read_bytes()
    assert hashlib.sha256(source).hexdigest()==manifest['bundle_sha256']==config['bundle_sha256']
    assert hashlib.sha256(raw).hexdigest()==config['archive_sha256']==config['hashes']['/detector-source.zip']


def run_module_loader(monkeypatch, raw, expected):
    # Execute the actual fixed Python loader embedded in the native bridge.
    loader=(ROOT/'mobile/ios/Web/bridge.mjs').read_text().split('const moduleLoader=String.raw`',1)[1].split('`;',1)[0]
    original=zipfile.ZipFile
    def open_memory(name):
        assert name=='/tmp/aitrust-detector-source.zip'
        return original(io.BytesIO(raw))
    namespace={'_aitrust_expected_source':expected}
    with monkeypatch.context() as patch:
        patch.setattr(zipfile,'ZipFile',open_memory)
        exec(compile(loader,'fixed-native-module-loader','exec'),namespace)
    return namespace


def test_actual_module_loader_retains_unicode_and_cleans_source(monkeypatch):
    source='RESULT = "café 😀"\n'.encode()
    result=run_module_loader(monkeypatch,builder.method_archive(source),hashlib.sha256(source).hexdigest())
    assert result['RESULT']=='café 😀'
    assert '_aitrust_source' not in result
    assert '_aitrust_archive' not in result


def test_module_loader_refuses_changed_source_before_execution(monkeypatch):
    source=b'raise AssertionError("must never execute")\n'
    with pytest.raises(ValueError,match='identity'):
        run_module_loader(monkeypatch,builder.method_archive(source),'0'*64)


@pytest.mark.parametrize('defect',['extra','duplicate','path','directory','compressed','oversized','executable','encrypted','comment','extra-field','truncated','crc','invalid-utf8'])
def test_actual_module_loader_rejects_unreviewed_archive_shapes(monkeypatch,defect):
    source=b'RESULT = 7\n'
    if defect=='oversized':source=b'x' * 200_001
    if defect=='invalid-utf8':source=b'\xff'
    member=zipfile.ZipInfo('method.py',date_time=(1980,1,1,0,0,0))
    member.create_system=3;member.external_attr=0o100644 << 16
    if defect=='path':member.filename='../method.py'
    if defect=='directory':member.filename='method.py/'
    if defect=='compressed':member.compress_type=zipfile.ZIP_DEFLATED
    if defect=='executable':member.external_attr=0o100755 << 16
    if defect=='extra-field':member.extra=b'\x01\x00\x00\x00'
    output=io.BytesIO()
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter('ignore',UserWarning)
        with zipfile.ZipFile(output,'w') as archive:
            archive.writestr(member,source)
            if defect in ('extra','duplicate'):archive.writestr('method.py' if defect=='duplicate' else 'other.py',b'RESULT = 8\n')
            if defect=='comment':archive.comment=b'unreviewed'
    raw=output.getvalue()
    if defect=='truncated':raw=raw[:-30]
    if defect=='crc':raw=raw.replace(source,b'RESULT = 9\n',1)
    if defect=='encrypted':
        raw=bytearray(raw);raw[6:8]=(1).to_bytes(2,'little');at=raw.index(b'PK\x01\x02');raw[at+8:at+10]=(1).to_bytes(2,'little');raw=bytes(raw)
    with pytest.raises((ValueError,zipfile.BadZipFile,UnicodeDecodeError)):
        run_module_loader(monkeypatch,raw,hashlib.sha256(source).hexdigest())


@pytest.mark.parametrize('source',[b'',b'x'*200_001,'not bytes',b'\xff'])
def test_module_packager_refuses_invalid_source(source):
    with pytest.raises(ValueError):builder.method_archive(source)


@pytest.fixture
def source_copy(tmp_path, monkeypatch):
    root = tmp_path / 'checkout'; root.mkdir()
    # Refusal controls must run before any website/npm build in a clean clone.
    # Derive their valid starting identity from tracked sources, not an ignored
    # generated device manifest that happens to exist on the developer's Mac.
    for name in ['protocol/unicode15-data.json', 'services/evaluator/app.py', 'eval/vectors/unicode/LICENSE.txt', 'site/public/device-licenses/unicode-license.txt', 'site/public/device-licenses/pyodide-MPL-2.0.txt', 'site/public/device-licenses/python-license.txt', 'site/public/device-licenses/source.txt']:
        target = root / name; target.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(ROOT / name, target)
    inventory = json.loads((ROOT / 'sbom/assets/notices.json').read_text())
    bound = {'sbom/assets/notices.json', *inventory['sources']}
    for row in inventory['assets']:
        bound.add(row['path']); bound.update(notice['path'] for notice in row['notices'])
    for name in bound:
        target = root / name; target.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(ROOT / name, target)
    method, source_hash = runpy.run_path(str(ROOT / 'scripts/build-device-detector.py'))['project']((ROOT / 'services/evaluator/app.py').read_bytes())
    bundle_hash = hashlib.sha256(method).hexdigest()
    manifest = {'method_sha256': source_hash, 'bundle_sha256': bundle_hash,
                'path': '/device/method-' + bundle_hash + '.py', 'runtime': '314.0.7',
                'max_codepoints': 20000, 'normalization_id': 'NFC-Unicode-15.0.0/v1',
                'normalization_data_sha256': hashlib.sha256((ROOT / 'protocol/unicode15-data.json').read_bytes()).hexdigest()}
    manifest_path = root / 'site/src/device-manifest.json'; manifest_path.parent.mkdir(parents=True)
    manifest_path.write_text(json.dumps(manifest))
    monkeypatch.setattr(builder, 'ROOT', root)
    return root


@pytest.mark.parametrize('field,value', [('path', '/../../private'), ('runtime', 'unexpected'), ('max_codepoints', True), ('normalization_id', 'NFC-Unicode-unknown'), ('method_sha256', 'g' * 64), ('extra', 'unaccepted')])
def test_mutated_manifest_refused_before_copying_material(source_copy, field, value):
    path = source_copy / 'site/src/device-manifest.json'; data = json.loads(path.read_text()); data[field] = value; path.write_text(json.dumps(data))
    with pytest.raises(ValueError): builder.assets()


def test_changed_normalization_is_not_packaged_under_old_identity(source_copy):
    (source_copy / 'protocol/unicode15-data.json').write_text('{}')
    with pytest.raises(ValueError): builder.assets()


def test_existing_destination_symlink_is_never_followed(tmp_path, prepared_assets):
    tmp_path.chmod(0o700); actual = tmp_path / 'actual'; actual.mkdir(mode=0o700); sentinel = actual / 'keep'; sentinel.write_text('unchanged')
    link = tmp_path / 'package'; link.symlink_to(actual)
    result = subprocess.run([sys.executable, str(ROOT / 'scripts/prepare-native-bundle.py'), '--output', str(link)], capture_output=True, timeout=30)
    assert result.returncode == 2 and sentinel.read_text() == 'unchanged' and list(actual.iterdir()) == [sentinel]
    assert str(tmp_path).encode() not in result.stdout + result.stderr


@pytest.mark.parametrize('change', ['missing', 'different', 'extra', 'linked'])
def test_unreviewed_notice_is_never_packaged(source_copy, change):
    notice = source_copy / 'site/public/device-licenses/unicode-license.txt'
    if change == 'missing': notice.unlink()
    elif change == 'different': notice.write_text('replacement notice')
    elif change == 'extra': (notice.parent / 'unreviewed.txt').write_text('extra')
    else:
        notice.unlink(); notice.symlink_to(source_copy / 'eval/vectors/unicode/LICENSE.txt')
    with pytest.raises(ValueError): builder.assets()


@pytest.mark.parametrize('name', ['pyodide-MPL-2.0.txt', 'python-license.txt', 'source.txt'])
def test_direct_packager_refuses_altered_runtime_notice_bytes(source_copy, name):
    notice = source_copy / 'site/public/device-licenses' / name
    notice.write_bytes(notice.read_bytes() + b'changed runtime notice')
    with pytest.raises(ValueError): builder.assets()
