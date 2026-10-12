"""Pre-side-effect controls; real database/role/concurrency tests run on Linux."""
import importlib.util
from pathlib import Path
import subprocess
import sys

import pytest

ROOT=Path(__file__).resolve().parents[1]


def load(name):
    spec=importlib.util.spec_from_file_location(name,ROOT/'scripts'/('metadata-store-sandbox.py' if name=='runner' else 'verify-research-invitations.py'))
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


@pytest.mark.parametrize('profile',['participant','live','../../service',None])
def test_unknown_profile_refuses_before_sandbox_or_process(profile,monkeypatch):
    module=load('runner')
    monkeypatch.setattr(module.tempfile,'mkdtemp',lambda *a,**k:pytest.fail('No sandbox created'))
    monkeypatch.setattr(module.subprocess,'run',lambda *a,**k:pytest.fail('No process started'))
    with pytest.raises(ValueError,match='supported synthetic storage profile'):
        module.run_control('output/verification/unused.json',profile)


@pytest.mark.parametrize('path',['/','/tmp','/var/lib/postgresql/18/main','relative'])
def test_invitation_worker_refuses_non_sandbox_before_psql(path,monkeypatch):
    module=load('invitation')
    monkeypatch.setattr(module.subprocess,'run',lambda *a,**k:pytest.fail('No database call'))
    with pytest.raises((ValueError,OSError)):module.verify(path)


def test_invitation_worker_refuses_root_before_psql(tmp_path,monkeypatch):
    module=load('invitation')
    monkeypatch.setattr(module.os,'geteuid',lambda:0)
    monkeypatch.setattr(module.subprocess,'run',lambda *a,**k:pytest.fail('No database call'))
    with pytest.raises(ValueError):module.verify(tmp_path)


def test_real_invitation_cli_refusal_hides_path_and_traceback():
    result=subprocess.run([sys.executable,str(ROOT/'scripts/verify-research-invitations.py'),
        '--sandbox-dir','/PRIVATE_INVITATION_CANARY'],capture_output=True,timeout=8)
    assert result.returncode==1
    assert b'PRIVATE_INVITATION_CANARY' not in result.stdout+result.stderr
    assert b'Traceback' not in result.stdout+result.stderr
    assert b'no production acceptance' in result.stderr


def test_synthetic_digests_are_fixed_width_and_not_live_credentials():
    module=load('invitation')
    assert module.digest(1)=="decode('"+'0'*63+"1','hex')"
    with pytest.raises(OverflowError):module.digest(2**256)
