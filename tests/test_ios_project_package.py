"""Exercise actual native-package privacy, freshness and reproducibility failures."""
import importlib.util
import json
import os
from pathlib import Path
import plistlib
import shutil
import subprocess
import sys
import zipfile
import hashlib
import runpy
import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('ios_builder', ROOT / 'scripts/build-ios-project.py')
builder = importlib.util.module_from_spec(spec); spec.loader.exec_module(builder)


@pytest.fixture
def prepared_assets():
    if not (ROOT / 'site/node_modules/pyodide/package.json').is_file() or not (ROOT / 'site/public/device/runtime-314.0.7/pyodide.mjs').is_file():
        pytest.skip('Requires the separately built public device assets; required site CI exercises this path after its build.')


def test_actual_package_can_be_inspected_without_credentials(tmp_path, prepared_assets):
    tmp_path.chmod(0o700); destination = tmp_path / 'package'
    result = subprocess.run([sys.executable, str(ROOT / 'scripts/build-ios-project.py'), '--output', str(destination)], capture_output=True, timeout=30)
    assert result.returncode == 0
    summary = json.loads(result.stdout); assert not summary['credentials_generated'] and not summary['phone_signing_configured']
    assert str(tmp_path).encode() not in result.stdout + result.stderr
    archive = destination / 'AI-Trust-ID-iOS.zip'
    assert destination.stat().st_mode & 0o077 == 0 and archive.stat().st_mode & 0o077 == 0
    with zipfile.ZipFile(archive) as package:
        names = package.namelist()
        assert all(not Path(name).is_absolute() and '..' not in Path(name).parts for name in names)
        config = json.loads(package.read('Assets/native-assets.json'))
        for name, expected in config['hashes'].items():
            assert hashlib.sha256(package.read('Assets' + name)).hexdigest() == expected
        share = plistlib.loads(package.read('Share-Info.plist'))
        assert share['NSExtension']['NSExtensionPointIdentifier'] == 'com.apple.share-services'
        assert 'NSAppTransportSecurity' not in share
        assert not any(name.endswith('.entitlements') or name.endswith('.mobileprovision') or name.endswith('.p12') for name in names)
        assert 'LICENSE' in names and any(name.startswith('Notices/') for name in names)
        assert plistlib.loads(package.read('PrivacyInfo.xcprivacy')) == {'NSPrivacyTracking': False}
    before = archive.read_bytes()
    again = subprocess.run([sys.executable, str(ROOT / 'scripts/build-ios-project.py'), '--output', str(destination)], capture_output=True, timeout=30)
    assert again.returncode == 2 and archive.read_bytes() == before


def test_package_is_deterministic_for_identical_selected_sources(prepared_assets):
    assert builder.files() == builder.files()


@pytest.mark.parametrize('profile,bundle,version', [('developer', 'com.aitrustid.personal.preview', '0.1'),
                                                  ('distribution', 'com.aitrustid.app', '1.0')])
def test_profiles_package_their_own_identifiers_without_signing(profile, bundle, version, prepared_assets):
    payload = builder.files(profile)
    project = plistlib.loads(payload['AITrustID.xcodeproj/project.pbxproj'])
    settings = [r['buildSettings'] for r in project['objects'].values() if r['isa'] == 'XCBuildConfiguration' and 'PRODUCT_BUNDLE_IDENTIFIER' in r['buildSettings']]
    assert {r['PRODUCT_BUNDLE_IDENTIFIER'] for r in settings} == {bundle, bundle + '.share', bundle + '.uiTests'}
    assert all(r['CODE_SIGNING_ALLOWED'] == 'NO' and 'DEVELOPMENT_TEAM' not in r for r in settings)
    assert all(plistlib.loads(payload[t + '-Info.plist'])['CFBundleShortVersionString'] == version for t in ['App', 'Share'])
    assert payload['AppLicense.txt'] == (ROOT / 'LICENSE').read_bytes()
    assert payload['Privacy.txt'] == (ROOT / 'mobile/ios/Privacy.txt').read_bytes()
    assert payload['PrivacyInfo.xcprivacy'] == (ROOT / 'mobile/ios/PrivacyInfo.xcprivacy').read_bytes()
    assert 'does not redact personal information' in payload['Privacy.txt'].decode()
    assert payload['Artwork.xcassets/AppIcon.appiconset/AppIcon.png'] == (ROOT / 'mobile/ios/Artwork/AppIcon.png').read_bytes()
    assert not any(name.endswith(('.p12', '.mobileprovision', '.entitlements')) for name in payload)


