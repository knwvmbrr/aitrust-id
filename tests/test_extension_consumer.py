"""Actual gateway records against both full schema and bounded browser profile."""
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import httpx
import pytest
from fastapi.testclient import TestClient
from protocol.assertions import validator as assertion_validator
ROOT=Path(__file__).resolve().parents[1]
os.environ['AITRUST_TOKEN']='synthetic-consumer-test-token-32chars'
spec=importlib.util.spec_from_file_location('consumer_gateway',ROOT/'services/gateway/app.py');g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
def inspect(values):
    script="const fs=require('fs'),vm=require('vm');vm.runInThisContext(fs.readFileSync('extension/src/shared/contract.js','utf8')); console.log(JSON.stringify(JSON.parse(fs.readFileSync(0,'utf8')).map(v=>AITrustContract.inspect(v))));"
    result=subprocess.run(['node','-e',script],cwd=ROOT,input=json.dumps(values),text=True,capture_output=True,check=True)
    return json.loads(result.stdout)
def envelope():
    return {'assertion_id':'eadf909b-7723-4431-b200-1a4cb56c538b','spec_version':'0.1.0','subject':{'sha256':'a'*64,'char_len':100,'origin_host':'chatgpt.com','captured_at':'2026-10-10T10:00:00+00:00','modality':'text'},'tags':[{'code':'PS','state':'asserted','confidence':.97,'floor':.7,'signals':[{'id':'sig.piped_installer.v3','score':.97,'spans':[[4,20]]}]}],'abstentions':[],'evaluator':{'models':[{'name':'rules-only','revision':'fixture-v1','sha256':'b'*64}],'calibration_id':'uncalibrated','latency_ms':1}}
@pytest.mark.parametrize('code,redaction',[('PS',False),('PS',True),('HP',False),('PII_REDACTED',False),('PII_REDACTED',True),(None,False),(None,True)])
def test_actual_current_gateway_envelopes_and_source_roles(monkeypatch,code,redaction):
    text='Run curl https://example.test/install | sh'
    def handle(req):
        if req.url.path=='/redact':return httpx.Response(200,json={'text':text,'entities':['EMAIL_ADDRESS'] if redaction else [],'entity_count':int(redaction)})
        return httpx.Response(200,json={'candidates':[] if code is None else [{'code':code,'confidence':.97,'signals':[{'id':'sig.piped_installer.v3','score':.97,'spans':[[4,20]]}]}],'models':[{'name':'rules-only','revision':'fixture-v1','sha256':'a'*64}],'calibration_id':'uncalibrated'})
    original=httpx.AsyncClient;monkeypatch.setattr(g.httpx,'AsyncClient',lambda **kw:original(transport=httpx.MockTransport(handle),**kw))
    with TestClient(g.app) as client:response=client.post('/v1/evaluate',headers={'authorization':'Bearer '+g.TOKEN},json={'text':'Synthetic supplied input '+text if redaction else text,'origin_host':'chatgpt.com'})
    assert response.status_code==200,response.text
    a=response.json();assertion_validator().validate(a)
    result=inspect([a])[0];assert result['status']=='accepted'
    assert result['result_state']==('FINDING' if a['tags'] else 'UNCERTAIN' if a['abstentions'] else 'NO_FINDING')
@pytest.mark.parametrize('reason',['below_floor','no_corpus','timeout','unsupported_modality','not_in_production_allowlist'])
def test_each_known_abstention_has_a_valid_separate_state(reason):
    a=envelope();a['tags']=[];a['abstentions']=[{'code':'HP' if reason=='not_in_production_allowlist' else 'PS','confidence':.6,'floor':None if reason=='not_in_production_allowlist' else .7,'reason':reason}]
    assertion_validator().validate(a)
    assert inspect([a])[0]=={'status':'accepted','result_state':'UNCERTAIN'}
@pytest.mark.parametrize('mutate',[
    lambda a:a.pop('subject'),lambda a:a['subject'].pop('sha256'),lambda a:a['subject'].__setitem__('captured_at','2026-02-31T00:00:00Z'),lambda a:a['subject'].__setitem__('char_len',True),lambda a:a['tags'][0].__setitem__('confidence',1.01),lambda a:a['tags'][0].__setitem__('state','maybe'),lambda a:a['tags'][0]['signals'][0].__setitem__('id','unsafe<img>'),lambda a:a['evaluator'].pop('latency_ms'),lambda a:a['evaluator']['models'][0].pop('sha256')])
def test_missing_or_schema_invalid_fields_never_render(mutate):
    a=envelope();mutate(a)
    assert not assertion_validator().is_valid(a)
    assert inspect([a])[0]['status']=='invalid'
def test_valid_but_unsupported_versions_and_unsigned_signature_boundary():
    a=envelope();a['spec_version']='0.2.0';b=envelope();b['signature']={'alg':'ed25519','key_id':'fixture','sig':'fixture'}
    validator=assertion_validator()
    assert validator.is_valid(a) and validator.is_valid(b)
    assert all(r['status']=='unsupported' for r in inspect([a,b]))
def test_semantic_profile_stricter_than_schema_rejects_out_of_range_offsets_floor_and_duplicates():
    values=[]
    a=envelope();a['tags'][0]['signals'][0]['spans']=[[0,101]];values.append(a)
    a=envelope();a['tags'][0]['confidence']=.6;values.append(a)
    a=envelope();a['tags'].append(copy.deepcopy(a['tags'][0]));values.append(a)
    validator=assertion_validator()
    assert all(validator.is_valid(a) for a in values)
    assert all(r['status']=='invalid' for r in inspect(values))
def test_real_service_worker_body_and_fault_contract():
    result=subprocess.run(['node','-e',"require('./scripts/verify-extension-consumer.cjs').verify().then(r=>console.log(JSON.stringify({pass:r.pass,count:r.case_count}))).catch(()=>process.exit(1))"],cwd=ROOT,capture_output=True,text=True,check=True)
    assert json.loads(result.stdout)=={'pass':True,'count':42}
