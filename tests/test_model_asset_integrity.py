"""A model manifest cannot turn corrupted or added assets into a healthy model."""
import ast
import importlib.util
import json
import os
from pathlib import Path
import pytest
ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('model_identity', ROOT/'services/anonymizer/model_identity.py')
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)


@pytest.fixture
def sealed(tmp_path):
    model = tmp_path/'model'; model.mkdir()
    (model/'weights.bin').write_bytes(bytes(range(255)))
    (model/'config.cfg').write_text('language=en\n')
    manifest = tmp_path/'manifest.json'
    digest = m.seal(model, manifest)
    return model, manifest, digest


def test_verified_identity_and_deterministic_seal(sealed, tmp_path):
    model, manifest, digest = sealed
    assert m.verify(model, manifest) == {'model_name':'en_core_web_sm', 'model_version':'3.8.0', 'manifest_sha256':digest, 'asset_files':2, 'verified_before_load':True}
    assert m.seal(model, tmp_path/'same.json') == digest


@pytest.mark.parametrize('action', ['changed', 'missing', 'extra', 'symlink', 'fifo'])
def test_asset_mutations_fail_before_load(sealed, action):
    model, manifest, _ = sealed
    if action == 'changed': (model/'config.cfg').write_text('changed')
    elif action == 'missing': (model/'weights.bin').unlink()
    elif action == 'extra': (model/'unreviewed.py').write_text('raise Exception()')
    elif action == 'symlink': (model/'outside').symlink_to(manifest)
    else: os.mkfifo(model/'fifo')
    with pytest.raises(m.ModelIntegrityError, match='failed integrity'): m.verify(model, manifest)


@pytest.mark.parametrize('action', ['missing_manifest', 'missing_digest', 'changed_manifest', 'wrong_digest', 'symlink_manifest', 'empty_root'])
def test_missing_or_changed_trust_material_fails(sealed, action):
    model, manifest, _ = sealed
    checksum = Path(str(manifest)+'.sha256')
    if action == 'missing_manifest': manifest.unlink()
    elif action == 'missing_digest': checksum.unlink()
    elif action == 'changed_manifest': manifest.write_text('{}')
    elif action == 'wrong_digest': checksum.write_text('0'*64)
    elif action == 'symlink_manifest':
        alternate = manifest.with_suffix('.other'); manifest.rename(alternate); manifest.symlink_to(alternate)
    else:
        for p in model.iterdir(): p.unlink()
    with pytest.raises(m.ModelIntegrityError): m.verify(model, manifest)


@pytest.mark.parametrize('mutate', [
    lambda d: d.update(format='model-assets/v2'),
    lambda d: d.update(model_version='4.0.0'),
    lambda d: d.update(model_name='another'),
    lambda d: d.update(extra='unexpected'),
    lambda d: d.update(files=['list']),
    lambda d: d['files'].update({'../private':d['files']['config.cfg']}),
    lambda d: d['files'].update({'/private':d['files']['config.cfg']}),
    lambda d: d['files']['config.cfg'].update(bytes=True),
    lambda d: d['files']['config.cfg'].update(bytes=-1),
    lambda d: d['files']['config.cfg'].update(sha256='G'*64),
    lambda d: d['files']['config.cfg'].update(extra='unexpected'),
])
def test_malformed_manifest_rejected_even_if_its_checksum_matches(sealed, mutate):
    model, manifest, _ = sealed
    data = json.loads(manifest.read_text()); mutate(data)
    raw = m.canonical(data); manifest.write_bytes(raw)
    Path(str(manifest)+'.sha256').write_text(m.digest(raw))
    with pytest.raises(m.ModelIntegrityError): m.verify(model, manifest)


@pytest.mark.parametrize('raw', [b'[]', b'{', b'{"format":1,"format":2}', b'['*1100, b'{"x":'+b'9'*100000+b'}', b'{"x":NaN}', b'{"x":1.1}'])
def test_invalid_json_rejected_with_fixed_error(sealed, raw):
    model, manifest, _ = sealed; manifest.write_bytes(raw)
    Path(str(manifest)+'.sha256').write_text(m.digest(raw))
    with pytest.raises(m.ModelIntegrityError, match='English model assets failed integrity verification'): m.verify(model, manifest)


def test_size_and_count_bounds(sealed, monkeypatch):
    model, manifest, _ = sealed
    monkeypatch.setattr(m, 'MAX_BYTES', 10)
    with pytest.raises(m.ModelIntegrityError): m.verify(model, manifest)
    monkeypatch.setattr(m, 'MAX_BYTES', 256*1024*1024)
    monkeypatch.setattr(m, 'MAX_FILES', 1)
    with pytest.raises(m.ModelIntegrityError): m.verify(model, manifest)


def test_startup_check_precedes_model_provider_and_never_seals():
    tree = ast.parse((ROOT/'services/anonymizer/app.py').read_text())
    called = [(node.lineno, ast.unparse(node.func)) for node in ast.walk(tree) if isinstance(node, ast.Call)]
    verification = next(line for line, name in called if name == 'verify_installed')
    creation = next(line for line, name in called if name == 'NlpEngineProvider')
    assert verification < creation
    assert not any(name.endswith('seal') for _, name in called)
