"""The synthetic restore must refuse before files, secrets or commands."""
import importlib.util
import os
from pathlib import Path
import stat
import sys
from types import SimpleNamespace
import pytest

ROOT = Path(__file__).resolve().parents[1]
FILE = ROOT / 'deploy/backup/restore.py'
spec = importlib.util.spec_from_file_location('restore_under_test', FILE)
restore = importlib.util.module_from_spec(spec)
spec.loader.exec_module(restore)
NAME = '20261012T000000Z-abcdef01'
ARGS = ['restore.py', '--generation', NAME, '--backup-label', '20261012-000000F',
        '--target', 'aitrust_probe_' + 'a'*32 + '_before', '--schema', 'recovery_' + 'a'*32,
        '--expected-rows', '2']


def isolated(monkeypatch):
    monkeypatch.setattr(restore.sys, 'platform', 'linux')
    monkeypatch.setattr(restore.os, 'geteuid', lambda: 0)
    original_stat = restore.os.stat
    def namespace_stat(path,*args,**kwargs):
        if str(path) in ('/proc/self/ns/net','/proc/1/ns/net'):
            return SimpleNamespace(st_dev=4,st_ino=2 if 'self' in str(path) else 1)
        return original_stat(path,*args,**kwargs)
    monkeypatch.setattr(restore.os,'stat',namespace_stat)
    monkeypatch.setattr(restore.socket, 'if_nameindex', lambda: [(1, 'lo')])


def test_valid_namespace_and_stable_identity(monkeypatch):
    isolated(monkeypatch)
    identity = restore.require_isolated_network()
    assert identity == (4, 2)
    restore.require_same_network(identity)
    with pytest.raises(ValueError, match='changed'):
        restore.require_same_network((4, 3))


@pytest.mark.parametrize('kind', ['not_linux', 'not_root', 'host', 'extra_interface', 'empty_interfaces', 'missing_proc', 'interface_error'])
def test_refused_boundary_before_any_side_effect(monkeypatch, kind):
    isolated(monkeypatch)
    if kind == 'not_linux': monkeypatch.setattr(restore.sys, 'platform', 'darwin')
    if kind == 'not_root': monkeypatch.setattr(restore.os, 'geteuid', lambda: 1000)
    if kind == 'host': monkeypatch.setattr(restore.os, 'stat', lambda p,*a,**k: SimpleNamespace(st_dev=4, st_ino=1))
    if kind == 'extra_interface': monkeypatch.setattr(restore.socket, 'if_nameindex', lambda: [(1,'lo'),(2,'eth0')])
    if kind == 'empty_interfaces': monkeypatch.setattr(restore.socket, 'if_nameindex', lambda: [])
    def unavailable(*args, **kwargs): raise OSError('private-host-diagnosis')
    if kind == 'missing_proc': monkeypatch.setattr(restore.os, 'stat', unavailable)
    if kind == 'interface_error': monkeypatch.setattr(restore.socket, 'if_nameindex', unavailable)
    def forbidden(*args, **kwargs): raise AssertionError('Side effect before boundary refusal')
    monkeypatch.setattr(restore.sys, 'argv', ARGS)
    monkeypatch.setattr(restore, 'protected_generation', forbidden)
    monkeypatch.setattr(restore.os, 'umask', forbidden)
    monkeypatch.setattr(restore, 'run', forbidden)
    monkeypatch.setattr(Path, 'mkdir', forbidden)
    monkeypatch.setattr(Path, 'read_text', forbidden)
    with pytest.raises(SystemExit) as refused:
        restore.main()
    assert 'private-host-diagnosis' not in str(refused.value)


def facts(mode=stat.S_IFDIR|0o755, owner=0):
    return SimpleNamespace(st_mode=mode,st_uid=owner,st_dev=9)


