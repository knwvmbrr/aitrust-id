"""Authenticated local orchestration. Only redacted text is forwarded to evaluation."""
import asyncio
import hashlib
import hmac
import os
import time
import unicodedata
import uuid
from datetime import datetime, timezone
from typing import Literal

import httpx
from fastapi import FastAPI, Header, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator
from starlette.middleware.body_limit import RequestBodyLimitMiddleware

SPEC_VERSION='0.1.0'
TOKEN=os.environ['AITRUST_TOKEN']
if TOKEN == 'change-me' or len(TOKEN)<16:
    raise RuntimeError('AITRUST_TOKEN must be a generated secret of at least 16 characters')
ANONYMIZER=os.environ.get('ANONYMIZER_URL','http://anonymizer:8000')
EVALUATOR=os.environ.get('EVALUATOR_URL','http://evaluator:8000')
PRODUCTION_TAGS=frozenset({'PS','PII_REDACTED'})
KNOWN_CODES=frozenset({'NF','FI','HP','MT','PS','IV','FA','PA','UNK','PII_REDACTED'})
FLOORS={'PS':.70}
LIMIT=asyncio.Semaphore(4)
app=FastAPI(title='AITrust-ID Gateway',version=SPEC_VERSION)
app.add_middleware(RequestBodyLimitMiddleware,max_body_size=1_250_000)

class StrictModel(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True)
class EvalRequest(StrictModel):
    text:str=Field(min_length=1,max_length=200_000)
    origin_host:str=Field(default='unknown',max_length=253)
    modality:Literal['text','code','image','audio','video','document']='text'
class Redaction(StrictModel):
    text:str=Field(max_length=200_000)
    # Entity values never belong in an assertion. This is the inspected English
    # recognizer category contract, not an arbitrary redactor-supplied string.
    entities:list[Literal['AGE','AU_ABN','AU_ACN','AU_MEDICARE','AU_TFN',
        'CREDIT_CARD','CRYPTO','DATE_TIME','EMAIL','EMAIL_ADDRESS','IBAN_CODE',
        'ID','IN_AADHAAR','IN_PAN','IN_PASSPORT','IN_VEHICLE_REGISTRATION',
        'IN_VOTER','IP_ADDRESS','LOCATION','MEDICAL_LICENSE','NRP','ORGANIZATION',
        'PERSON','PHONE_NUMBER','SG_NRIC_FIN','UK_NHS','URL','US_BANK_NUMBER',
        'US_DRIVER_LICENSE','US_ITIN','US_PASSPORT','US_SSN']]=Field(max_length=32)
    entity_count:int=Field(ge=0,le=200_000)

    @model_validator(mode='after')
    def consistent_categories(self):
        if len(set(self.entities)) != len(self.entities):
            raise ValueError('Duplicate redaction category')
        if bool(self.entities) != bool(self.entity_count) or len(self.entities)>self.entity_count:
            raise ValueError('Inconsistent redaction categories/count')
        return self
class Signal(StrictModel):
    id:str=Field(pattern=r'^[a-z0-9_.]+\.v\d+$')
    score:float=Field(ge=0,le=1)
    spans:list[list[int]]
class Candidate(StrictModel):
    code:str
    confidence:float=Field(ge=0,le=1)
    signals:list[Signal]=Field(min_length=1)
class Model(StrictModel):
    name:str
    sha256:str=Field(pattern='^[a-f0-9]{64}$')
    revision:str
class Evaluation(StrictModel):
    candidates:list[Candidate]
    models:list[Model]
    calibration_id:str

async def post_validated(client,url,payload,model):
    response=await client.post(url,json=payload)
    response.raise_for_status()
    return model.model_validate(response.json())

@app.get('/healthz')
async def healthz():
    try:
        async with httpx.AsyncClient(timeout=2,trust_env=False) as client:
            for url in (ANONYMIZER,EVALUATOR):
                response=await client.get(url+'/healthz')
                response.raise_for_status()
                if response.json().get('ok') is not True:
                    raise ValueError('not ready')
    except (httpx.HTTPError,ValueError):
        raise HTTPException(503,'Local dependencies are unavailable')
    return {'ok':True,'spec_version':SPEC_VERSION}

