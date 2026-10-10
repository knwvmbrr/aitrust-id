"""Synthetic real-HTTP faults against an explicitly disposable fixture stack."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
import json
from pathlib import Path
import socket
import time
import urllib.error,urllib.request

def verify(env_file,mode_file):
    if 'aitrust-staging' not in str(mode_file.resolve()) or not mode_file.is_file():
        raise ValueError('Dedicated staging control file required')
    rows=[s.split('=',1)[1] for s in env_file.read_text().splitlines() if s.startswith('AITRUST_TOKEN=')]
    if len(rows)!=1:raise ValueError('Private staging token required')
    token=rows[0];opener=urllib.request.build_opener(urllib.request.ProxyHandler({}));cases=[]
    def mode(name):mode_file.write_text(json.dumps({'mode':name}))
    def check(name,expected,timeout=25):
        body=json.dumps({'text':'Synthetic resource fixture.'}).encode()
        req=urllib.request.Request('http://127.0.0.1:8787/v1/evaluate',data=body,
            headers={'Authorization':'Bearer '+token,'Content-Type':'application/json'})
        begin=time.perf_counter()
        try:
            with opener.open(req,timeout=timeout) as r:status,raw=r.status,r.read()
        except urllib.error.HTTPError as r:status,raw=r.code,r.read()
        assert status==expected,name+' unexpected status'
        if status!=200:assert 'tags' not in json.loads(raw)
        assert token not in raw.decode()
        elapsed=round((time.perf_counter()-begin)*1000,2)
        cases.append({'name':name,'status':status,'elapsed_ms':elapsed,'pass':True})
        return elapsed
    mode('healthy');check('fixture_ready',200)
    for fault in ('malformed','unknown_code','bad_span'):
        mode(fault);check(fault,502)
        mode('healthy');check(fault+'_recovery',200)
    mode('slow');sockets=[]
    try:
        body=json.dumps({'text':'Synthetic resource fixture.'}).encode()
        headers=('POST /v1/evaluate HTTP/1.1\r\nHost: 127.0.0.1\r\nAuthorization: Bearer '+token+
                 '\r\nContent-Type: application/json\r\nContent-Length: '+str(len(body))+ '\r\nConnection: close\r\n\r\n').encode()
        for _ in range(4):
            connection=socket.create_connection(('127.0.0.1',8787),timeout=3)
            connection.sendall(headers+body);sockets.append(connection)
        time.sleep(.8)
        check('fifth_request_busy',503)
    finally:
        begin=time.perf_counter()
        for connection in sockets:connection.close()
        mode('healthy')
    check('disconnect_releases_capacity',200)
    recovery_ms=round((time.perf_counter()-begin)*1000,2)
    assert recovery_ms<2000,'Disconnected requests retained capacity'
    mode('slow')
    try:
        elapsed=check('dependency_timeout',504)
        assert 9000<elapsed<14000,'Declared upstream timeout not enforced'
    finally:mode('healthy')
    check('timeout_releases_capacity',200)
    return {'captured_at':datetime.now(timezone.utc).isoformat(),'pass':True,'fixture_is_not_a_detector':True,
            'cases':cases,'four_admitted_fifth_rejected':True,'disconnect_capacity_recovery_ms':recovery_ms,
            'upstream_work_already_received_may_continue':True,'independent_accuracy_evidence':False,
            'release_validated':False,'public_endpoint_created':False}
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--env-file',type=Path,required=True);p.add_argument('--mode-file',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    try:r=verify(a.env_file,a.mode_file)
    except Exception as error:
        r={'captured_at':datetime.now(timezone.utc).isoformat(),'pass':False,'error_type':type(error).__name__,'independent_accuracy_evidence':False}
        a.output.write_text(json.dumps(r,indent=2)+'\n');print('Fault checks failed; no acceptance granted.');raise SystemExit(1)
    a.output.write_text(json.dumps(r,indent=2)+'\n');print('Fault checks passed:',len(r['cases']),'scenarios; no accuracy claimed.')
