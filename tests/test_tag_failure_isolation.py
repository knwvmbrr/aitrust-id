"""Selected routes reserve capacity independently; security prerequisites still apply."""
import asyncio
import json

import httpx
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from protocol.assertions import validator
from replay_fixture import synthetic_identity
from test_gateway_cancellation import Request
from test_gateway_integration import g
from test_local_cli import cli,credential


@pytest.mark.parametrize('blocked_mode,healthy_mode,capacity',[('all','privacy',3),('privacy','all',1)])
def test_saturated_route_cannot_take_other_routes_capacity(monkeypatch,blocked_mode,healthy_mode,capacity):
    async def scenario():
        started=0;full=asyncio.Event();release=asyncio.Event()
        async def handle(req):
            nonlocal started
            body=json.loads(req.content)
            # Different selected text lets the synthetic redactor stall one
            # route; no real recognizer accuracy is inferred from this fixture.
            if body['text']=='stalled':
                started+=1
                if started==capacity:full.set()
                await release.wait()
            if req.url.path=='/redact':
                return httpx.Response(200,json={'identity':synthetic_identity(),'text':body['text'],'entities':[],'entity_count':0})
            return httpx.Response(200,json={'candidates':[],'models':[],'calibration_id':'synthetic'})
        original=httpx.AsyncClient
        monkeypatch.setattr(g.httpx,'AsyncClient',lambda **kw:original(transport=httpx.MockTransport(handle),**kw))
        monkeypatch.setattr(g,'LIMIT',asyncio.Semaphore(3));monkeypatch.setattr(g,'PRIVACY_LIMIT',asyncio.Semaphore(1))
        def evaluate(mode,text):return g.evaluate(g.EvalRequest(text=text,check_mode=mode),Request(),'Bearer '+g.TOKEN,'')
        tasks=[asyncio.create_task(evaluate(blocked_mode,'stalled')) for _ in range(capacity)]
        try:
            await asyncio.wait_for(full.wait(),1)
            with pytest.raises(HTTPException) as exc:await evaluate(blocked_mode,'not admitted')
            assert exc.value.status_code==503
            good=await asyncio.wait_for(evaluate(healthy_mode,'healthy'),1)
            validator().validate(good)
            assert good['tags']==[]
            assert g.LIMIT._value==(0 if blocked_mode=='all' else 3)
            assert g.PRIVACY_LIMIT._value==(0 if blocked_mode=='privacy' else 1)
        finally:
            # Do not leave started requests running when an assertion fails.
            for task in tasks:task.cancel()
            await asyncio.gather(*tasks,return_exceptions=True)
        assert g.LIMIT._value==3 and g.PRIVACY_LIMIT._value==1
        recovered=await asyncio.wait_for(evaluate(blocked_mode,'recovered'),1)
        validator().validate(recovered)
    asyncio.run(scenario())


@pytest.mark.parametrize('mode',['all','privacy'])
@pytest.mark.parametrize('failure',['timeout','malformed','redactor_failure'])
def test_failure_returns_only_selected_slot_and_recovers(monkeypatch,mode,failure):
    async def scenario():
        broken=True
        async def handle(req):
            if broken:
                if failure=='timeout':raise httpx.ReadTimeout('PRIVATE',request=req)
                return httpx.Response(200 if failure=='malformed' else 500,json={'private':'never echo'})
            if req.url.path=='/redact':return httpx.Response(200,json={'identity':synthetic_identity(),'text':'healthy','entities':[],'entity_count':0})
            return httpx.Response(200,json={'candidates':[],'models':[],'calibration_id':'synthetic'})
        original=httpx.AsyncClient
        monkeypatch.setattr(g.httpx,'AsyncClient',lambda **kw:original(transport=httpx.MockTransport(handle),**kw))
        monkeypatch.setattr(g,'LIMIT',asyncio.Semaphore(3));monkeypatch.setattr(g,'PRIVACY_LIMIT',asyncio.Semaphore(1))
        with pytest.raises(HTTPException) as exc:
            await g.evaluate(g.EvalRequest(text='healthy',check_mode=mode),Request(),'Bearer '+g.TOKEN,'')
        assert exc.value.status_code==(504 if failure=='timeout' else 502)
        assert 'PRIVATE' not in exc.value.detail and 'never echo' not in exc.value.detail
        assert g.LIMIT._value==3 and g.PRIVACY_LIMIT._value==1
        broken=False
        row=await g.evaluate(g.EvalRequest(text='healthy',check_mode=mode),Request(),'Bearer '+g.TOKEN,'')
        validator().validate(row)
    asyncio.run(scenario())


def test_privacy_readiness_does_not_probe_failed_ps_and_default_still_fails(monkeypatch):
    paths=[]
    def handle(req):
        paths.append(req.url.host)
        return httpx.Response(200 if req.url.host=='anonymizer' else 503,json={'ok':True})
    original=httpx.AsyncClient
    monkeypatch.setattr(g.httpx,'AsyncClient',lambda **kw:original(transport=httpx.MockTransport(handle),**kw))
    with TestClient(g.app) as client:
        assert client.get('/healthz?check_mode=privacy').status_code==200
        assert paths==['anonymizer'];paths.clear()
        assert client.get('/healthz').status_code==503
        assert paths==['anonymizer','evaluator'];paths.clear()
        assert client.get('/healthz?check_mode=unknown').status_code==422 and not paths


@pytest.mark.parametrize('value',[[],None,'ok',{'ok':False}])
def test_invalid_health_is_unavailable_not_a_gateway_crash(monkeypatch,value):
    original=httpx.AsyncClient
    monkeypatch.setattr(g.httpx,'AsyncClient',lambda **kw:original(transport=httpx.MockTransport(
        lambda req:httpx.Response(200,json=value)),**kw))
    with TestClient(g.app) as client:assert client.get('/healthz?check_mode=privacy').status_code==503


def test_owner_doctor_can_select_privacy_without_ps(tmp_path,monkeypatch,capsys):
    from test_draft_privacy import privacy_response
    response,_=privacy_response(monkeypatch,found=False);row=response.json();env=credential(tmp_path)
    calls=[]
    def local(path,payload=None,token=None):
        calls.append((path,payload))
        return {'ok':True} if payload is None else row
    monkeypatch.setattr(cli,'local_request',local)
    assert cli.main(['doctor','--privacy','--env-file',str(env)])==0
    assert calls[0]==('/healthz?check_mode=privacy',None)
    assert calls[1][1]['check_mode']=='privacy'
    assert 'privacy check ready' in capsys.readouterr().out


def test_compose_privacy_startup_cannot_depend_on_the_ps_evaluator():
    import yaml
    from pathlib import Path
    config = yaml.safe_load((Path(__file__).resolve().parents[1] /
                             'deploy/docker-compose.yml').read_text())
    gateway = config['services']['gateway']
    assert gateway['depends_on'] == {'anonymizer': {'condition': 'service_healthy'}}
    assert gateway['ports'] == ['127.0.0.1:8787:8000']
    assert config['networks']['inspection']['internal'] is True
    assert gateway['cap_drop'] == ['ALL']
    assert gateway['read_only'] is True
    assert gateway['mem_limit'] == '256m'