@app.post('/v1/evaluate')
async def evaluate(req:EvalRequest,request:Request,authorization:str=Header(default=''),origin:str=Header(default='')):
    if not hmac.compare_digest(authorization.encode(),f'Bearer {TOKEN}'.encode()):
        raise HTTPException(401,'Invalid local token')
    if origin and not origin.startswith('chrome-extension://'):
        raise HTTPException(403,'Browser page requests are not permitted')
    if req.modality!='text':
        raise HTTPException(422,'Unsupported modality; only text is currently evaluated')
    t0=time.perf_counter()
    try:
        await asyncio.wait_for(LIMIT.acquire(),timeout=.1)
    except TimeoutError:
        raise HTTPException(503,'Evaluator is busy; retry later')
    work=disconnect=None
    async def pipeline():
        async with httpx.AsyncClient(timeout=10,trust_env=False) as client:
            normalized=unicodedata.normalize('NFC',req.text)
            red=await post_validated(client,ANONYMIZER+'/redact',{'text':normalized},Redaction)
            red.text=unicodedata.normalize('NFC',red.text)
            if red.entity_count and red.text==normalized:
                raise ValueError('Redactor reports detections without changing text')
            ev=await post_validated(client,EVALUATOR+'/signals',{'text':red.text},Evaluation)
        return red,ev
    async def watch_disconnect():
        # FastAPI has already consumed the validated body. Wait for the next
        # ASGI disconnect event directly; polling is_disconnected() uses its own
        # cancellation scope and can swallow task cancellation during cleanup.
        while True:
            message=await request.receive()
            if message['type']=='http.disconnect':return
    try:
        work=asyncio.create_task(pipeline())
        disconnect=asyncio.create_task(watch_disconnect())
        completed,_=await asyncio.wait((work,disconnect),return_when=asyncio.FIRST_COMPLETED)
        if work not in completed:
            raise HTTPException(408,'Client disconnected before a result was available')
        red,ev=await work
        for candidate in ev.candidates:
            for signal in candidate.signals:
                for span in signal.spans:
                    if len(span)!=2 or not 0<=span[0]<span[1]<=len(red.text):
                        raise ValueError('Invalid evidence offsets')
        tags,abstentions=calibrate([c.model_dump() for c in ev.candidates])
    except httpx.TimeoutException:
        raise HTTPException(504,'Local evaluation timed out')
    except (httpx.HTTPError,ValidationError,ValueError):
        raise HTTPException(502,'Local dependency returned an invalid evaluation')
    finally:
        tasks=[task for task in (work,disconnect) if task is not None]
        for task in tasks:
            if not task.done():task.cancel()
        await asyncio.gather(*tasks,return_exceptions=True)
        LIMIT.release()
    if red.entity_count:
        tags.append({'code':'PII_REDACTED','confidence':1.,'state':'asserted','signals':[{'id':'presidio.entity.v1','score':1.,'detail':{'entities':red.entities,'count':red.entity_count}}]})
    return {'assertion_id':str(uuid.uuid4()),'spec_version':SPEC_VERSION,'subject':{'sha256':hashlib.sha256(red.text.encode()).hexdigest(),'char_len':len(red.text),'origin_host':req.origin_host,'captured_at':datetime.now(timezone.utc).isoformat(),'modality':req.modality},'tags':tags,'abstentions':abstentions,'evaluator':{'models':[m.model_dump() for m in ev.models],'calibration_id':ev.calibration_id,'latency_ms':round((time.perf_counter()-t0)*1000,1)}}

def calibrate(candidates):
    """Only PS can assert from the evaluator; the redactor owns PII assertions."""
    tags, abstentions = [], []
    for candidate in candidates:
        code = candidate['code']
        if code not in KNOWN_CODES:
            raise ValueError('Unrecognized evaluator candidate code')
        if code != 'PS':
            abstentions.append({'code': code, 'confidence': candidate['confidence'],
                               'floor': None, 'reason': 'not_in_production_allowlist'})
            continue
        floor = FLOORS[code]
        if candidate['confidence'] >= floor:
            tags.append({'code': code, 'confidence': candidate['confidence'],
                         'floor': floor, 'state': 'asserted', 'signals': candidate['signals']})
        else:
            abstentions.append({'code': code, 'confidence': candidate['confidence'],
                               'floor': floor, 'reason': 'below_floor'})
    return tags, abstentions
