"""Diagnostic readability is separate from CI's privileged isolation assertion."""
import errno
import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    'manifest_declarations_verifier', ROOT/'scripts/verify-manifest-declarations.py')
verifier = importlib.util.module_from_spec(spec)
spec.loader.exec_module(verifier)


@pytest.mark.parametrize('unreadable', ['/proc/self/ns/net', '/proc/1/ns/net'])
def test_permission_denied_is_explicitly_unknown(monkeypatch, unreadable):
    monkeypatch.setattr(verifier.sys, 'platform', 'linux')
    calls = []

    def denied(path):
        calls.append(path)
        if path == unreadable:
            raise PermissionError(errno.EACCES, 'Permission denied', path)
        return 'net:[42]'

    monkeypatch.setattr(verifier.os, 'readlink', denied)
    assert verifier.network_namespace_observation() == {
        'network_namespace_differs_from_init': None,
        'network_namespace_probe_status': 'not_readable'}
    assert unreadable in calls


@pytest.mark.parametrize('init_namespace, differs', [('net:[42]', False), ('net:[43]', True)])
def test_readable_namespace_comparison_retains_known_result(monkeypatch, init_namespace, differs):
    monkeypatch.setattr(verifier.sys, 'platform', 'linux')
    links = {'/proc/self/ns/net': 'net:[42]', '/proc/1/ns/net': init_namespace}
    monkeypatch.setattr(verifier.os, 'readlink', links.__getitem__)
    observed = verifier.network_namespace_observation()
    assert observed['network_namespace_differs_from_init'] is differs
    assert observed['network_namespace_probe_status'] == 'observed'


def test_macos_reports_not_applicable_without_proc_probe(monkeypatch):
    monkeypatch.setattr(verifier.sys, 'platform', 'darwin')

    def forbidden(path):
        pytest.fail('Non-Linux diagnostic attempted a proc namespace probe')

    monkeypatch.setattr(verifier.os, 'readlink', forbidden)
    assert verifier.network_namespace_observation() == {
        'network_namespace_differs_from_init': None,
        'network_namespace_probe_status': 'not_applicable'}
