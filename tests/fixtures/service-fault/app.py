"""Disposable upstream fault fixture. Never deploy as an application service."""
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import json,os,time
from pathlib import Path
from protocol.replay_identity import redactor_identity
SYNTHETIC_IDENTITY=redactor_identity({"python":"3.12.14","platform_machine":"x86_64","model_manifest_sha256":"a"*64,"sources":{k:"a"*64 for k in ["app","model_loader","requirements_lock","identity_contract","identity_builder"]},"dependencies":{"synthetic-test-only":"1.0"},"dependency_records":{"synthetic-test-only":"b"*64},"recognizer_configuration_sha256":"c"*64,"recognizer_count":1})
class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args):pass
    def respond(self,value,status=200):
        raw=json.dumps(value).encode();self.send_response(status);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(raw)));self.end_headers()
        try:self.wfile.write(raw)
        except (BrokenPipeError,ConnectionResetError):pass
    def do_GET(self):self.respond({'ok':True} if self.path=='/healthz' else {},200 if self.path=='/healthz' else 404)
    def do_POST(self):
        size=int(self.headers.get('Content-Length','0'))
        if size>1_250_000:self.respond({},413);return
        try:payload=json.loads(self.rfile.read(size))
        except ValueError:self.respond({},400);return
        mode=json.loads(Path('/fixture/mode.json').read_text())['mode']
        if mode=='slow':time.sleep(15)
        if mode=='invalid_redaction' and self.path=='/redact':
            self.respond({'identity':SYNTHETIC_IDENTITY,'text':payload['text'],'entities':['PERSON'],'entity_count':1});return
        if self.path=='/redact':self.respond({'identity':SYNTHETIC_IDENTITY,'text':payload['text'],'entities':[],'entity_count':0});return
        if mode=='malformed':self.respond({'unexpected':'synthetic'});return
        candidate={'code':'UC' if mode=='unknown_code' else 'PS','confidence':1.,'signals':[{'id':'sig.fixture.v1','score':1.,'spans':[[0,999_999]] if mode=='bad_span' else [[0,1]]}]}
        self.respond({'candidates':[candidate] if mode in ('unknown_code','bad_span') else [],'models':[{'name':'rules-only','sha256':os.environ['EVAL_SOURCE_SHA'],'revision':'context-v5'}],'calibration_id':'uncalibrated-rules-v5'})
ThreadingHTTPServer(('0.0.0.0',8000),Handler).serve_forever()
