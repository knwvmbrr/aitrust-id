"""Refuse unsafe backup execution before creating files or changing privilege."""
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from tools import backup_retention as retention

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize('platform,uid,optimize,name', [
    ('darwin', 0, 0, 'debian'), ('linux', 1000, 0, 'debian'),
    ('linux', 0, 1, 'debian'), ('linux', 0, 0, '../debian'),
    ('linux', 0, 0, 'debian;id'), ('linux', 0, 0, ''),
])
def test_early_refusal_has_no_privilege_or_file_operations(monkeypatch, platform, uid, optimize, name):
    monkeypatch.setattr(sys, 'platform', platform)
    monkeypatch.setattr(sys, 'flags', SimpleNamespace(optimize=optimize))
    monkeypatch.setattr(retention.os, 'geteuid', lambda: uid)
    def forbidden(*args, **kwargs):
        pytest.fail('Unsafe request reached a state-changing operation')
    monkeypatch.setattr(retention.os, 'setuid', forbidden)
    monkeypatch.setattr(retention.tempfile, 'mkdtemp', forbidden)
    monkeypatch.setattr(retention.importlib.util, 'spec_from_file_location', forbidden)
    with pytest.raises(ValueError):
        retention.prepare_account(name)


@pytest.mark.parametrize('uid,optimize,interfaces,expected', [
    (0, 0, [(1, 'lo')], (1, 2)),
    (1000, 1, [(1, 'lo')], (1, 2)),
    (1000, 0, [(1, 'lo'), (2, 'eth0')], (1, 2)),
    (1000, 0, [(1, 'lo')], (9, 9)),
])
def test_current_namespace_and_non_root_identity_are_required(monkeypatch, uid, optimize, interfaces, expected):
    monkeypatch.setattr(sys, 'platform', 'linux')
    monkeypatch.setattr(sys, 'flags', SimpleNamespace(optimize=optimize))
    monkeypatch.setattr(retention.os, 'geteuid', lambda: uid)
    monkeypatch.setattr(retention.os, 'stat', lambda *args: SimpleNamespace(st_dev=1, st_ino=2))
    monkeypatch.setattr(retention.socket, 'if_nameindex', lambda: interfaces)
    with pytest.raises(ValueError):
        retention.require_namespace(expected)


def test_namespace_failure_precedes_database_or_temporary_directory(monkeypatch):
    monkeypatch.setattr(retention, 'hashes', lambda: {})
    def refuse(*args):
        raise ValueError('boundary')
    def forbidden(*args, **kwargs):
        pytest.fail('No database or directory may be created after isolation failure')
    monkeypatch.setattr(retention, 'require_namespace', refuse)
    monkeypatch.setattr(retention.os, 'umask', forbidden)
    monkeypatch.setattr(retention.tempfile, 'mkdtemp', forbidden)
    monkeypatch.setattr(retention.subprocess, 'run', forbidden)
    with pytest.raises(ValueError):
        retention.verify((1, 2))


def cli_module():
    spec = importlib.util.spec_from_file_location('backup_retention_cli', ROOT/'scripts/verify-backup-retention.py')
    module = importlib.util.module_from_spec(spec)
    old = sys.dont_write_bytecode
    try:
        spec.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = old
    return module


@pytest.mark.parametrize('failure', [ValueError, KeyError, OSError, RuntimeError, AssertionError])
def test_setup_failures_do_not_echo_private_values_or_write_reports(monkeypatch, capsys, failure):
    cli = cli_module()
    def refuse(*args):
        raise failure('PRIVATE_KEY_OR_PATH_CANARY')
    def forbidden(*args, **kwargs):
        pytest.fail('Setup refusal must not publish a report or private log')
    monkeypatch.setattr(cli, 'prepare_account', refuse)
    monkeypatch.setattr(cli, 'write_report', forbidden)
    monkeypatch.setattr(cli, 'create', forbidden)
    assert cli.main(['--run-as', 'debian']) == 2
    captured = capsys.readouterr()
    assert captured.out == ''
    result = json.loads(captured.err)
    assert result['state'] == 'UNAVAILABLE'
    assert 'PRIVATE_KEY_OR_PATH_CANARY' not in captured.err


def test_actual_cli_parser_does_not_echo_unknown_private_argument(tmp_path):
    result = subprocess.run([sys.executable, '-I', '-B', str(ROOT/'scripts/verify-backup-retention.py'),
        '--unknown', 'PRIVATE_ARGUMENT_CANARY'], cwd=tmp_path, capture_output=True, text=True, timeout=15)
    assert result.returncode == 2
    assert result.stdout == ''
    assert result.stderr == 'Backup retention check refused; use --help for arguments.\n'
    assert not list(tmp_path.iterdir())
