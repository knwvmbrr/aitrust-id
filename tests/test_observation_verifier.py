"""A restricted diagnostic must not become a fictional isolation claim."""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('observation_verifier', ROOT/'scripts/verify-independent-observations.py')
verifier = importlib.util.module_from_spec(spec); spec.loader.exec_module(verifier)


def test_permission_denial_is_unknown(monkeypatch):
    monkeypatch.setattr(verifier.sys, 'platform', 'linux')
    def denied(path):
        raise PermissionError('Restricted proc namespace')
    monkeypatch.setattr(verifier.os, 'readlink', denied)
    assert verifier.network_namespace_comparison() is None


def test_unavailable_proc_entry_is_unknown(monkeypatch):
    monkeypatch.setattr(verifier.sys, 'platform', 'linux')
    def absent(path):
        raise FileNotFoundError('No proc namespace')
    monkeypatch.setattr(verifier.os, 'readlink', absent)
    assert verifier.network_namespace_comparison() is None


def test_actual_namespace_comparison_preserves_false_and_true(monkeypatch):
    monkeypatch.setattr(verifier.sys, 'platform', 'linux')
    monkeypatch.setattr(verifier.os, 'readlink', lambda path: 'net:[1]')
    assert verifier.network_namespace_comparison() is False
    monkeypatch.setattr(verifier.os, 'readlink', lambda path: 'net:[1]' if path=='/proc/1/ns/net' else 'net:[2]')
    assert verifier.network_namespace_comparison() is True


def test_non_linux_does_not_probe_proc(monkeypatch):
    monkeypatch.setattr(verifier.sys, 'platform', 'darwin')
    def forbidden(path):
        raise AssertionError('Non-Linux probe forbidden')
    monkeypatch.setattr(verifier.os, 'readlink', forbidden)
    assert verifier.network_namespace_comparison() is None


def test_method_identity_is_bound_to_the_specific_invoked_tool():
    inventory={path: str(index)*64 for index,path in enumerate(verifier.METHOD_SOURCES.values(),1)}
    for script,source in verifier.METHOD_SOURCES.items():
        assert verifier.method_matches({'method_sha256':inventory[source]},[script],inventory)
        for foreign in inventory.values():
            if foreign != inventory[source]:
                assert not verifier.method_matches({'method_sha256':foreign},[script],inventory)
    assert not verifier.method_matches({'method_sha256':'1'*64},['unknown.py'],inventory)
    assert not verifier.method_matches({},[],inventory)
    assert not verifier.method_matches({},['scripts/credential-flow.py'],inventory)
    assert not verifier.method_matches({},['scripts/credential-flow.py'],{})