@pytest.mark.parametrize('profile', ['', 'production', '../../private', None, True])
def test_unknown_profile_refused_before_packaging(monkeypatch, profile):
    monkeypatch.setattr(builder, 'ROOT', Path('/nonexistent-fixture-must-not-be-read'))
    with pytest.raises(ValueError, match='Unknown native project profile'):
        builder.files(profile)


@pytest.fixture
def source_copy(tmp_path, monkeypatch):
    root = tmp_path / 'checkout'; root.mkdir()
    manifest = root / 'mobile/ios/PrivacyInfo.xcprivacy'
    manifest.parent.mkdir(parents=True)
    shutil.copyfile(ROOT / 'mobile/ios/PrivacyInfo.xcprivacy', manifest)
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
    with pytest.raises(ValueError): builder.files()


def test_changed_normalization_is_not_packaged_under_old_identity(source_copy):
    (source_copy / 'protocol/unicode15-data.json').write_text('{}')
    with pytest.raises(ValueError): builder.files()


def test_existing_destination_symlink_is_never_followed(tmp_path, prepared_assets):
    tmp_path.chmod(0o700); actual = tmp_path / 'actual'; actual.mkdir(mode=0o700); sentinel = actual / 'keep'; sentinel.write_text('unchanged')
    link = tmp_path / 'package'; link.symlink_to(actual)
    result = subprocess.run([sys.executable, str(ROOT / 'scripts/build-ios-project.py'), '--output', str(link)], capture_output=True, timeout=30)
    assert result.returncode == 2 and sentinel.read_text() == 'unchanged' and list(actual.iterdir()) == [sentinel]
    assert str(tmp_path).encode() not in result.stdout + result.stderr


def test_privacy_manifest_is_a_resource_of_both_targets():
    objects = builder.project()['objects']
    for target in ['App', 'Share']:
        phases = objects[builder.uid('target-' + target)]['buildPhases']
        resources = [objects[p] for p in phases if objects[p]['isa'] == 'PBXResourcesBuildPhase']
        names = [objects[objects[b]['fileRef']]['path'] for phase in resources for b in phase['files']]
        assert names.count('PrivacyInfo.xcprivacy') == 1
        assert names.count('Privacy.txt') == 1


@pytest.mark.parametrize('mutation', ['tracking', 'empty_apis', 'unknown', 'duplicate', 'invalid',
                                     'missing', 'file_link', 'parent_link'])
def test_unreviewed_privacy_declarations_refused_before_packaging(source_copy, mutation):
    path = source_copy / 'mobile/ios/PrivacyInfo.xcprivacy'
    if mutation in {'tracking', 'empty_apis', 'unknown'}:
        data = {'NSPrivacyTracking': False}
        if mutation == 'tracking': data['NSPrivacyTracking'] = True
        elif mutation == 'empty_apis': data['NSPrivacyAccessedAPITypes'] = []
        else: data['unreviewed'] = False
        path.write_bytes(plistlib.dumps(data))
    elif mutation == 'duplicate':
        path.write_bytes(path.read_bytes().replace(b'</dict>', b'<key>NSPrivacyTracking</key><true/></dict>'))
    elif mutation == 'invalid': path.write_bytes(b'not a plist')
    elif mutation == 'missing': path.unlink()
    elif mutation == 'file_link':
        actual = source_copy / 'elsewhere.xcprivacy'; path.rename(actual); path.symlink_to(actual)
    elif mutation == 'parent_link':
        actual = source_copy / 'elsewhere'; path.parent.rename(actual); path.parent.symlink_to(actual)
    with pytest.raises(ValueError, match='Native privacy manifest'):
        builder.files()
