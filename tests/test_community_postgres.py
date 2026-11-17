import copy
import json
from pathlib import Path
import subprocess
import pytest
from tools import community_core as c
from tools import community_postgres as p
from tests.test_community_core import request


def test_adapter_refuses_unsupported_platform_before_any_database_contact(monkeypatch):
    monkeypatch.setattr(p.sys,'platform','darwin')
    monkeypatch.setattr(p,'run_worker',lambda *a,**k:pytest.fail('Must not contact PostgreSQL'))
    with pytest.raises(c.Refused):p.Postgres('/private/production')


def test_psql_uses_bounded_stdin_fixed_role_and_no_input_values_in_arguments(monkeypatch):
    pg=object.__new__(p.Postgres);pg.argv=['/usr/bin/env','-i','psql']
    seen=[]
    def worker(argv,**kwargs):
        seen.append((argv,kwargs));return subprocess.CompletedProcess(argv,0,b't\n',b'')
    monkeypatch.setattr(p,'run_worker',worker)
    assert pg.sql("SELECT 'PRIVATE_CANARY';",'ait_community_runtime')=='t'
    argv,k=seen[0];assert 'PRIVATE_CANARY' not in str(argv)
    assert k['timeout']==6 and k['output_limit']==524288 and k['input'].startswith(b'SET ROLE ait_community_runtime;')
    with pytest.raises(c.Refused):pg.sql('SELECT 1','ait_community_owner')
    assert len(seen)==1


def test_failed_psql_worker_is_a_fixed_refusal(monkeypatch):
    pg=object.__new__(p.Postgres);pg.argv=['psql']
    monkeypatch.setattr(p,'run_worker',lambda *a,**k:subprocess.CompletedProcess(a,1,b'',b'PRIVATE_CANARY'))
    with pytest.raises(c.Refused) as error:pg.sql('SELECT 1')
    assert 'PRIVATE_CANARY' not in str(error.value)


def test_compare_swap_retries_same_request_without_overwriting_and_bounds_conflict():
    pg=object.__new__(p.Postgres);base=c.initial();queries=[]
    pg.read=lambda:c.Community(base)
    pg.sql=lambda query,role:(queries.append(query) or ('f' if len(queries)==1 else 't'))
    req=request('submit',{'body':"Invented '; SQL text",'consent_public':True})
    result=pg.apply('user-one',req,1000)
    assert result['id']==req['request_id'] and len(queries)==2
    assert all("Invented" not in q for q in queries)
    queries.clear();pg.sql=lambda query,role:(queries.append(query) or 'f')
    with pytest.raises(c.Refused):pg.apply('user-one',req,1000)
    assert len(queries)==6


@pytest.mark.parametrize('kwargs',[{'after':-1},{'after':True},{'limit':21},{'limit':False},{'private':True}])
def test_public_query_limits_are_checked_before_sql(kwargs):
    pg=object.__new__(p.Postgres);pg.sql=lambda *a,**k:pytest.fail('No query for malformed arguments')
    with pytest.raises(c.Refused):pg.view('public',**kwargs)


def test_hosted_workflow_tracks_every_executed_source_and_keeps_synthetic_isolation():
    import fnmatch
    import importlib.util
    import yaml
    root=Path(__file__).resolve().parents[1]
    spec=importlib.util.spec_from_file_location('community_pg_verifier_inventory',root/'scripts/verify-community-postgres.py')
    verifier=importlib.util.module_from_spec(spec);spec.loader.exec_module(verifier)
    workflow=yaml.safe_load((root/'.github/workflows/community-workbench.yml').read_text())
    triggers=workflow.get('on',workflow.get(True))
    for event in ('push','pull_request'):
        patterns=triggers[event]['paths']
        for path in verifier.SOURCES:
            assert (root/path).is_file() and any(fnmatch.fnmatchcase(path,p) for p in patterns),path
    serialized=json.dumps(workflow)
    assert 'sudo unshare --net' in serialized and '--run-as' in serialized
    assert workflow['permissions']=={'contents':'read'}


def test_postgres_state_encoding_preserves_utf8_within_the_storage_budget():
    value = {'public': '☕🌳'}
    encoded = p.encode_state(value)
    assert encoded == '{"public":"☕🌳"}'.encode('utf-8')
    assert json.loads(encoded) == value and len(encoded) < len(c.encode(value))
