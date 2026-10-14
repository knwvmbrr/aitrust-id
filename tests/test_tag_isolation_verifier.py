"""Refuse unowned/not-ready fault runs and validate the checker before any mutation."""
import importlib.util
from pathlib import Path

import pytest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('isolation_verifier',ROOT/'scripts/verify-tag-isolation.py')
v=importlib.util.module_from_spec(spec);spec.loader.exec_module(v)


@pytest.mark.parametrize('field,value',[('status','stopped'),('status','failed'),('engine','docker'),('containers',[])])
def test_nonready_or_unexercised_engine_is_refused_without_mutation(monkeypatch,tmp_path,field,value):
    state={'status':'ready','engine':'podman','containers':['a','b','c']};state[field]=value
    monkeypatch.setattr(v.setup,'read_state',lambda folder:state)
    monkeypatch.setattr(v.setup,'Engine',lambda name:pytest.fail('Unaccepted setup entered the engine'))
    with pytest.raises(ValueError):v.verify(tmp_path,tmp_path/'runtime.env')


def test_schema_environment_must_work_before_pausing_anything(monkeypatch,tmp_path):
    import hashlib
    state={'status':'ready','engine':'podman','containers':['a','b','c'],'project':'aitrust-local-'+'f'*32}
    roles=dict(zip(state['containers'],('anonymizer','evaluator','gateway')));calls=[]
    class Engine:
        binary='synthetic'
        def run(self,*argv):
            calls.append(argv)
            assert argv[0]=='exec','Environment error caused a mutation'
            return hashlib.sha256((ROOT/'services'/roles[argv[1]]/'app.py').read_bytes()).hexdigest()
    monkeypatch.setattr(v.setup,'read_state',lambda folder:state)
    monkeypatch.setattr(v.setup,'Engine',lambda name:Engine())
    monkeypatch.setattr(v.setup,'owned',lambda engine,kind,identity,project:{'Config':{'Labels':{'org.aitrust.local-role':roles[identity]}},'State':{'Running':True,'Paused':False}})
    monkeypatch.setattr(v.aitrust,'read_token',lambda file:'synthetic-test-token')
    monkeypatch.setattr(v.aitrust,'local_request',lambda *args,**kw:{})
    monkeypatch.setattr(v.aitrust,'validate_result',lambda *args,**kw:(_ for _ in ()).throw(RuntimeError('missing schema checker')))
    with pytest.raises(RuntimeError):v.verify(tmp_path,tmp_path/'runtime.env')
    assert len(calls)==3 and all(c[0]=='exec' for c in calls)


@pytest.mark.parametrize('fault',['wrong_role','not_running','already_paused','source_mismatch'])
def test_owned_runtime_mismatch_is_refused_before_faults(monkeypatch,tmp_path,fault):
    state={'status':'ready','engine':'podman','containers':['a','b','c'],'project':'aitrust-local-'+'f'*32}
    calls=[]
    class Engine:
        def run(self,*argv):calls.append(argv);return 'f'*64
    row={'Config':{'Labels':{'org.aitrust.local-role':'anonymizer'}},'State':{'Running':True,'Paused':False}}
    if fault=='wrong_role':row['Config']['Labels']['org.aitrust.local-role']='gateway'
    if fault=='not_running':row['State']['Running']=False
    if fault=='already_paused':row['State']['Paused']=True
    monkeypatch.setattr(v.setup,'read_state',lambda folder:state)
    monkeypatch.setattr(v.setup,'Engine',lambda name:Engine())
    monkeypatch.setattr(v.setup,'owned',lambda *args:row)
    monkeypatch.setattr(v.aitrust,'read_token',lambda file:'synthetic-test-token')
    with pytest.raises(ValueError):v.verify(tmp_path,tmp_path/'runtime.env')
    assert all(c[0]=='exec' for c in calls)
