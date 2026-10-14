#!/usr/bin/env python3
"""Actual loopback HTTP to private synthetic PostgreSQL; never participant intake."""
import argparse
import base64
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from protocol.reports import write_report
from tools.research_admission import PROFILE, FIXED, CHOICES, digest_token

NAMES = ['services/research/app.py', 'services/research/worker.py', 'tests/test_research_http.py',
    'scripts/verify-research-http.py', 'scripts/metadata-store-sandbox.py',
    'scripts/research-admission.py', 'scripts/verify-metadata-store.py', 'scripts/worker_process.py',
    'tools/research_admission.py', 'tools/blind_review_io.py',
    'deploy/research/metadata-development.sql', 'deploy/research/metadata-invitation-development.sql']


def inventory(): return {name: hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in NAMES}
def token(n): return base64.urlsafe_b64encode(n.to_bytes(32, 'big')).decode().rstrip('=')
CAPABILITY = token(900)  # Public invented fixture, never a real pilot credential.


def guard(path):
    spec = importlib.util.spec_from_file_location('http_sandbox_guard', ROOT/'scripts/verify-metadata-store.py')
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module.sandbox(path)


def verify(path):
    directory = guard(path); before = inventory(); cases = []
    command = ['/usr/lib/postgresql/18/bin/psql', '-XqAtw', '-v', 'ON_ERROR_STOP=1',
        '-h', str(directory/'socket'), '-p', '55443', '-d', 'postgres']
    def sql(query):
        result = subprocess.run(command, input=("SET statement_timeout='5s';\n"+query).encode(),
            capture_output=True, env={'PATH':os.defpath, 'LANG':'C.UTF-8'}, timeout=12)
        if result.returncode or len(result.stdout)+len(result.stderr)>65536:
            raise ValueError('Synthetic HTTP storage control refused')
        return result.stdout.decode().strip()
    observed = json.loads(sql("SELECT json_build_object('data',current_setting('data_directory'),"
        "'socket',current_setting('unix_socket_directories'),'cluster',current_setting('cluster_name'),"
        "'listen',current_setting('listen_addresses'),'version',current_setting('server_version_num'),"
        "'tcp',inet_server_addr());"))
    if (observed.get('data') != str(directory/'data') or observed.get('socket') != str(directory/'socket')
            or observed.get('cluster') != 'aitrust-metadata-synthetic' or observed.get('listen') != ''
            or observed.get('tcp') is not None or not 180000 <= int(observed.get('version',0)) < 190000):
        raise ValueError('Synthetic HTTP database identity refused')
    sql((ROOT/'deploy/research/metadata-development.sql').read_text())
    sql((ROOT/'deploy/research/metadata-invitation-development.sql').read_text())
    digest = "decode('"+digest_token(token(901))+"','hex')"
    assert sql('SET ROLE ait_metadata_maintenance; SELECT metadata_dev.issue_invitation_synthetic('+digest+',2,3600);') == 't'
    with socket.socket() as selected:
        selected.bind(('127.0.0.1',0)); port = selected.getsockname()[1]
    worker = subprocess.Popen([sys.executable, str(Path(__file__).resolve()),
        '--sandbox-dir',str(directory),'--serve',str(port)], cwd=ROOT,
        env={'PATH':os.defpath,'LANG':'C.UTF-8'}, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    def request(value, capability=CAPABILITY):
        raw = value if type(value) is bytes else json.dumps(value).encode()
        req = urllib.request.Request('http://127.0.0.1:'+str(port)+'/v1/feedback',data=raw,
            headers={'Content-Type':'application/json','Authorization':'Bearer '+capability})
        try: response = opener.open(req,timeout=20)
        except urllib.error.HTTPError as error: response = error
        with response:
            payload = response.read(2049)
            assert len(payload)<=2048 and response.headers['Cache-Control']=='no-store'
            assert response.headers['X-Content-Type-Options']=='nosniff'
            assert b'PRIVATE_HTTP_CANARY' not in payload and CAPABILITY.encode() not in payload
            return response.status, json.loads(payload)
    def submit(n=902):
        return {'format':PROFILE,'synthetic':True,'operation':'submit','invitation_token':token(901),
            'withdrawal_token':token(n),'feedback':{**FIXED,**{key:values[0] for key,values in CHOICES.items()}}}
    try:
        deadline = time.monotonic()+10
        while True:
            assert worker.poll() is None, 'Synthetic HTTP process exited'
            try:
                assert request(b'{}', capability=token(999))[0]==400; break
            except OSError:
                assert time.monotonic()<deadline, 'Synthetic HTTP startup unavailable'
                time.sleep(.05)
        assert sql('SELECT count(*) FROM metadata_dev.feedback;')=='0'
        cases.append('actual_http_auth_refusal_without_insertion')
        status, first = request(submit()); assert status==200 and first['synthetic_only'] is True
        assert request(submit()) == (200,first)
        assert sql('SELECT count(*) FROM metadata_dev.feedback;')=='1'
        cases.append('actual_http_worker_database_roundtrip_and_idempotent_retry')
        changed = submit(); changed['feedback']['feedback']='hard_to_use'
        assert request(changed)[0]==503
        assert sql('SELECT used FROM metadata_dev.invitations WHERE digest='+digest+';')=='1'
        cases.append('conflicting_retry_does_not_consume_quota_or_overwrite')
        for value in (b'{', b'{"text":"PRIVATE_HTTP_CANARY"}', b'{"x":1,"x":2}', b'x'*4097):
            assert request(value)[0]==400
        assert sql('SELECT count(*) FROM metadata_dev.feedback;')=='1'
        cases.append('private_malformed_ambiguous_and_oversize_http_payloads_refused')
        assert request(submit(903))[0]==200
        assert request(submit(904))[0]==503
        assert sql('SELECT count(*) FROM metadata_dev.feedback;')=='2'
        cases.append('database_quota_enforced_through_actual_http')
        withdrawal = {'format':PROFILE,'synthetic':True,'operation':'withdraw','withdrawal_token':token(902)}
        assert request(withdrawal)[1]['removed'] is True
        assert request(withdrawal)[1]['removed'] is False
        assert request(submit())[0]==503
        assert sql('SELECT count(*) FROM metadata_dev.feedback;')=='1'
        cases.append('actual_http_withdrawal_is_idempotent_and_retry_cannot_resurrect')
        assert request(b'{}',capability=token(999))[0]==400
        assert request(withdrawal)[0]==200
        cases.append('service_recovers_after_refused_workers_and_requests')
    finally:
        worker.terminate()
        try: worker.wait(timeout=5)
        except subprocess.TimeoutExpired: worker.kill(); worker.wait(timeout=5)
    assert before==inventory()
    return {'captured_at':datetime.now(timezone.utc).isoformat(),'pass':True,'profile':'synthetic-research-http/v1',
        'sources':before,'source_unchanged_during_execution':True,'completed_cases':cases,
        'actual_loopback_http':True,'actual_postgresql':True,'worker_process_stopped':True,
        'only_synthetic_records':True,'public_listener_started':False,'collection_enabled':False,
        'participant_data_accepted':False,'production_database_changed':False,
        'independent_accuracy_evidence':False,'release_approved':False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sandbox-dir',required=True)
    parser.add_argument('--serve',type=int,help=argparse.SUPPRESS)
    parser.add_argument('--output')
    args = parser.parse_args()
    try:
        if args.serve is not None:
            directory = guard(args.sandbox_dir)
            from services.research.app import development_app
            import uvicorn
            app = development_app(directory,CAPABILITY,'127.0.0.1:'+str(args.serve))
            uvicorn.run(app,host='127.0.0.1',port=args.serve,access_log=False,log_level='critical',
                        proxy_headers=False,server_header=False,lifespan='off',limit_concurrency=8)
            return 0
        record = verify(args.sandbox_dir)
        if args.output: write_report(args.output,record)
        print(json.dumps(record)); return 0
    except (ValueError,OSError,AssertionError,subprocess.SubprocessError,ImportError):
        print('Synthetic HTTP verification refused; no production acceptance.',file=sys.stderr)
        return 1


if __name__=='__main__': raise SystemExit(main())
