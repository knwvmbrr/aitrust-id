"""Selected notice consistency must never promote legal permission or stale resources."""
import hashlib
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import base64
import pytest
from scripts import asset_notices as assets

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def checkout(tmp_path):
    root = tmp_path / 'checkout'; root.mkdir()
    value = json.loads((ROOT / assets.MANIFEST).read_text())
    names = {assets.MANIFEST, assets.UNICODE, assets.UNICODE_COPY, *value['sources']}
    for row in value['assets']:
        names.add(row['path']); names.update(n['path'] for n in row['notices'])
    for name in names:
        target = root / name; target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, target)
    return root


def mutate(root, callback):
    path = root / assets.MANIFEST; value = json.loads(path.read_text()); callback(value)
    path.write_text(json.dumps(value))


def test_source_only_clean_checkout_has_no_runtime_or_model_execution_claim(checkout):
    result = assets.verify(checkout)
    assert result['asset_bindings'] == 16 and result['font_files'] == 5
    assert result['bundled_unicode_notice_matched']
    assert result['prepared_runtime_files_matched'] == 0
    assert not result['runtime_origin_archive_reprocessed']
    assert not result['permission_cleared'] and not result['license_release_pass']
    assert not result['optional_model_weights_observed_by_this_check']
    assert not result['full_dependency_coverage'] and not result['independent_accuracy_evidence']


@pytest.mark.parametrize('field,value', [('permission_cleared', True), ('full_dependency_coverage', True),
    ('reviewed_by', 'unreviewed'), ('profile', 'other'), ('captured_at', '2099-01-01T00:00:00+00:00'),
    ('captured_at', '2026-10-11'), ('extra', True), ('assets', []), ('runtime_members', []),
    ('optional_model_references', []), ('runtime_origin', {})])
def test_metadata_cannot_grant_permission_or_hide_coverage(checkout, field, value):
    mutate(checkout, lambda record: record.update({field: value}))
    with pytest.raises((ValueError, KeyError, TypeError)): assets.verify(checkout)


@pytest.mark.parametrize('name', ['scripts/asset_notices.py', 'site/public/fonts/provenance.json',
    'site/public/fonts/nunito-sans-latin.woff2', 'site/public/fonts/OFL.txt',
    'protocol/normalization.py', assets.UNICODE, assets.UNICODE_COPY, assets.MODEL_CARD])
def test_changed_observed_material_is_rejected(checkout, name):
    path = checkout / name; path.write_bytes(path.read_bytes() + b'changed')
    with pytest.raises(ValueError): assets.verify(checkout)


@pytest.mark.parametrize('change', ['missing', 'linked', 'parent_link', 'traversal', 'extra', 'duplicate', 'notice'])
def test_unsafe_or_unbound_asset_is_rejected(checkout, tmp_path, change):
    path = checkout / assets.UNICODE_COPY
    if change == 'missing': path.unlink()
    elif change == 'linked':
        path.unlink(); path.symlink_to(checkout / assets.UNICODE)
    elif change == 'parent_link':
        directory = checkout / 'site/public/device-licenses'; held = tmp_path / 'held'
        directory.rename(held); directory.symlink_to(held)
    elif change == 'traversal': mutate(checkout, lambda r: r['assets'][0].update(path='../private'))
    elif change == 'extra': mutate(checkout, lambda r: r['assets'].append(dict(r['assets'][0], path='extra')))
    elif change == 'duplicate': mutate(checkout, lambda r: r['assets'].append(r['assets'][0]))
    else: mutate(checkout, lambda r: r['assets'][0]['notices'][0].update(sha256='0' * 64))
    with pytest.raises((ValueError, OSError)): assets.verify(checkout)


def test_duplicate_json_keys_rejected_before_shadowing(checkout):
    path = checkout / assets.MANIFEST; raw = path.read_text()
    path.write_text(raw.replace('{', '{"profile":"other",', 1))
    with pytest.raises(ValueError): assets.verify(checkout)


def package(members):
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode='w:gz') as archive:
        for name, data, kind in members:
            entry = tarfile.TarInfo('package/' + name)
            if kind == 'link': entry.type = tarfile.SYMTYPE; entry.linkname = '/private'
            else: entry.size = len(data)
            archive.addfile(entry, io.BytesIO(data) if kind != 'link' else None)
    raw = stream.getvalue()
    return raw, {'artifact_sha256': hashlib.sha256(raw).hexdigest(),
                 'integrity': 'sha512-' + base64.b64encode(hashlib.sha512(raw).digest()).decode()}


def test_archive_members_observed_without_extraction(tmp_path):
    raw, origin = package([(name, name.encode(), 'file') for name in assets.RUNTIME_FILES])
    assert [r['name'] for r in assets.runtime_members(raw, origin)] == list(assets.RUNTIME_FILES)
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize('change', ['duplicate', 'missing', 'link', 'digest', 'integrity'])
def test_corrupt_or_ambiguous_archive_refused(change):
    rows = [(name, name.encode(), 'file') for name in assets.RUNTIME_FILES]
    if change == 'duplicate': rows.append(rows[0])
    elif change == 'missing': rows.pop()
    elif change == 'link': rows[0] = (rows[0][0], b'', 'link')
    raw, origin = package(rows)
    if change == 'digest': origin['artifact_sha256'] = '0' * 64
    elif change == 'integrity': origin['integrity'] = 'sha512-' + base64.b64encode(b'x' * 64).decode()
    with pytest.raises(ValueError): assets.runtime_members(raw, origin)


def test_mutating_both_vendor_and_prepared_runtime_cannot_clear_upstream_identity(checkout):
    public = checkout / 'site/public/device/runtime-314.0.7'; public.mkdir(parents=True)
    vendor = checkout / 'site/node_modules/pyodide'; vendor.mkdir(parents=True)
    (vendor / 'package.json').write_text('{"version":"314.0.7"}')
    for name in assets.RUNTIME_FILES:
        (vendor / name).write_bytes(b'same altered runtime')
        (public / name).write_bytes(b'same altered runtime')
    with pytest.raises(ValueError, match='Prepared runtime differs'): assets.verify(checkout, prepared_runtime=True)


def test_cli_reports_no_clearance_and_explicit_clearance_request_fails():
    script = ROOT / 'scripts/verify-asset-notices.py'
    result = subprocess.run([sys.executable, str(script)], cwd=ROOT, capture_output=True, timeout=20)
    assert result.returncode == 0
    assert not json.loads(result.stdout)['license_release_pass']
    refused = subprocess.run([sys.executable, str(script), '--require-clearance'], cwd=ROOT, capture_output=True, timeout=20)
    assert refused.returncode == 1


def test_cli_does_not_echo_private_archive_path(tmp_path):
    path = tmp_path / 'private-canary.tgz'; path.write_bytes(b'not the observed upstream archive')
    result = subprocess.run([sys.executable, str(ROOT / 'scripts/verify-asset-notices.py'),
        '--runtime-archive', str(path)], cwd=ROOT, capture_output=True, timeout=20)
    assert result.returncode == 2 and not result.stdout
    assert str(path).encode() not in result.stderr
    assert b'private-canary' not in result.stderr
