#!/usr/bin/env python3
"""Fixed candidate-engine and in-process ASGI checks; no service or network starts.

This is a NEW diagnostic worker. Only observe_cases is copied unchanged from
redaction-development-worker.py; it is not the whole historical abed worker.
Only the two immutable public synthetic fixtures are accepted as input.
"""
import asyncio
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import sys


def canonical(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()


ENGLISH_SHA='8794def090345dff3209f2feb1242edff8338d2f5dc890bccaa4a753c8ec962f'
COMPACT_SHA='94dcfb195ee24b56b626d15bbada73b9385d5cdebd1ac90a27d08b0a45953335'
APP_SHA='6c694b9debc2e28ae4e36b767597b28ff6633b220d7919ec979b32304c61760d'
MODEL_SHA='0de0a5285fed4ee53463a48f70886873802ef94135fa5afdfaeb30eda38cfda4'


def observe_cases(app,rows):
 output=[]
 original_operate=app.anonymizer._operate
 applied=[]
 def observe_operation(*args,**kwargs):
  nonlocal applied
  applied=[{'entity':r.entity_type,'start':r.start,'end':r.end} for r in kwargs['pii_entities']]
  return original_operate(*args,**kwargs)
 app.anonymizer._operate=observe_operation
 try:
  for row in rows:
   findings=app.analyzer.analyze(text=row['text'],language='en',score_threshold=0.0)
   # Presidio may mutate these objects while merging anonymization conflicts.
   predicted=[{'entity':r.entity_type,'start':r.start,'end':r.end} for r in findings]
   applied=[]
   redacted=app.anonymizer.anonymize(text=row['text'],analyzer_results=findings)
   output.append({'id':row['id'],'predicted':predicted,
    'applied':applied,'redaction_changed':redacted.text!=row['text'],'expected_literal_values_still_present':sum(row['text'][r['start']:r['end']] in redacted.text for r in row['expected'])})
 finally:
  app.anonymizer._operate=original_operate
 return output

def coverage(row, observed):
    wanted={i for span in row['expected']for i in range(span['start'],span['end'])}
    applied=set()
    for item in observed['applied']:
        start,end=item['start'],item['end']
        if type(start)is not int or type(end)is not int or not 0<=start<end<=len(row['text']):
            raise ValueError('Invalid applied source coordinates')
        applied.update(range(start,end))
    return {'id':row['id'],'expected_characters':len(wanted),
            'unmasked_expected_characters':len(wanted-applied),
            'masked_outside_expected_characters':len(applied-wanted)}


async def asgi_checks(module,report):
    if importlib.metadata.version('httpx')!='0.28.1':
        raise ValueError('Installed HTTP client identity differs')
    privacy=Path('/app/protocol/http_privacy.py').read_bytes()
    if hashlib.sha256(privacy).hexdigest()!='6151d7bf923cb6613c8615c15ee27706bdd0b8aa6c4015db0e40886a90168807':
        raise ValueError('HTTP privacy source differs')
    import httpx
    from protocol.http_privacy import application
    original_analyze=module.analyzer.analyze
    original_operate=module.anonymizer._operate
    seen=[];applied=[];calls=0;rows=[]
    report['asgi']=rows
    def analyze(*args,**kwargs):
        nonlocal seen,calls
        calls+=1;seen=original_analyze(*args,**kwargs)
        return seen
    def operate(*args,**kwargs):
        nonlocal applied
        applied=[{'entity':r.entity_type,'start':r.start,'end':r.end}for r in kwargs['pii_entities']]
        return original_operate(*args,**kwargs)
    module.analyzer.analyze=analyze;module.anonymizer._operate=operate
    try:
        transport=httpx.ASGITransport(app=application(),raise_app_exceptions=False)
        async with httpx.AsyncClient(transport=transport,base_url='http://probe.invalid')as client:
            async def request(case_id,*,text=None,status=200,wanted=None,unchanged=False,no_email=False,method='POST',raw=None,json_body=None):
                nonlocal seen,applied,calls
                report['http_stage']=case_id
                seen=[];applied=[];calls=0
                kwargs={'json':{'text':text}}if text is not None else ({'json':json_body}if json_body is not None else {})
                if raw is not None:kwargs={'content':raw,'headers':{'content-type':'application/json'}}
                response=await client.request(method,'/healthz'if case_id=='health'else'/redact',**kwargs)
                if (response.status_code!=status or response.headers.get('cache-control')!='no-store'
                        or response.headers.get('x-content-type-options')!='nosniff'):
                    raise ValueError('HTTP response contract differs')
                row={'id':case_id,'status':response.status_code,'private_headers':True}
                if text is not None and status==200:
                    value=response.json()
                    if set(value)!={'text','entities','entity_count','identity'}or value['identity']!=module.REDACTOR_IDENTITY:
                        raise ValueError('HTTP result identity differs')
                    if (type(value['entity_count'])is not int or value['entity_count']!=len(seen)
                            or value['entities']!=sorted({r.entity_type for r in seen})or calls!=1):
                        raise ValueError('HTTP entity metadata differs')
                    wanted=wanted or []
                    item={'id':case_id,'text':text,'expected':[{'start':start,'end':end}for start,end in wanted]}
                    measured=coverage(item,{'applied':applied});row.update(measured)
                    row['changed']=value['text']!=text;row['entity_count']=value['entity_count']
                    row['email_observed']='EMAIL_ADDRESS'in value['entities']
                    row['identity_matches']=True
                    if wanted and (measured['unmasked_expected_characters']or any(text[start:end]in value['text']for start,end in wanted)
                                   or not row['email_observed']):
                        raise ValueError('HTTP expected email coverage differs')
                    if unchanged and (value['text']!=text or value['entity_count']!=0 or applied):
                        raise ValueError('Benign HTTP control changed')
                    if no_email and row['email_observed']:
                        raise ValueError('Rejected form became an email')
                elif case_id=='health':
                    value=response.json()
                    if value.get('ok')is not True or value.get('model_identity')!=module.MODEL_IDENTITY:
                        raise ValueError('HTTP health identity differs')
                    row['model_identity_matches']=True
                elif status>=400:
                    if calls or applied or 'INVENTED_PRIVATE_MARKER'in response.text or 'x'*64 in response.text:
                        raise ValueError('Invalid HTTP input was processed or reflected')
                    row['input_processed']=False;row['input_reflected']=False
                rows.append(row)
            value='pilot [at] example [dot] org'
            text='Contact '+value+'.'
            await request('bracket_original',text=text,wanted=[(8,8+len(value))])
            prefix='Ω 😀 ';text=prefix+value+'.'
            await request('bracket_unicode_context',text=text,wanted=[(len(prefix),len(prefix)+len(value))])
            value='PILOT[AT]EXAMPLE[DOT]ORG'
            await request('bracket_marker_case',text=value,wanted=[(0,len(value))])
            first='one [at] example [dot] org';second='two [at] example [dot] org'
            text=first+'; '+second+'.'
            await request('two_addresses',text=text,wanted=[(0,len(first)),(len(first)+2,len(first)+2+len(second))])
            await request('benign_text',text='This is an ordinary fictional answer with no identifiers.',unchanged=True)
            await request('benign_markers',text='[at] and [dot] are markers.',no_email=True)
            await request('invalid_suffix',text='pilot [at] example [dot] invalidsuffix',no_email=True)
            marker='INVENTED_PRIVATE_MARKER'
            await request('wrong_type',json_body={'text':{'value':marker}},status=422)
            await request('extra_field',json_body={'text':'Example','extra':marker},status=422)
            await request('too_long',json_body={'text':'x'*200001},status=422)
            await request('invalid_json',raw=b'{"text":"INVENTED_PRIVATE_MARKER"',status=422)
            await request('body_limit',raw=b'x'*1250001,status=413)
            await request('unsupported_method',method='GET',status=405)
            await request('health',method='GET')
    finally:
        module.analyzer.analyze=original_analyze
        module.anonymizer._operate=original_operate
    if len(rows)!=14 or len({r['id']for r in rows})!=14:
        raise ValueError('Incomplete fixed HTTP cohort')
    return rows


def main():
    report={'kind':'isolated_bracketed_email_development','pass':False,
            'real_user_data':False,'independent_accuracy_evidence':False,
            'production_services_modified':False,'network_http_route':False,
            'recognizer_override':False}
    stage='execution_boundary'
    try:
        if sys.platform!='linux'or os.getuid()!=10001 or set(os.listdir('/sys/class/net'))!={'lo'}:
            raise ValueError('Isolated runtime required')
        status=Path('/proc/self/status').read_text()
        fields=dict(line.split(':',1)for line in status.splitlines()if ':'in line)
        if int(fields['CapEff'].strip(),16)or int(fields['CapBnd'].strip(),16)or int(fields['NoNewPrivs'].strip())!=1:
            raise ValueError('Isolated privileges required')
        raw=sys.stdin.buffer.read(2000001)
        if len(raw)>2000000:raise ValueError('Fixed diagnostic input bound')
        payload=json.loads(raw)
        if set(payload)!={'sources','fixtures'}or set(payload['fixtures'])!={'english','compact'}:
            raise ValueError('Fixed diagnostic input differs')
        english,compact=payload['fixtures']['english'],payload['fixtures']['compact']
        if canonical(english)!=ENGLISH_SHA or canonical(compact)!=COMPACT_SHA:
            raise ValueError('Fixed diagnostic fixtures differ')
        if len(english['rows'])!=42 or len(compact['rows'])!=6:
            raise ValueError('Fixed diagnostic counts differ')
        expected=payload['sources']
        paths={'app':'app.py','model_loader':'model_identity.py','requirements_lock':'requirements.lock',
               'identity_contract':'protocol/replay_identity.py','identity_builder':'replay_metadata.py'}
        def hashes():return {key:hashlib.sha256((Path('/app')/path).read_bytes()).hexdigest()for key,path in paths.items()}
        if expected!=hashes()or expected['app']!=APP_SHA:
            raise ValueError('Candidate sources differ')
        stage='model_verification_before_application'
        sys.path.insert(0,'/app')
        import model_identity
        verified=model_identity.verify_installed()
        if verified['manifest_sha256']!=MODEL_SHA or verified['verified_before_load']is not True:
            raise ValueError('Candidate model differs')
        stage='engine_startup'
        import app
        if app.REDACTOR_IDENTITY['configuration']['sources']!=expected:
            raise ValueError('Loaded source identity differs')
        report.update(model_identity=verified,sources=expected,redactor_identity=app.REDACTOR_IDENTITY)
        stage='english_engine'
        rows=observe_cases(app,english['rows']);report['rows']=rows
        stage='compact_engine'
        compact_rows=observe_cases(app,compact['rows']);report['compact_rows']=compact_rows
        english_masking=[coverage(row,observed)for row,observed in zip(english['rows'],rows)]
        compact_masking=[coverage(row,observed)for row,observed in zip(compact['rows'],compact_rows)]
        report.update(english_masking=english_masking,compact_masking=compact_masking)
        wanted=next(row for row in english_masking if row['id']=='challenge_obfuscated_email')
        if wanted['unmasked_expected_characters']or wanted['masked_outside_expected_characters']:
            raise ValueError('Known bracketed challenge remains unmasked or overmasked')
        if any(row['unmasked_expected_characters']or row['masked_outside_expected_characters']for row in compact_masking):
            raise ValueError('Compact controls changed')
        stage='asgi_http'
        http=asyncio.run(asgi_checks(app,report))
        stage='final_source_identity'
        after=hashes();report['source_sha256_after']=after
        if after!=expected:raise ValueError('Candidate source changed during execution')
        report.update(rows=rows,compact_rows=compact_rows,english_masking=english_masking,
                      compact_masking=compact_masking,asgi=http,redactor_identity=app.REDACTOR_IDENTITY,
                      model_identity=verified,sources=expected,source_unchanged=True,
                      fixture_sha256={'english':ENGLISH_SHA,'compact':COMPACT_SHA},
                      privacy_module_sha256='6151d7bf923cb6613c8615c15ee27706bdd0b8aa6c4015db0e40886a90168807')
        report['pass']=True
    except Exception as error:
        report.update(failed_stage=stage,error_type=type(error).__name__)
        print('Fixed bracketed-email diagnostic failed.',file=sys.stderr)
    report['captured_at']=datetime.now(timezone.utc).isoformat()
    print(json.dumps(report))
    return 0 if report['pass']else 1


if __name__=='__main__':raise SystemExit(main())
