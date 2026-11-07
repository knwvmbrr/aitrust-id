"""Refuse stale/partial proofs and premature native release claims."""
import copy
import json
from pathlib import Path
import runpy
import shutil
import pytest

ROOT = Path(__file__).resolve().parents[1]
guard = runpy.run_path(str(ROOT / 'scripts/verify-native-share-evidence.py'))


def proof():
    return json.loads((ROOT / guard['PROOF']).read_text())


@pytest.fixture
def prepared_assets():
    if not (ROOT / 'site/node_modules/pyodide/package.json').is_file() or not (ROOT / 'site/src/device-manifest.json').is_file():
        pytest.skip('The required site job runs asset equality after preparing the pinned runtime.')


def test_current_native_software_proof(prepared_assets):
    assert guard['verify']()['pass']


@pytest.mark.parametrize('key,value', [('physical_device', True), ('independent_accuracy', True),
    ('human_accessibility', True), ('installable_phone_release', True), ('pass', False),
    ('source_unchanged_during_execution', False), ('owned_simulator_removed', False),
    ('test_count', 4), ('test_count', 5.0), ('profile', 'unknown'), ('captured_at', '2099-01-01T00:00:00+00:00')])
def test_overclaim_or_partial_execution_refused(key, value):
    value_proof = proof(); value_proof[key] = value
    with pytest.raises(ValueError): guard['verify'](proof=value_proof)


def test_changed_source_identity_refused():
    value = proof(); value['sources']['mobile/ios/Source/ShareController.swift'] = '0' * 64
    with pytest.raises(ValueError): guard['verify'](proof=value)


def test_missing_asset_identity_refused():
    value = proof(); value['asset_fingerprints'].pop(next(iter(value['asset_fingerprints'])))
    with pytest.raises(ValueError): guard['verify'](proof=value)


def test_unknown_asset_identity_refused():
    value = proof(); expected = value['asset_fingerprints'].pop('/bridge.mjs')
    value['asset_fingerprints']['/unreviewed.mjs'] = expected
    with pytest.raises(ValueError): guard['verify'](proof=value)


def test_zeroed_executable_asset_digest_refused(prepared_assets):
    value = proof(); value['asset_fingerprints']['/method.py'] = '0' * 64
    with pytest.raises(ValueError, match='Native bundle differs'):
        guard['verify'](proof=value)


def test_projection_generator_change_invalidates_execution(tmp_path):
    module = runpy.run_path(str(ROOT / 'scripts/verify-ios-share.py'))
    for name in module['SOURCES']:
        target = tmp_path / name; target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, target)
    path = tmp_path / 'scripts/build-device-detector.py'
    path.write_text(path.read_text() + '\n# A generator revision requires new native execution.\n')
    with pytest.raises(ValueError, match='Native sources changed'):
        guard['verify'](root=tmp_path, proof=proof())


@pytest.mark.parametrize('field,value', [('percent_complete', 100),
                                      ('completed_at', '2026-11-07T00:00:00+00:00'),
                                      ('completed_by', ['unverified'])])
def test_simulator_proof_cannot_close_physical_acceptance(tmp_path, field, value):
    module = runpy.run_path(str(ROOT / 'scripts/verify-ios-share.py'))
    for name in [*module['SOURCES'], 'docs/scope-progress.json']:
        target = tmp_path / name; target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, target)
    path = tmp_path / 'docs/scope-progress.json'; progress = json.loads(path.read_text())
    next(r for r in progress['records'] if r['id'] == 'N-013')[field] = value
    path.write_text(json.dumps(progress))
    with pytest.raises(ValueError): guard['verify'](root=tmp_path, proof=proof())
