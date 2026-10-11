"""Actual Python signer to native Web Crypto; no private test key is retained."""
import base64
import hashlib
import json
import os
from pathlib import Path
import subprocess

import pytest
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, utils
from fastapi.testclient import TestClient
from protocol.transport_signing import load_private_key, payload, public_profile, sign_headers
from test_gateway_integration import g, upstream

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def key():
    return ec.generate_private_key(ec.SECP256R1())


def verify_python(key, response, request, nonce):
    raw = base64.urlsafe_b64decode(response.headers['X-AITrust-Signature']+'==')
    key.public_key().verify(utils.encode_dss_signature(int.from_bytes(raw[:32]), int.from_bytes(raw[32:])),
                            payload(nonce, request, response.content), ec.ECDSA(hashes.SHA256()))


def test_actual_gateway_python_to_webcrypto(monkeypatch, key):
    calls=upstream(monkeypatch);monkeypatch.setattr(g,'SIGNING_KEY',key)
    nonce='b'*64;request=json.dumps({'text':'synthetic private example','origin_host':'chatgpt.com'},ensure_ascii=False).encode()
    with TestClient(g.app) as client:
        response=client.post('/v1/evaluate',content=request,headers={'authorization':'Bearer '+g.TOKEN,'content-type':'application/json','X-AITrust-Nonce':nonce})
    assert response.status_code==200 and len(calls)==2
    verify_python(key,response,request,nonce)
    fixture={'key':public_profile(key),'headers':dict(response.headers),'nonce':nonce,'request':request.decode(),'response':response.text}
    script="""const fs=require('node:fs'),vm=require('node:vm');vm.runInThisContext(fs.readFileSync('extension/src/shared/transport.js','utf8'));
    (async()=>{const v=JSON.parse(fs.readFileSync(0,'utf8')),key=await AITrustTransport.selectedKey(v.key),response=new Response(v.response,{headers:v.headers});
    await AITrustTransport.verify(response,new TextEncoder().encode(v.response),v.nonce,v.request,key);
    for(const change of [{nonce:'a'.repeat(64)},{request:'{}'},{response:v.response+' '}]){let rejected=false;const x={...v,...change};try{await AITrustTransport.verify(response,new TextEncoder().encode(x.response),x.nonce,x.request,key);}catch{rejected=true;}if(!rejected)throw Error('alteration accepted');}
    console.log('verified; replay and exact-byte alterations refused');})().catch(()=>process.exit(1));"""
    output=subprocess.run(['node','-e',script],input=json.dumps(fixture),text=True,cwd=ROOT,capture_output=True,check=True)
    assert output.stdout.strip()=='verified; replay and exact-byte alterations refused'


@pytest.mark.parametrize('nonce',['','abc','a'*63,'A'*64,'a'*65])
def test_bad_nonce_never_evaluates(monkeypatch,nonce):
    calls=upstream(monkeypatch)
    with TestClient(g.app) as client:
        response=client.post('/v1/evaluate',json={'text':'synthetic'},headers={'authorization':'Bearer '+g.TOKEN,'X-AITrust-Nonce':nonce})
    assert response.status_code==422 and not calls


def test_no_signer_refuses_before_evaluation(monkeypatch):
    calls=upstream(monkeypatch);monkeypatch.setattr(g,'SIGNING_KEY',None)
    with TestClient(g.app) as client:
        response=client.post('/v1/evaluate',json={'text':'synthetic'},headers={'authorization':'Bearer '+g.TOKEN,'X-AITrust-Nonce':'a'*64})
    assert response.status_code==503 and not calls


def test_duplicate_nonce_refused(monkeypatch,key):
    calls=upstream(monkeypatch);monkeypatch.setattr(g,'SIGNING_KEY',key)
    with TestClient(g.app) as client:
        response=client.post('/v1/evaluate',json={'text':'synthetic'},headers=[('authorization','Bearer '+g.TOKEN),('X-AITrust-Nonce','a'*64),('X-AITrust-Nonce','b'*64)])
    assert response.status_code==422 and not calls


@pytest.mark.parametrize('mode',[0o400,0o600,0o644,0o660])
def test_private_file_permissions(tmp_path,key,mode):
    p=tmp_path.resolve()/'key.pem';p.write_bytes(key.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,serialization.NoEncryption()));p.chmod(mode)
    if mode in (0o400,0o600):assert public_profile(load_private_key(p))==public_profile(key)
    else:
        with pytest.raises(ValueError):load_private_key(p)


def test_private_symlink_and_wrong_curve(tmp_path):
    p=tmp_path.resolve()/'key.pem';key=ec.generate_private_key(ec.SECP384R1());p.write_bytes(key.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,serialization.NoEncryption()));p.chmod(0o600)
    with pytest.raises(ValueError):load_private_key(p)
    link=p.with_name('link.pem');link.symlink_to(p)
    with pytest.raises(ValueError):load_private_key(link)


def test_private_special_file_and_oversize_refused(tmp_path):
    fifo=tmp_path.resolve()/'pipe';os.mkfifo(fifo,0o600)
    with pytest.raises(ValueError):load_private_key(fifo)
    large=fifo.with_name('large.pem');large.write_bytes(b'x'*16_385);large.chmod(0o600)
    with pytest.raises(ValueError):load_private_key(large)


def test_public_key_rejects_unknown_fields_invalid_points_and_fingerprint(key):
    good=public_profile(key)
    invalid=[{**good,'extra':'ignored'}, {**good,'key_id':'f'*64}, {**good,'profile':'future/v2'}]
    raw=b'\x04'+b'\0'*64
    invalid.append({'profile':good['profile'],'key_id':hashlib.sha256(raw).hexdigest(),
                    'public_key':base64.urlsafe_b64encode(raw).decode().rstrip('=')})
    script="""const fs=require('node:fs'),vm=require('node:vm');vm.runInThisContext(fs.readFileSync('extension/src/shared/transport.js','utf8'));
    (async()=>{for(const key of JSON.parse(fs.readFileSync(0,'utf8'))){let rejected=false;try{await AITrustTransport.selectedKey(key);}catch{rejected=true;}if(!rejected)throw Error('key accepted');}console.log('all invalid public keys refused');})().catch(()=>process.exit(1));"""
    result=subprocess.run(['node','-e',script],input=json.dumps(invalid),text=True,cwd=ROOT,capture_output=True,check=True)
    assert result.stdout.strip()=='all invalid public keys refused'


def test_cli_generates_and_derives_same_public_profile(tmp_path):
    directory=tmp_path.resolve();directory.chmod(0o700);private=directory/'private.pem';public=directory/'public.json';derived=directory/'derived.json'
    def run(*args):return subprocess.run(['node','scripts/gateway-key.cjs',*map(str,args)],cwd=ROOT,capture_output=True,text=True)
    assert run('keygen',private,public).returncode==0
    assert public_profile(load_private_key(private))==json.loads(public.read_text())
    before=private.read_bytes();assert run('keygen',private,public).returncode==2 and private.read_bytes()==before
    assert run('public',private,derived).returncode==0 and public.read_bytes()==derived.read_bytes()
