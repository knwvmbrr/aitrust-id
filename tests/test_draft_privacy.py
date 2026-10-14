"""Privacy-only work must stay independent of the command detector and sending."""
import asyncio
import copy
import hashlib
import json
from pathlib import Path

import httpx
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from replay_fixture import synthetic_identity
from test_gateway_integration import g
from test_gateway_cancellation import Request
from test_local_cli import cli, credential
from protocol.assertions import validator

TEXT='Email alice@example.test before sharing.'
ROOT=Path(__file__).resolve().parents[1]


def privacy_response(monkeypatch, found=True, fail=False):
    calls=[]
    def handle(request):
        calls.append((request.url.path,json.loads(request.content)))
        assert request.url.path=='/redact', 'Privacy mode entered the evaluator'
        if fail:return httpx.Response(500,json={})
        return httpx.Response(200,json={'text':'Email <EMAIL_ADDRESS> before sharing.' if found else TEXT,
            'entities':['EMAIL_ADDRESS'] if found else [],'entity_count':int(found),
            'identity':synthetic_identity()})
    original=httpx.AsyncClient
    monkeypatch.setattr(g.httpx,'AsyncClient',lambda **kw:original(transport=httpx.MockTransport(handle),**kw))
    with TestClient(g.app) as client:
        response=client.post('/v1/evaluate',headers={'authorization':'Bearer '+g.TOKEN},
                             json={'text':TEXT,'check_mode':'privacy'})
    return response,calls


@pytest.mark.parametrize('found',[False,True])
def test_privacy_uses_only_redactor_and_exact_identity(monkeypatch,found):
    response,calls=privacy_response(monkeypatch,found)
    assert response.status_code==200
    row=response.json();validator().validate(row)
    assert len(calls)==1 and calls[0][0]=='/redact'
    assert row['evaluator']['calibration_id']=='procedural-redaction-v1'
    assert [m['name'] for m in row['evaluator']['models']]==['presidio-redaction','gateway-pipeline']
    assert [t['code'] for t in row['tags']]==(['PII_REDACTED'] if found else [])
    assert row['abstentions']==[] and 'alice@example.test' not in response.text
    assert cli.validate_result(row,privacy=True)==row
    with pytest.raises(cli.LocalCheckError):cli.validate_result(row)


def test_redactor_failure_never_becomes_a_privacy_clearance(monkeypatch):
    response,calls=privacy_response(monkeypatch,fail=True)
    assert response.status_code==502 and len(calls)==1
    assert 'tags' not in response.json() and TEXT not in response.text


@pytest.mark.parametrize('mode',[False,True,None,[],{},'PS','Privacy','privacy-only',''])
def test_unknown_modes_fail_before_upstream(monkeypatch,mode):
    calls=[]
    original=httpx.AsyncClient
    def handle(req):calls.append(req);raise AssertionError('Invalid mode reached a service')
    monkeypatch.setattr(g.httpx,'AsyncClient',lambda **kw:original(transport=httpx.MockTransport(handle),**kw))
    with TestClient(g.app) as client:
        response=client.post('/v1/evaluate',headers={'authorization':'Bearer '+g.TOKEN},
                             json={'text':TEXT,'check_mode':mode})
    assert response.status_code==422 and calls==[]


@pytest.mark.parametrize('headers,modality,status',[
    ({},'text',401),
    ({'authorization':'Bearer incorrect'},'text',401),
    ({'authorization':'Bearer '+g.TOKEN,'origin':'https://hostile.test'},'text',403),
    ({'authorization':'Bearer '+g.TOKEN},'document',422),
    ({'authorization':'Bearer '+g.TOKEN,'X-AITrust-Nonce':'bad'},'text',422),
])
def test_privacy_never_bypasses_existing_controls(monkeypatch,headers,modality,status):
    original=httpx.AsyncClient
    monkeypatch.setattr(g.httpx,'AsyncClient',lambda **kw:original(
        transport=httpx.MockTransport(lambda req:pytest.fail('Unauthorized upstream access')),**kw))
    with TestClient(g.app) as client:
        response=client.post('/v1/evaluate',headers=headers,
                             json={'text':TEXT,'modality':modality,'check_mode':'privacy'})
    assert response.status_code==status


def test_privacy_disconnect_cancels_redaction_and_releases_slot(monkeypatch):
    async def scenario():
        started=asyncio.Event();cancelled=asyncio.Event()
        async def handle(req):
            assert req.url.path=='/redact';started.set()
            try:await asyncio.Event().wait()
            except asyncio.CancelledError:cancelled.set();raise
        original=httpx.AsyncClient
        monkeypatch.setattr(g.httpx,'AsyncClient',lambda **kw:original(transport=httpx.MockTransport(handle),**kw))
        monkeypatch.setattr(g,'LIMIT',asyncio.Semaphore(4))
        request=Request();task=asyncio.create_task(g.evaluate(
            g.EvalRequest(text=TEXT,check_mode='privacy'),request,'Bearer '+g.TOKEN,''))
        await asyncio.wait_for(started.wait(),1);request.disconnected.set()
        with pytest.raises(HTTPException) as exc:await asyncio.wait_for(task,1)
        assert exc.value.status_code==408 and cancelled.is_set() and g.LIMIT._value==4
    asyncio.run(scenario())


