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


@pytest.mark.skipif(sys.platform != 'linux', reason='Exercises Linux-only disposable-directory and errno contract')
@pytest.mark.parametrize('stage,exception,cleanup_interrupted', [
    ('version', KeyboardInterrupt, False),
    ('start', KeyboardInterrupt, False),
    ('start', KeyboardInterrupt, True),
    ('version', SystemExit, False),
])
def test_cancellation_preserved_after_owned_cleanup(monkeypatch, stage, exception, cleanup_interrupted):
    # Fake only process/namespace seams; exercise the real private-file lifecycle.
    # No PostgreSQL process is created by this unit test.
    import shutil
    observed = {'work': None, 'running': False, 'stopped': False}
    original = exception('original cancellation')
    old_umask = retention.os.umask(0o077)
    actual_mkdtemp = retention.tempfile.mkdtemp
    actual_is_dir, actual_is_file = Path.is_dir, Path.is_file
    def owned_temp(**kwargs):
        name = actual_mkdtemp(**kwargs)
        observed['work'] = Path(name)
        return name
    class RefusedSocket:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def settimeout(self, *args): pass
        def connect(self, *args): raise OSError(101, 'simulated Linux ENETUNREACH')
    def fake_process(args, **kwargs):
        args = list(map(str, args))
        if args[-1] == 'version':
            if stage == 'version': raise original
            return SimpleNamespace(returncode=0, stdout=b'pgBackRest 2.59.3', stderr=b'')
        if args[-1] == '--version':
            return SimpleNamespace(returncode=0, stdout=b'postgres (PostgreSQL) 18.6', stderr=b'')
        if args[0].endswith('/initdb'):
            Path(args[args.index('-D')+1]).mkdir()
        if args[-1] == 'start':
            observed['running'] = True
            raise original
        if args[-1] == 'status':
            return SimpleNamespace(returncode=0 if observed['running'] else 3, stdout=b'', stderr=b'')
        if args[-1] == 'stop':
            if cleanup_interrupted: raise KeyboardInterrupt('second cancellation')
            observed['running'] = False
            observed['stopped'] = True
        return SimpleNamespace(returncode=0, stdout=b'', stderr=b'')
    monkeypatch.setattr(retention, 'hashes', lambda: {})
    monkeypatch.setattr(retention, 'require_namespace', lambda _: None)
    monkeypatch.setattr(retention.socket, 'socket', lambda *args: RefusedSocket())
    monkeypatch.setattr(retention.tempfile, 'mkdtemp', owned_temp)
    monkeypatch.setattr(Path, 'is_dir', lambda self: True if str(self)=='/usr/lib/postgresql/18/bin' else actual_is_dir(self))
    monkeypatch.setattr(Path, 'is_file', lambda self: True if str(self)=='/usr/bin/pgbackrest' else actual_is_file(self))
    monkeypatch.setattr(retention.shutil, 'disk_usage', lambda _: SimpleNamespace(free=3_000_000_000))
    monkeypatch.setattr(retention.subprocess, 'run', fake_process)
    try:
        with pytest.raises(exception) as raised:
            retention.verify((1, 2))
        assert raised.value is original
        assert observed['work'] is not None
        assert observed['work'].exists() is cleanup_interrupted
        if stage == 'start' and not cleanup_interrupted:
            assert observed['stopped'] and not observed['running']
    finally:
        retention.os.umask(old_umask)
        # A retained fake cluster has no process; remove only this test-owned path.
        if observed['work'] is not None and observed['work'].exists():
            shutil.rmtree(observed['work'])
