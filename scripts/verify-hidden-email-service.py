#!/usr/bin/env python3
"""Exercise fixed synthetic requests inside an isolated, source-bound Linux redactor.

Mount this script and current app.py read-only into the pinned redactor image.
Input is the expected source-digest map, never user text. No service port opens.
"""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys


def main():
    report={'pass':False,'kind':'isolated_redactor_asgi_regressions',
            'real_user_data':False,'independent_accuracy_evidence':False,
            'production_services_modified':False,'network_http_route':False}
    stage='execution_boundary'
    try:
        if sys.platform!='linux' or os.geteuid()!=10001:
            raise ValueError('Isolated Linux identity required')
        status=Path('/proc/self/status').read_text()
        if ('NoNewPrivs:\t1' not in status or
            int(next(l.split()[1] for l in status.splitlines() if l.startswith('CapEff:')),16)!=0 or
            set(os.listdir('/sys/class/net'))!={'lo'}):
            raise ValueError('Isolated execution boundary required')
        raw=sys.stdin.buffer.read(20001)
        if len(raw)>20000:raise ValueError('Diagnostic input bound')
        expected=json.loads(raw)
        names={'app':'app.py','model_loader':'model_identity.py','requirements_lock':'requirements.lock',
               'identity_contract':'protocol/replay_identity.py','identity_builder':'replay_metadata.py'}
        def identities():
            return {k:hashlib.sha256((Path('/app')/n).read_bytes()).hexdigest() for k,n in names.items()}
        if expected!=identities():raise ValueError('Sources differ')
        stage='service_startup'
        sys.path.insert(0,'/app')
        import app
        from fastapi.testclient import TestClient
        from protocol.http_privacy import application
        if app.REDACTOR_IDENTITY['configuration']['sources']!=expected:
            raise ValueError('Loaded source identity differs')
        cases=[]
        masking=[]
        applied=[]
        original_operate=app.anonymizer._operate
        def observe_operation(*args,**kwargs):
            nonlocal applied
            applied=[(r.start,r.end) for r in kwargs['pii_entities']]
            return original_operate(*args,**kwargs)
        app.anonymizer._operate=observe_operation
        with TestClient(application(),raise_server_exceptions=False) as client:
            def check(name,response,status_code):
                if (response.status_code!=status_code or
                    response.headers.get('cache-control')!='no-store' or
                    response.headers.get('x-content-type-options')!='nosniff'):
                    raise ValueError('HTTP contract failed')
                cases.append(name)
            for index,separator in enumerate(['\u200b','\u200c','\u200d','\ufeff']):
                for position in (2,5,10):
                    stage=f'email_{index}_{position}'
                    address='pilot@example.com'
                    text='Email '+address[:position]+separator+address[position:]+'.'
                    applied=[]
                    response=client.post('/redact',json={'text':text})
                    check(f'email_{index}_{position}',response,200)
                    value=response.json()
                    stage=f'email_{index}_{position}_mask'
                    wanted=set(range(6,len(text)-1))
                    masked={i for start,end in applied for i in range(start,end)}
                    remaining=len(wanted-masked)
                    extra=len(masked-wanted)
                    masking.append({'case_id':f'email_{index}_{position}',
                                    'unmasked_expected_characters':remaining,
                                    'masked_outside_expected_characters':extra})
                    if remaining or text[6:-1] in value['text']:
                        raise ValueError('Complete masking failed')
                    stage=f'email_{index}_{position}_entity'
                    if 'EMAIL_ADDRESS' not in value['entities']:
                        raise ValueError('Email evidence missing')
                    stage=f'email_{index}_{position}_identity'
                    if value['identity']!=app.REDACTOR_IDENTITY:
                        raise ValueError('Identity differs')
            stage='ordinary_email'
            response=client.post('/redact',json={'text':'Email pilot@example.com.'})
            check('ordinary_email',response,200)
            if response.json()['text']!='Email <EMAIL_ADDRESS>.':raise ValueError('Ordinary email changed')
            stage='benign_text'
            text='This is an ordinary fictional answer with no identifiers.'
            response=client.post('/redact',json={'text':text});check('benign_text',response,200)
            if response.json()['text']!=text:raise ValueError('Benign text changed')
            marker='INVENTED_PRIVATE_MARKER'
            for name,value in [('wrong_type',{'text':{'value':marker}}),
                               ('extra_field',{'text':'Example','extra':marker}),
                               ('too_long',{'text':'x'*200001})]:
                stage=name
                response=client.post('/redact',json=value);check(name,response,422)
                if marker in response.text:raise ValueError('Error reflected input')
            stage='invalid_json'
            response=client.post('/redact',content=b'{"text":"INVENTED_PRIVATE_MARKER"',
                                 headers={'content-type':'application/json'})
            check('invalid_json',response,422)
            if marker in response.text:raise ValueError('Malformed input reflected')
            stage='body_limit'
            response=client.post('/redact',content=b'x'*1250001,
                                 headers={'content-type':'application/json'})
            check('body_limit',response,413)
            stage='unsupported_method'
            check('unsupported_method',client.get('/redact'),405)
            stage='health'
            response=client.get('/healthz');check('health',response,200)
            if response.json().get('ok') is not True:raise ValueError('Health failed')
        stage='final_identity_and_coverage'
        app.anonymizer._operate=original_operate
        if expected!=identities() or len(cases)!=21 or len(set(cases))!=21:
            raise ValueError('Incomplete or stale diagnostic')
        report.update(pass_=True,source_sha256=expected,case_ids=cases,requests_exercised=len(cases),
                      source_unchanged=True,uid=10001,network='none',capabilities_empty=True,
                      no_new_privileges=True,masking_observations=masking,
                      cases_with_extra_masking=sum(r['masked_outside_expected_characters']>0 for r in masking),
                      probe_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
        report['pass']=report.pop('pass_')
    except Exception as error:
        # Only fixed diagnostic text is used; still keep exception bodies private.
        report.update(failed_stage=stage,error_type=type(error).__name__)
        print('Hidden-email service diagnostic failed.',file=sys.stderr)
    report['captured_at']=datetime.now(timezone.utc).isoformat()
    print(json.dumps(report))
    return 0 if report['pass'] else 1


if __name__=='__main__':raise SystemExit(main())