@pytest.mark.parametrize('case', ['valid', 'ancestor_symlink', 'ancestor_writable', 'ancestor_service_owned', 'container_shared', 'generation_link', 'generation_file', 'generation_shared', 'generation_service_owned', 'missing'])
def test_protected_generation_boundaries(monkeypatch, case):
    root=Path('/var/lib/aitrust-id/protected'); selected=root/NAME
    def observation(path):
        if case=='missing' and path==selected: raise FileNotFoundError('private-host-diagnosis')
        if path==root:
            return facts(stat.S_IFDIR|(0o750 if case=='container_shared' else 0o700))
        if path==selected:
            if case=='generation_link': return facts(stat.S_IFLNK|0o777)
            if case=='generation_file': return facts(stat.S_IFREG|0o700)
            if case=='generation_shared': return facts(stat.S_IFDIR|0o770)
            if case=='generation_service_owned': return facts(stat.S_IFDIR|0o700, 1000)
            return facts(stat.S_IFDIR|0o700)
        if path==Path('/var/lib'):
            if case=='ancestor_symlink': return facts(stat.S_IFLNK|0o777)
            if case=='ancestor_writable': return facts(stat.S_IFDIR|0o775)
            if case=='ancestor_service_owned': return facts(owner=1000)
        return facts()
    monkeypatch.setattr(Path, 'lstat', observation)
    monkeypatch.setattr(restore.os, 'scandir', lambda *a,**k: Entries([]))
    if case=='valid': assert restore.protected_generation(NAME)==selected
    else:
        with pytest.raises(ValueError) as refused: restore.protected_generation(NAME)
        assert 'private-host-diagnosis' not in str(refused.value)


@pytest.mark.parametrize('name', ['current', '../'+NAME, '/'+NAME, NAME+'/', '', '.staging-abcdef'])
def test_only_explicit_named_generation(monkeypatch,name):
    def forbidden(*args,**kwargs): raise AssertionError('Inspected unsupported generation')
    monkeypatch.setattr(Path,'lstat',forbidden)
    with pytest.raises(ValueError): restore.protected_generation(name)


def test_valid_network_does_not_override_generation_refusal(monkeypatch):
    isolated(monkeypatch)
    monkeypatch.setattr(restore.sys,'argv',ARGS)
    def refuse(*args,**kwargs): raise ValueError('Invalid protected generation')
    def forbidden(*args,**kwargs): raise AssertionError('Mutation after generation refusal')
    monkeypatch.setattr(restore,'protected_generation',refuse)
    monkeypatch.setattr(restore.os,'umask',forbidden)
    monkeypatch.setattr(restore,'run',forbidden)
    with pytest.raises(SystemExit,match='Invalid protected generation'): restore.main()


class Entries:
 def __init__(self,values):self.values=values
 def __enter__(self):return iter(self.values)
 def __exit__(self,*args):return False


@pytest.mark.parametrize('kind',['private_file','private_subdirectory','protected_hardlink','service_file','shared_file','symlink_file','fifo','directory_link','mount_crossing','walk_error','budget','entry_budget'])
def test_every_protected_member_is_inspected(monkeypatch,kind):
 protected=Path('/var/lib/aitrust-id/protected');selected=protected/NAME;child=selected/'child'
 def observation(path):
  value=facts(stat.S_IFDIR|(0o700 if path in (protected,selected) else 0o755))
  if path==child:
   value=facts(stat.S_IFREG|0o600)
   if kind=='private_subdirectory':value.st_mode=stat.S_IFDIR|0o700
   if kind=='service_file':value.st_uid=1000
   if kind=='shared_file':value.st_mode=stat.S_IFREG|0o640
   if kind=='symlink_file':value.st_mode=stat.S_IFLNK|0o777
   if kind=='fifo':value.st_mode=stat.S_IFIFO|0o600
   if kind=='directory_link':value.st_mode=stat.S_IFLNK|0o777
   if kind=='mount_crossing':value.st_dev=10
   if kind=='protected_hardlink':value.st_nlink=2
  return value
 monkeypatch.setattr(Path,'lstat',observation)
 def scan(folder):
  if kind=='walk_error':raise OSError('PRIVATE_RECOVERY_CANARY')
  entry=SimpleNamespace(path=str(child),stat=lambda **kwargs:observation(child))
  if Path(folder)==child:return Entries([])
  if kind=='entry_budget':return Entries(entry for _ in range(100001))
  return Entries([entry])
 monkeypatch.setattr(restore.os,'scandir',scan)
 if kind=='budget':
  moments=iter([0,31]);monkeypatch.setattr(restore.time,'monotonic',lambda:next(moments))
 if kind in ('private_file','private_subdirectory','protected_hardlink'):assert restore.protected_generation(NAME)==selected
 else:
  with pytest.raises(ValueError) as refused:restore.protected_generation(NAME)
  assert 'PRIVATE_RECOVERY_CANARY' not in str(refused.value)
