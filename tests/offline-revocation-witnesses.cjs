'use strict';

const test=require('node:test');
const assert=require('node:assert/strict');
const {generateKeyPairSync}=require('node:crypto');
const fs=require('node:fs');
const os=require('node:os');
const path=require('node:path');
const {spawnSync}=require('node:child_process');
const logTool=require('../protocol/revocation.cjs');
const witness=require('../protocol/revocation-witnesses.cjs');
const receipt=require('../protocol/receipts.cjs');

function key(type='ed25519'){
 const {publicKey,privateKey}=generateKeyPairSync(type,type==='ec'?{namedCurve:'prime256v1'}:{});
 return {pub:publicKey.export({type:'spki',format:'pem'}),priv:privateKey.export({type:'pkcs8',format:'pem'})};
}
const authority=key(),a=key(),b=key('ec'),c=key();
const genesis=logTool.extend(null,authority.priv,null,1000,600);
const next=logTool.extend(genesis,authority.priv,a.pub,1001,600);
const fork=logTool.extend(genesis,authority.priv,b.pub,1001,600);
const policy=witness.createPolicy(authority.pub,2,[a.pub,b.pub,c.pub]);
const a0=witness.sign(genesis,authority.pub,a.priv,null);
const b0=witness.sign(genesis,authority.pub,b.priv,null);
const a1=witness.sign(next,authority.pub,a.priv,a0);
const b1=witness.sign(next,authority.pub,b.priv,b0);
const check=(log=next,proofs=[a1,b1],selected=policy)=>witness.verify(log,authority.pub,selected,proofs);

