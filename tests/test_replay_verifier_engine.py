"""Backend selection must preserve the existing private staging boundary."""
import importlib.util
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('replay_engine',ROOT/'scripts/verify-assertion-replay.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

@pytest.mark.parametrize('engine',['arbitrary-command','',None])
def test_unapproved_engine_refused_before_credentials_or_processes(monkeypatch,tmp_path,engine):
    monkeypatch.setattr(m.subprocess,'run',lambda *a,**k:pytest.fail('No process may run'))
    with pytest.raises(ValueError,match='Unsupported staging container engine'):
        m.verify(tmp_path/'missing','aitrust-staging',engine)

@pytest.mark.parametrize('engine',['docker','podman'])
def test_production_scope_stays_refused_for_either_backend(monkeypatch,tmp_path,engine):
    monkeypatch.setattr(m.sys,'platform','linux')
    monkeypatch.setattr(m.subprocess,'run',lambda *a,**k:pytest.fail('No process may run'))
    with pytest.raises(ValueError,match='dedicated Linux staging'):
        m.verify(tmp_path/'missing','production',engine)
