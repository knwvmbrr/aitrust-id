'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),crypto=require('node:crypto'),fs=require('node:fs'),os=require('node:os'),path=require('node:path'),{spawnSync,execFileSync}=require('node:child_process');
const r=require('../protocol/receipts.cjs'),{create}=require('../tools/composition/core.cjs');
const root=path.resolve(__dirname,'..');
function pair(alg='ed25519'){const p=crypto.generateKeyPairSync(alg,alg==='ec'?{namedCurve:'prime256v1'}:{});return {private:p.privateKey.export({type:'pkcs8',format:'pem'}),public:p.publicKey.export({type:'spki',format:'pem'})};}
function observed(text='Synthetic text'){
 const s=create();s.start(0);s.event({kind:'edit',at:1,before:0,after:text.length,position:0,removed:0,added:text.length,input:'paste'});s.pause(10);
 return {...s.snapshot(),artifact_sha256:r.hash(Buffer.from(text)),artifact_encoding:'UTF-8; exact editor value; no normalization',source_sha256:r.hash(fs.readFileSync(path.join(root,'tools/composition/core.cjs')))};
}
test('published canonical vector is key-sorted with exact arrays/numbers',()=>{assert.equal(r.canonical({z:[true,null,-0,1e-7],a:'é'}),'{"a":"é","z":[true,null,0,1e-7]}');assert.deepEqual(JSON.parse(JSON.stringify(r.parse('{ "b": 2, "a": [1] }'))),{b:2,a:[1]});});
for(const text of ['{"a":1,"a":2}','{"a":{"x":1,"x":2}}','[1,]','{"a":1,}','01','NaN','1e999','9007199254740993','{}false','{"x":"\\ud800"}', '['.repeat(18)+'0'+']'.repeat(18)])test('strict parser refuses '+text.slice(0,25),()=>assert.throws(()=>r.parse(text)));
test('oversize and invalid UTF8 are refused',()=>{assert.throws(()=>r.parse(' '.repeat(262145)));assert.throws(()=>r.parse(Buffer.from([255])));});
for(const alg of ['ed25519','ec']){
 test(alg+' signs and verifies exact canonical records under a pinned key',()=>{const k=pair(alg),record={kind:'test',value:42},env=r.sign(record,k.private);assert.equal(r.canonical(r.verify(env,k.public)),r.canonical(record));assert.throws(()=>r.verify(env,pair(alg).public));});
 test(alg+' receipt binds artifact, evidence, expiry and distinct trust states',()=>{const k=pair(alg),artifact=Buffer.from('Synthetic text'),record=r.receipt(artifact,observed(),1000),env=r.sign(record,k.private);let result=r.inspectReceipt(env,k.public,artifact,1100);assert.equal(result.expiry,'within_declared_window');assert.equal(result.revocation,'unchecked');assert.equal(result.authorship,'unestablished');assert.equal(result.certified_valid,false);assert.equal(result.forgery_cost_class,'unvalidated');assert.equal(r.inspectReceipt(env,k.public,artifact,1000+86400).expiry,'expired');assert.equal(r.inspectReceipt(env,k.public,artifact,999).expiry,'not_yet_current');assert.throws(()=>r.inspectReceipt(env,k.public,Buffer.from('Another artifact'),1100));});
 test(alg+' payload or signature tampering is refused',()=>{const k=pair(alg),env=r.sign({kind:'test'},k.private);assert.throws(()=>r.verify({...env,payload:Buffer.from('{"kind":"changed"}').toString('base64')},k.public));assert.throws(()=>r.verify({...env,signature:Buffer.alloc(64).toString('base64')},k.public));});
}
test('algorithm mismatch, unknown profile and embedded-key auto-trust refused',()=>{const k=pair(),env=r.sign({a:1},k.private);for(const change of [{algorithm:'RSA'},{version:'unknown'},{public_key:k.public},{key_sha256:'0'.repeat(64)}])assert.throws(()=>r.verify({...env,...change},k.public));});
test('a correctly signed noncanonical payload is still refused',()=>{const k=pair(),raw=Buffer.from('{ "b":2,"a":1 }'),env=r.sign({a:1},k.private);env.payload=raw.toString('base64');env.signature=crypto.sign(null,raw,k.private).toString('base64');assert.throws(()=>r.verify(env,k.public),/Noncanonical/);});
for(const change of [{forgery_cost_class:'structural'},{authorship_proven:true},{independent_timestamp:true},{tag_issuance:true},{revocation_status:'good'},{extra:true},{expires_at:1000+604801}])test('unsupported receipt claim '+Object.keys(change)[0]+' refused',()=>{const k=pair(),a=Buffer.from('Synthetic text'),receipt={...r.receipt(a,observed(),1000),...change};assert.throws(()=>r.inspectReceipt(r.sign(receipt,k.private),k.public,a,1100));});
test('observation claims and privacy suppression are validated',()=>{for(const change of [{tags:['PA']},{authorship_inference:true},{record_type:'assertion'},{method:'unknown'},{timing:{...observed().timing,samples:2,dwell_cv:1}},{extra:'private text'}])assert.throws(()=>r.receipt(Buffer.from('Synthetic text'),{...observed(),...change},1000));});
test('unsupported expiry or artifact binding refused before issuance',()=>{for(const lifetime of [0,59,604801,NaN])assert.throws(()=>r.receipt(Buffer.from('Synthetic text'),observed(),1000,lifetime));assert.throws(()=>r.receipt(Buffer.from('altered'),observed(),1000));});
test('exact UTF8 artifact binding preserves a leading Unicode BOM',()=>{const text='\ufeffSynthetic text',k=pair(),a=Buffer.from(text),record=r.receipt(a,observed(text),1000);assert.equal(r.inspectReceipt(r.sign(record,k.private),k.public,a,1100).artifact_binding,'matched');});
test('CLI local files, both algorithms, refusal and assertion-schema checks',()=>{
 const dir=fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(),'aitrust-receipt-')));fs.chmodSync(dir,0o700);
 const run=(...args)=>spawnSync(process.execPath,['scripts/receipt.cjs',...args],{cwd:root,encoding:'utf8',env:process.env});
 try{
  for(const alg of ['Ed25519','ECDSA-P256-SHA256']){
   const prefix=path.join(dir,alg),priv=prefix+'.private.pem',pub=prefix+'.public.pem',artifact=prefix+'.txt',observation=prefix+'.observation.json',receipt=prefix+'.receipt.json';
   assert.equal(run('keygen',alg,priv,pub).status,0);assert.equal(fs.statSync(priv).mode&0o777,0o600);assert.equal(run('keygen',alg,priv,pub).status,2);
   fs.writeFileSync(artifact,'Synthetic text');fs.writeFileSync(observation,JSON.stringify(observed()));
   assert.equal(run('issue',artifact,observation,priv,receipt).status,0);const verification=run('verify',receipt,pub,artifact);assert.equal(verification.status,0);assert.equal(JSON.parse(verification.stdout).certified_valid,false);
   fs.writeFileSync(artifact,'Changed');assert.equal(run('verify',receipt,pub,artifact).status,2);
   fs.writeFileSync(artifact,'Synthetic text');
   fs.chmodSync(priv,0o644);assert.equal(run('issue',artifact,observation,priv,prefix+'.refused.json').status,2);fs.chmodSync(priv,0o600);
   const link=prefix+'.link';fs.symlinkSync(priv,link);assert.equal(run('issue',artifact,observation,link,prefix+'.refused.json').status,2);
   const assertion=JSON.parse(execFileSync(process.env.AITRUST_VERIFY_PYTHON||'python3',['-c',"import sys,json;sys.path.insert(0,'tests');from test_extension_consumer import envelope;print(json.dumps(envelope()))"],{cwd:root,encoding:'utf8'}));
   const input=prefix+'.assertion.json',signed=prefix+'.signed.json';fs.writeFileSync(input,JSON.stringify(assertion));assert.equal(run('sign-assertion',input,priv,signed).status,0);assert.equal(run('verify-assertion',signed,pub).status,0);
   assertion.assertion_id='malformed';fs.writeFileSync(input,JSON.stringify(assertion));assert.equal(run('sign-assertion',input,priv,prefix+'.bad-signature.json').status,2);assert(!fs.existsSync(prefix+'.bad-signature.json'));
   fs.writeFileSync(prefix+'.schema-bad.json',JSON.stringify(r.sign(assertion,fs.readFileSync(priv))));assert.equal(run('verify-assertion',prefix+'.schema-bad.json',pub).status,2);
  }
 }finally{fs.rmSync(dir,{recursive:true,force:true});}
});