test('two distinct selected keys sign exactly the validated current checkpoint',()=>{
 const result=check();
 assert.equal(result.status,'selected_witness_threshold_met');
 assert.equal(result.verified_witness_key_count,2);
 assert.equal(result.checkpoint_sequence,2);
 assert.equal(result.checkpoint_sha256,logTool.history(next,authority.pub)[1].sha256);
 assert.equal(receipt.verify(b1,b.pub).checkpoint_sha256,result.checkpoint_sha256);
 assert(!JSON.stringify(result).includes(logTool.id(a.pub)));
 for(const k of ['independent_operators_proven','independently_timestamped','public_distribution_proven','completeness_proven','key_status_evaluated','tag_issuance'])assert.equal(result[k],false);
});
test('zero or one authenticated observation cannot meet the selected minimum',()=>{
 for(const inputs of [[],[a1]]){
  assert.equal(check(next,inputs).verified_witness_key_count,inputs.length);
  assert.equal(check(next,inputs).status,'insufficient_selected_witnesses');
 }
 assert.equal(check(next,[a1,b1],{...policy,minimum_witnesses:3}).status,'insufficient_selected_witnesses');
});
test('an authority, duplicate key or unreviewed policy cannot dilute the threshold',()=>{
 assert.throws(()=>witness.sign(next,authority.pub,authority.priv,null),/Authority/);
 assert.throws(()=>witness.createPolicy(authority.pub,2,[a.pub,authority.pub]),/Authority/);
 assert.throws(()=>witness.createPolicy(authority.pub,2,[a.pub,a.pub]),/duplicate/);
 for(const bad of [{...policy,minimum_witnesses:1},{...policy,unexpected:true},{...policy,version:'future'}])assert.throws(()=>check(next,[a1,b1],bad),/Invalid witness policy/);
 assert.throws(()=>check(next,[a1,a1]),/duplicate/);
});
test('equivalent P-256 public point encodings represent one witness and one authority',()=>{
 // Public fixtures only: two supported SPKI encodings of one P-256 point.
 const expanded='-----BEGIN PUBLIC KEY-----\nMFkwEwYHKoZIzj0CAQYIKoZIzj0DAQcDQgAEnH0a9Yj3u7XIpzPlvLm61RoYwKAf\ncOFu4FCN7qtQ88m0mrPL/PGy6AHvbNLjqdm7KVZNnsXJGpSrZEtKmQamvg==\n-----END PUBLIC KEY-----\n';
 const compact='-----BEGIN PUBLIC KEY-----\nMDkwEwYHKoZIzj0CAQYIKoZIzj0DAQcDIgACnH0a9Yj3u7XIpzPlvLm61RoYwKAf\ncOFu4FCN7qtQ88k=\n-----END PUBLIC KEY-----\n';
 assert.equal(witness.createPolicy(authority.pub,2,[expanded,c.pub]).minimum_witnesses,2);
 assert.equal(witness.createPolicy(authority.pub,2,[compact,c.pub]).minimum_witnesses,2);
 assert.throws(()=>witness.createPolicy(authority.pub,2,[expanded,compact]),/duplicate/);
 assert.throws(()=>witness.createPolicy(compact,2,[expanded,c.pub]),/Authority/);
 assert.throws(()=>witness.createPolicy(expanded,2,[compact,c.pub]),/Authority/);
});
test('all supplied observations validate even when two already meet the threshold',()=>{
 const unrelated=key(),wrong=witness.sign(next,authority.pub,unrelated.priv,null);
 assert.throws(()=>check(next,[a1,b1,wrong]),/Unknown/);
 const corrupted={...witness.sign(next,authority.pub,c.priv,null),signature:Buffer.alloc(64).toString('base64')};
 assert.throws(()=>check(next,[a1,b1,corrupted]),/signature/i);
 const inflated={...receipt.verify(witness.sign(next,authority.pub,c.priv,null),c.pub),independent_operators_proven:true};
 assert.throws(()=>check(next,[a1,b1,receipt.sign(inflated,c.priv)]),/different checkpoint/);
});
test('a same-sequence fork, earlier checkpoint or different authority cannot verify',()=>{
 assert.throws(()=>check(fork),/different checkpoint/);
 assert.throws(()=>check(genesis),/different checkpoint/);
 assert.throws(()=>check(next,[a0,b1]),/different checkpoint/);
 const other=logTool.extend(null,c.priv,null,1001,600);
 assert.throws(()=>check(other),/Untrusted/);
});
test('advancing a witness rejects replay, fork, another witness or missing predecessor',()=>{
 assert.throws(()=>witness.sign(next,authority.pub,a.priv,a1),/later checkpoint/);
 assert.throws(()=>witness.sign(genesis,authority.pub,a.priv,a1),/later checkpoint/);
 assert.throws(()=>witness.sign(next,authority.pub,b.priv,a0),/Untrusted/);
 assert.throws(()=>witness.sign(next,authority.pub,a.priv,undefined));
 const laterFork=logTool.extend(fork,authority.priv,null,1002,600);
 assert.throws(()=>witness.sign(laterFork,authority.pub,a.priv,a1),/absent/);
 const laterNext=logTool.extend(next,authority.priv,null,1002,600);
 assert.equal(receipt.verify(witness.sign(laterNext,authority.pub,a.priv,a1),a.pub).checkpoint_sequence,3);
});
test('refuses an authority log with a broken suffix before signing or counting witnesses',()=>{
 const broken={...next,checkpoints:[...next.checkpoints.slice(0,-1),{...next.checkpoints[1],signature:Buffer.alloc(64).toString('base64')}]};
 assert.throws(()=>witness.sign(broken,authority.pub,a.priv,a0),/signature/i);
 assert.throws(()=>check(broken),/signature/i);
});
test('actual CLI builds a policy, signs, advances and verifies without overwriting or printing private data',()=>{
 const dir=fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(),'aitrust-witness-')));
 const p=name=>path.join(dir,name);
 const put=(name,value)=>fs.writeFileSync(p(name),value,{mode:0o600});
 const run=(...args)=>spawnSync(process.execPath,['scripts/revocation-witnesses.cjs',...args],{cwd:path.resolve(__dirname,'..'),encoding:'utf8',timeout:5000});
 const privateKey=p('a.pem'),signed=p('a.json'),pinned=p('authority.pub'),zero=p('genesis.json'),one=p('next.json'),saved=p('policy.json');
 try{
  put('a.pem',a.priv);put('b.pem',b.priv);put('a.pub',a.pub);put('b.pub',b.pub);put('authority.pub',authority.pub);
  put('genesis.json',receipt.bytes(genesis));put('next.json',receipt.bytes(next));put('null.json','null');
  assert.equal(run('policy',pinned,'2',saved,p('a.pub'),p('b.pub')).status,0);
  assert.equal(run('sign',zero,pinned,privateKey,signed).status,2);
  assert.equal(run('sign',zero,pinned,privateKey,signed,'--first-observation').status,0);
  const unchanged=fs.readFileSync(signed);
  assert.equal(run('sign',zero,pinned,privateKey,signed,'--first-observation').status,2);
  assert.deepEqual(fs.readFileSync(signed),unchanged);
  assert.equal(run('verify',zero,pinned,saved,signed).status,3);
  assert.equal(run('sign',one,pinned,privateKey,p('a-next.json'),'--after',signed).status,0);
  assert.equal(run('sign',one,pinned,p('b.pem'),p('b-next.json'),'--first-observation').status,0);
  const successful=run('verify',one,pinned,saved,p('a-next.json'),p('b-next.json'));
  assert.equal(successful.status,0);
  assert.equal(JSON.parse(successful.stdout).verified_witness_key_count,2);
  for(const refused of [
   run('sign',one,pinned,privateKey,p('bad.json'),'--after',p('null.json')),
   run('verify',one,pinned,saved,p('a-next.json'),signed),
  ]){
   assert.equal(refused.status,2);assert.equal(refused.stdout,'');assert(!refused.stderr.includes(dir));
  }
  fs.chmodSync(privateKey,0o644);
  assert.equal(run('sign',one,pinned,privateKey,p('bad.json'),'--first-observation').status,2);
  assert(!fs.existsSync(p('bad.json')));
  assert(!successful.stdout.includes('PRIVATE KEY'));
  assert.equal(fs.statSync(p('a-next.json')).mode&0o077,0);
 }finally{fs.rmSync(dir,{recursive:true,force:true});}
});
