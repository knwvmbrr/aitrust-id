"""Exercise exact native-engine resource packaging, without installing a phone app."""
import importlib.util
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
        assert any(name.startswith('Notices/') for name in package.namelist())
        assert all(name == 'LICENSE' or name.startswith(('Assets/', 'Notices/')) for name in package.namelist())
    again = subprocess.run([sys.executable, str(ROOT / 'scripts/prepare-native-bundle.py'), '--output', str(destination)], capture_output=True, timeout=30)
    assert again.returncode == 2
    assert archive.read_bytes() == before


def test_package_is_deterministic_for_identical_selected_sources(prepared_assets):
    assert builder.assets() == builder.assets()


@pytest.fixture
def source_copy(tmp_path, monkeypatch):
    root = tmp_path / 'checkout'; root.mkdir()
    # Refusal controls must run before any website/npm build in a clean clone.
    # Derive their valid starting identity from tracked sources, not an ignored
    # generated device manifest that happens to exist on the developer's Mac.
    for name in ['protocol/unicode15-data.json', 'services/evaluator/app.py']:
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