@pytest.mark.parametrize('found',[True,False])
def test_cli_privacy_is_brief_and_never_modifies_or_sends_draft(tmp_path,monkeypatch,capsys,found):
    response,_=privacy_response(monkeypatch,found);row=response.json();env=credential(tmp_path)
    draft=tmp_path/'draft.txt';draft.write_text(TEXT);before=draft.read_bytes();calls=[]
    def local(path,payload,token):
        calls.append((path,payload));assert token==cli.read_token(env);return copy.deepcopy(row)
    monkeypatch.setattr(cli,'local_request',local)
    assert cli.main(['privacy',str(draft),'--env-file',str(env),'--fail-on-finding'])==(2 if found else 0)
    output=capsys.readouterr()
    assert calls==[('/v1/evaluate',{'text':TEXT,'origin_host':'manual-local','check_mode':'privacy'})]
    assert draft.read_bytes()==before and TEXT not in output.out+output.err
    assert cli.read_token(env) not in output.out+output.err
    assert row['assertion_id'] not in output.out and 'PS' not in output.out
    assert 'not changed your draft or sent it' in output.out
    assert len(output.out.splitlines())==4
    assert ('Possible personal details' in output.out)==found


def resign(row):
    """Mutation tests cover semantically wrong identities with valid digests."""
    p=row['evaluator']['preprocessing'];r=p['configuration']['redactor']
    digest=lambda value:hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),
        ensure_ascii=True,allow_nan=False).encode()).hexdigest()
    r['sha256']=digest({k:r[k] for k in ('version','configuration')})
    p['sha256']=digest({k:p[k] for k in ('version','configuration')})
    row['evaluator']['models']=[{'name':'presidio-redaction','sha256':r['sha256'],'revision':r['version']},
                              {'name':'gateway-pipeline','sha256':p['sha256'],'revision':p['version']}]


@pytest.mark.parametrize('fault',[
    'pipeline-digest','redactor-digest','gateway-source','normalization-source','normalization-data',
    'app','model_loader','requirements_lock','identity_contract','identity_builder',
    'calibration','model','extra-model','wrong-tag','abstention','signal','score',
    'extra-detail','private-category','duplicate-category','count-bool','zero-count','too-small-count',
])
def test_privacy_rejects_mismatched_or_private_evidence(monkeypatch,fault):
    response,_=privacy_response(monkeypatch);row=response.json();p=row['evaluator']['preprocessing']
    if fault=='pipeline-digest':p['sha256']='0'*64
    elif fault=='redactor-digest':p['configuration']['redactor']['sha256']='0'*64
    elif fault in ('gateway-source','normalization-source','normalization-data'):
        key={'gateway-source':'gateway_source_sha256','normalization-source':'normalization_source_sha256','normalization-data':'normalization_data_sha256'}[fault]
        p['configuration'][key]='0'*64;resign(row)
    elif fault in p['configuration']['redactor']['configuration']['sources']:
        p['configuration']['redactor']['configuration']['sources'][fault]='0'*64;resign(row)
    elif fault=='calibration':row['evaluator']['calibration_id']='uncalibrated-rules-v6'
    elif fault=='model':row['evaluator']['models'][0]['sha256']='0'*64
    elif fault=='extra-model':row['evaluator']['models'].append({'name':'rogue','sha256':'0'*64,'revision':'1'})
    elif fault=='wrong-tag':row['tags'][0]['code']='PS'
    elif fault=='abstention':row['abstentions']=[{'code':'HP','confidence':1.,'floor':None,'reason':'not_in_production_allowlist'}]
    else:
        s=row['tags'][0]['signals'][0];d=s['detail']
        if fault=='signal':s['id']='rogue.observation.v1'
        elif fault=='score':s['score']=.9
        elif fault=='extra-detail':d['text']=TEXT
        elif fault=='private-category':d['entities']=[TEXT]
        elif fault=='duplicate-category':d['entities']*=2;d['count']=2
        elif fault=='count-bool':d['count']=True
        elif fault=='zero-count':d['count']=0
        elif fault=='too-small-count':d['entities'].append('PHONE_NUMBER')
    with pytest.raises((cli.LocalCheckError,ValueError)):
        cli.validate_result(row,privacy=True)


def test_json_export_is_explicit_and_excludes_draft(monkeypatch,tmp_path,capsys):
    response,_=privacy_response(monkeypatch);env=credential(tmp_path);draft=tmp_path/'draft.txt';draft.write_text(TEXT)
    monkeypatch.setattr(cli,'local_request',lambda *a,**kw:response.json())
    assert cli.main(['privacy',str(draft),'--env-file',str(env),'--json'])==0
    output=capsys.readouterr().out
    assert TEXT not in output and cli.read_token(env) not in output
    assert json.loads(output)['evaluator']['calibration_id']=='procedural-redaction-v1'


def test_saved_privacy_record_repeats_only_the_privacy_route(monkeypatch):
    from protocol.replay import replay,inspect_record
    response,_=privacy_response(monkeypatch);row=response.json();calls=[]
    assert inspect_record(row) is None
    def handle(req):
        body=json.loads(req.content);calls.append(body)
        assert body['check_mode']=='privacy' and body['text']==TEXT
        return httpx.Response(200,json=row)
    result=replay(row,TEXT,'synthetic-private-test-credential',transport=httpx.MockTransport(handle))
    assert result['status']=='matched' and result['signature_verified'] is False
    assert len(calls)==1


def test_bad_saved_privacy_record_never_transmits_original(monkeypatch):
    from protocol.replay import replay
    response,_=privacy_response(monkeypatch);row=response.json()
    row['tags'][0]['signals'][0]['detail']['text']=TEXT
    result=replay(row,TEXT,'synthetic-private-test-credential',transport=httpx.MockTransport(
        lambda req:pytest.fail('Unaccepted privacy record sent original input')))
    assert result['status']=='invalid' and result['reason']=='inconsistent_privacy_evidence'
