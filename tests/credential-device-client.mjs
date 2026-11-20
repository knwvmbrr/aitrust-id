import test from 'node:test';import assert from 'node:assert/strict';import fs from 'node:fs';import {execFileSync} from 'node:child_process';
import {credentialDeviceClient,validCredentialInput,manifest} from '../site/src/credential-device-client.js';
import {credentialSubject,validCredentialRecord,explainCredential} from '../site/src/credential-device-result.js';
const rows=JSON.parse(execFileSync(process.env.AITRUST_VERIFY_PYTHON||'python3',['-B','scripts/credential-device-cases.py'],{encoding:'utf8'}));
const flow=rows.find(r=>r.id==='flow').text;
const record=text=>structuredClone(rows.find(r=>r.text===text)?.expected);
class WorkerFixture{constructor(reply){this.reply=reply;this.terminated=false;}ready(){this.onmessage({data:{type:'ready'}});}postMessage(data){this.reply?.(this,data);}terminate(){this.terminated=true;}}
test('input limits, surrogate/NUL and unbranded subject refuse',async()=>{
 for(const text of ['',null,'x'.repeat(8001),'\0','\ud800']){assert.throws(()=>validCredentialInput(text));await assert.rejects(credentialSubject(text));}
 validCredentialInput('😀'.repeat(8000));const context=await credentialSubject('label="Cafe\u0301"\npass');assert(context.raw_characters>context.subject_characters);
 assert.throws(()=>validCredentialRecord(record(flow),{...context}));assert.throws(()=>explainCredential(record(flow)));
});
test('whole canonical fixtures validate, immutable evidence and no safety claims',async()=>{
 for(const row of rows.filter(r=>r.expected)){
  const r=validCredentialRecord(structuredClone(row.expected),await credentialSubject(row.text));const brief=explainCredential(r);
  assert(brief.title.length);assert(Object.isFrozen(r.original.findings));assert.throws(()=>r.original.raw_input='PRIVATE_CANARY');
  assert.equal(r.original.subject_executed,false);assert.equal(r.tag_asserted,false);assert.equal(r.safety_established,false);
 }
});
test('no eager worker, fresh owned worker for each explicit run and busy refuses',async()=>{
 let made=0,w;const client=credentialDeviceClient({createWorker:()=>{made++;return w=new WorkerFixture((self,data)=>self.onmessage({data:{type:'result',id:data.id,record:record(data.text)}}));}});
 assert.equal(made,0);for(const text of [flow,'pass']){const pending=client.check(text);await assert.rejects(client.check(flow));w.ready();await pending;assert(w.terminated);}assert.equal(made,2);
});
test('wrong subject and NFC-equivalent raw source cannot reuse a result',async()=>{
 for(const [sent,requested] of [[flow,'pass'],[rows.find(r=>r.id==='nfc').text,rows.find(r=>r.id==='nfc').text.normalize('NFC')]]){
  let w;const original=record(sent);const client=credentialDeviceClient({createWorker:()=>w=new WorkerFixture((self,d)=>self.onmessage({data:{type:'result',id:d.id,record:original}}))});
  const pending=client.check(requested);w.ready();await assert.rejects(pending);assert(w.terminated);
 }
});
test('stop, repeated cancellation and late replies cannot affect another client',async()=>{
 let a,b;const first=credentialDeviceClient({createWorker:()=>a=new WorkerFixture()}),second=credentialDeviceClient({createWorker:()=>b=new WorkerFixture()});
 const p=first.check(flow),q=second.check('pass'),pReject=assert.rejects(p);first.stop();first.stop();await pReject;assert(a.terminated&&!b.terminated);
 a.onmessage({data:{type:'result',id:1,record:record(flow)}});const qReject=assert.rejects(q);second.stop();await qReject;
});
test('load/check deadlines, errors, absent Worker and cleanup failure never produce zero',async()=>{
 let w;const loading=credentialDeviceClient({createWorker:()=>w=new WorkerFixture(),loadTimeout:10});await assert.rejects(loading.check(flow));assert(w.terminated);
 const run=credentialDeviceClient({createWorker:()=>w=new WorkerFixture(),checkTimeout:10});const p=run.check(flow);w.ready();await assert.rejects(p);assert(w.terminated);
 for(const kind of ['create','error','messageerror','terminate']){
  const c=credentialDeviceClient({createWorker:()=>{if(kind==='create')throw Error('PRIVATE_CANARY');w=new WorkerFixture((self,d)=>self.onmessage({data:{type:'result',id:d.id,record:record(d.text)}}));if(kind==='terminate')w.terminate=()=>{throw Error('PRIVATE_CANARY');};return w;}});
  const pending=c.check(flow);if(kind==='error')w.onerror();else if(kind==='messageerror')w.onmessageerror();else if(kind==='terminate')w.ready();await assert.rejects(pending);
 }
});
test('unexpected message phases and stale ids refuse complete records',async()=>{
 for(const mode of ['before_ready','wrong_id','double_ready','unavailable']){
  let w;const client=credentialDeviceClient({createWorker:()=>w=new WorkerFixture()});const pending=client.check(flow);
  if(mode!=='before_ready')w.ready();
  w.onmessage({data:mode==='double_ready'?{type:'ready'}:mode==='unavailable'?{type:'unavailable',id:1}:{type:'result',id:mode==='wrong_id'?999:1,record:record(flow)}});
  await assert.rejects(pending);assert(w.terminated);
 }
});
test('closed envelope and original nested schemas refuse raw extra fields and source drift',async()=>{
 const context=await credentialSubject(flow);const mutations=[r=>r.raw_input='PRIVATE_CANARY',r=>r.original.raw_input='PRIVATE_CANARY',r=>r.original.findings[0].raw='PRIVATE_CANARY',
 r=>r.counts.extra='PRIVATE_CANARY',r=>r.source_sha256.extra='PRIVATE_CANARY',r=>r.original.method_sha256='0'.repeat(64),
 r=>r.source_sha256['tools/credential_device.py']='0'.repeat(64),r=>r.raw_bytes++,r=>r.raw_sha256='0'.repeat(64),r=>r.subject_characters++,r=>r.original.subject_characters++,
 r=>r.original.findings[0].sink_span=[-1,99999],r=>r.original.recognized_read_spans[0]=[0,99999],r=>r.original.findings[0].source_spans=[[0,1]],
 r=>r.original.findings[0].source_spans=[],r=>r.original.findings.push(structuredClone(r.original.findings[0])),r=>r.original.recognized_read_spans.push(r.original.recognized_read_spans[0]),
 r=>r.original.findings[0].meaning='malicious',r=>r.original.findings[0].id='PS',r=>r.counts.static_flows=0,r=>r.counts.recognized_reads=0,
 r=>r.original.state='NO_SUPPORTED_FLOW',r=>r.original.subject_executed=true,r=>r.original.live_credential_verified=true,r=>r.tags.push('PS'),r=>r.context_classified=true,r=>r.safety_established=true];
 for(const mutate of mutations){const value=record(flow);mutate(value);assert.throws(()=>validCredentialRecord(value,context));}
});
test('accessor fields, sparse/extra collections and arbitrary prototypes refuse without executing getters',async()=>{
 const context=await credentialSubject(flow);let calls=0;const value=record(flow);Object.defineProperty(value.original,'method',{enumerable:true,get(){calls++;return manifest.method;}});
 assert.throws(()=>validCredentialRecord(value,context));assert.equal(calls,0);
 const extra=record(flow);extra.original.findings.foo='PRIVATE_CANARY';assert.throws(()=>validCredentialRecord(extra,context));
 const sparse=record(flow);delete sparse.original.findings[0];assert.throws(()=>validCredentialRecord(sparse,context));
 const proto=record(flow);Object.setPrototypeOf(proto.original,{extra:'PRIVATE_CANARY'});assert.throws(()=>validCredentialRecord(proto,context));
});
test('all original project and Unicode notices are exact, bundle inventory closed',()=>{
 const bundle=JSON.parse(fs.readFileSync('site/public'+manifest.path));assert.deepEqual(Object.keys(bundle.files).sort(),Object.keys(manifest.sources).sort());
 for(const name of ['LICENSE','NOTICE','eval/vectors/unicode/LICENSE.txt'])assert.equal(bundle.files[name],fs.readFileSync(name,'utf8'));
});
