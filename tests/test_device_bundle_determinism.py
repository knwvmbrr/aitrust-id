"""Fresh-checkout-safe tests for deterministic, atomic and bounded device builds."""
import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('device_builder', ROOT/'scripts/build-device-detector.py')
B = importlib.util.module_from_spec(spec);spec.loader.exec_module(B)
RAW = (ROOT/'services/evaluator/app.py').read_bytes()

@pytest.fixture
def output(tmp_path, monkeypatch):
    (tmp_path/'services/evaluator').mkdir(parents=True)
    (tmp_path/'services/evaluator/app.py').write_bytes(RAW)
    (tmp_path/'protocol').mkdir()
    for name in ['normalization.py','unicode15-data.json']:(tmp_path/'protocol'/name).write_bytes((ROOT/'protocol'/name).read_bytes())
    monkeypatch.setattr(B, 'ROOT', tmp_path)
    return tmp_path

@pytest.mark.parametrize('text',[
    'for (a, b) in items:\n    pass\n',
    '(a, b) = items\n',
    'pairs = [a for (a, b) in items]\n',
    'for (a, (b, c)) in items:\n    pass\n',
    '(a, b), (c, d) = items\n',
    'for (a, *b) in items:\n    pass\n',
    'a["("], b = items\n',
    'prefix = "🧩"; (a, b) = items\n',
])
def test_normalization_preserves_ast_and_is_idempotent(text):
    normalized = B.canonicalize(text)
    assert ast.dump(ast.parse(normalized)) == ast.dump(ast.parse(text))
    assert B.canonicalize(normalized) == normalized

def test_strings_and_comments_are_untouched():
    text='payload = """\nfor (a, b) in items:\n(a, b) = values\n"""\n# for (c, d) in items:\n'
    assert B.canonicalize(text) == text

def test_projection_matches_reviewed_frozen_normalization_bundle():
    data, method = B.project(RAW)
    assert method == hashlib.sha256(RAW).hexdigest()
    assert hashlib.sha256(data).hexdigest() == 'd97df1909f03bb1143e79425bf481bb411e02d5a59dd6ef61828e9be791bd4fb'

def test_fresh_build_matches_manifest(output):
    manifest = B.main()
    served = output/'site/public'/manifest['path'].lstrip('/')
    assert hashlib.sha256(served.read_bytes()).hexdigest() == manifest['bundle_sha256']
    assert manifest['method_sha256'] == hashlib.sha256(RAW).hexdigest()
    assert sorted(p.name for p in served.parent.glob('method-*.py')) == [served.name]
    assert 'builder_python' not in manifest
    assert json.loads((output/'output/device-build.json').read_text())['builder_python']

def test_unchanged_build_preserves_bytes_and_mtimes(output):
    m = B.main()
    paths = [output/'site/public'/m['path'].lstrip('/'), output/'site/src/device-manifest.json']
    previous = [(p.read_bytes(), p.stat().st_mtime_ns) for p in paths]
    assert B.main() == m
    assert [(p.read_bytes(), p.stat().st_mtime_ns) for p in paths] == previous

def test_stale_bundle_removed(output):
    B.main();stale=output/'site/public/device/method-obsolete.py';stale.write_text('obsolete')
    B.main();assert not stale.exists()

def test_failed_stale_cleanup_blocks_new_manifest(output, monkeypatch):
    B.main();manifest=output/'site/src/device-manifest.json';before=manifest.read_bytes()
    stale=output/'site/public/device/method-obsolete.py';stale.write_text('obsolete')
    original = Path.unlink
    def blocked(path, *args, **kwargs):
        if path == stale:raise PermissionError('synthetic undeletable stale file')
        return original(path, *args, **kwargs)
    monkeypatch.setattr(Path,'unlink',blocked)
    with pytest.raises(PermissionError):B.main()
    assert manifest.read_bytes() == before

def test_failed_atomic_replace_keeps_previous_file_and_cleans_temporary(output, monkeypatch):
    target=output/'artifact.txt';target.write_bytes(b'previous')
    def blocked(*args):raise OSError('synthetic replace failure')
    monkeypatch.setattr(B.os,'replace',blocked)
    with pytest.raises(OSError):B.write_if_changed(target,b'next')
    assert target.read_bytes() == b'previous'
    assert not list(output.glob('.build-*'))

def test_symlink_target_rejected(output):
    external=output/'external';external.write_bytes(b'private');target=output/'target';target.symlink_to(external)
    with pytest.raises(ValueError):B.write_if_changed(target,b'next')
    assert external.read_bytes() == b'private'
