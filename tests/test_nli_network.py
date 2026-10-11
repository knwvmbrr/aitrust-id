"""Failure controls never load a real filter into the test runner."""
import json
from pathlib import Path
import subprocess
import sys
from unittest.mock import Mock

import pytest
from research.nli import network
from research.nli.pairs import PairError


def library():
    lib = Mock()
    lib.seccomp_arch_native.return_value = 0xc000003e
    lib.seccomp_init.return_value = 123
    for name in ('seccomp_attr_set', 'seccomp_rule_add', 'seccomp_load'):
        getattr(lib, name).return_value = 0
    lib.seccomp_syscall_resolve_name.return_value = 1
    return lib


@pytest.fixture
def fake(monkeypatch):
    lib = library()
    monkeypatch.setattr(network.platform, 'system', lambda: 'Linux')
    monkeypatch.setattr(network.platform, 'machine', lambda: 'x86_64')
    monkeypatch.setattr(network.ctypes, 'CDLL', lambda *a, **k: lib)
    monkeypatch.setattr(network.Path, 'read_text', lambda p: 'NoNewPrivs:\t1\nSeccomp:\t2\n')
    return lib


def test_all_rules_and_synchronization_are_required(fake):
    result = network.install_linux_network_filter()
    assert result['denied_syscalls'] == list(network.DENIED)
    assert fake.seccomp_rule_add.call_count == len(network.DENIED)
    assert [c.args for c in fake.seccomp_attr_set.call_args_list] == [(123, 3, 1), (123, 4, 1)]
    fake.seccomp_release.assert_called_once_with(123)


@pytest.mark.parametrize('failure', ['architecture', 'context', 'nnp', 'threads', 'resolve', 'rule', 'load', 'status'])
def test_failure_refuses_instead_of_claiming_network_control(fake, monkeypatch, failure):
    if failure == 'architecture': fake.seccomp_arch_native.return_value = 0
    if failure == 'context': fake.seccomp_init.return_value = 0
    if failure == 'nnp': fake.seccomp_attr_set.side_effect = [-1, 0]
    if failure == 'threads': fake.seccomp_attr_set.side_effect = [0, -1]
    if failure == 'resolve': fake.seccomp_syscall_resolve_name.return_value = -1
    if failure == 'rule': fake.seccomp_rule_add.return_value = -1
    if failure == 'load': fake.seccomp_load.return_value = -1
    if failure == 'status': monkeypatch.setattr(network.Path, 'read_text', lambda p: 'NoNewPrivs: 0\nSeccomp: 0\n')
    with pytest.raises(PairError): network.install_linux_network_filter()
    if failure not in ('architecture', 'context'): fake.seccomp_release.assert_called_once_with(123)


@pytest.mark.parametrize('platform,arch', [('Darwin', 'arm64'), ('Linux', 'i686'), ('Windows', 'AMD64')])
def test_unsupported_platform_does_not_load_library(fake, monkeypatch, platform, arch):
    monkeypatch.setattr(network.platform, 'system', lambda: platform)
    monkeypatch.setattr(network.platform, 'machine', lambda: arch)
    with pytest.raises(PairError): network.install_linux_network_filter()
    fake.seccomp_init.assert_not_called()


@pytest.mark.skipif(sys.platform != 'linux', reason='Actual filter runs only in an isolated Linux subprocess')
def test_actual_unprivileged_network_denial_and_descendant():
    code = '''
import errno,json,socket,subprocess,sys
from research.nli.network import install_linux_network_filter
record=install_linux_network_filter()
for family in (socket.AF_INET,socket.AF_INET6,socket.AF_UNIX):
 try: socket.socket(family)
 except PermissionError as error: assert error.errno==errno.EPERM
 else: raise AssertionError('Socket was permitted')
try: socket.socketpair()
except PermissionError as error: assert error.errno==errno.EPERM
else: raise AssertionError('Socket pair was permitted')
child=subprocess.run([sys.executable,'-c','import socket;socket.socket()'],capture_output=True)
assert child.returncode!=0 and b'PermissionError' in child.stderr
print(json.dumps(record))
'''
    run = subprocess.run([sys.executable, '-c', code], cwd=Path(__file__).resolve().parents[1],
                         capture_output=True, timeout=10)
    assert run.returncode == 0, run.stderr.decode()
    assert json.loads(run.stdout)['no_new_privileges'] is True
