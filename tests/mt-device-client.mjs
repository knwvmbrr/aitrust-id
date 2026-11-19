import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {execFileSync} from 'node:child_process';
import {mtDeviceClient,validMTInput,manifest} from '../site/src/mt-device-client.js';
import {validMTRecord,explainMT} from '../site/src/mt-device-result.js';
const record=(kind='urgency',text='Buy now.')=>JSON.parse(execFileSync(process.env.AITRUST_VERIFY_PYTHON||'python3',['-c',"import sys;from tools.mt_device import inspect_mt_device;print(inspect_mt_device(sys.argv[1],sys.argv[2]))",kind,text],{encoding:'utf8'}));
class WorkerFixture{
 constructor(reply){this.reply=reply;this.terminated=false;}
 ready(){this.onmessage({data:{type:'ready'}});}
 postMessage(data){this.request=data;this.reply?.(this,data);}
 terminate(){this.terminated=true;}
}
test('input rejects unsupported selections, oversize and invalid Unicode',()=>{
 for(const [kind,text] of [['','Buy now.'],['choice','Buy now.'],['urgency',''],['urgency','x'.repeat(8001)],['urgency','\0'],['urgency','\ud800']])assert.throws(()=>validMTInput(kind,text));
 validMTInput('urgency','😀'.repeat(8000));
});
test('mounting/client creation does not start a worker; every run owns and closes one',async()=>{
 let made=0,worker;const client=mtDeviceClient({createWorker:()=>{made++;return worker=new WorkerFixture((w,d)=>w.onmessage({data:{type:'result',id:d.id,record:record(d.kind,d.text)}}));}});
 assert.equal(made,0);let pending=client.check('urgency','Buy now.');worker.ready();assert.equal((await pending).state,'OBSERVATIONS');assert.equal(worker.terminated,true);
 pending=client.check('authority','The example says "Experts agree".');worker.ready();assert.equal((await pending).counts.quoted_phrase_count,1);assert.equal(made,2);assert.equal(worker.terminated,true);
});
test('stop closes only its worker and refuses a late result',async()=>{
 let one,two;const first=mtDeviceClient({createWorker:()=>one=new WorkerFixture()});const other=mtDeviceClient({createWorker:()=>two=new WorkerFixture()});
 const a=first.check('urgency','Buy now.');const b=other.check('urgency','Buy now.');const refused=assert.rejects(a);first.stop();await refused;
 assert.equal(one.terminated,true);assert.equal(two.terminated,false);one.onmessage({data:{type:'result',id:1,record:record()}});
 const done=assert.rejects(b);other.stop();await done;
});
test('load and evaluation deadline terminate their own worker',async()=>{
 let worker;let client=mtDeviceClient({createWorker:()=>worker=new WorkerFixture(),loadTimeout:10});await assert.rejects(client.check('urgency','Buy now.'));assert(worker.terminated);
 client=mtDeviceClient({createWorker:()=>worker=new WorkerFixture(),checkTimeout:10});const pending=client.check('urgency','Buy now.');worker.ready();await assert.rejects(pending);assert(worker.terminated);
});
test('malformed, wrong-input-ID, and wrong-method messages never become observations',async()=>{
 for(const mode of ['malformed','id','method','identity','claim']){
  let worker;const value=record();if(mode==='method')value.method='unreviewed';if(mode==='identity')value.source_sha256['tools/mt_device.py']='a'.repeat(64);if(mode==='claim')value.tags=['MT'];
  const client=mtDeviceClient({createWorker:()=>worker=new WorkerFixture((w,d)=>w.onmessage({data:mode==='malformed'?{}:{type:'result',id:mode==='id'?d.id+1:d.id,record:value}}))});
  const pending=client.check('urgency','Buy now.');worker.ready();await assert.rejects(pending);assert(worker.terminated);
 }
});
test('worker unsupported/constructor failures refuse without an uncaught exception',async()=>{
 const client=mtDeviceClient({createWorker:()=>{throw Error('not supported');}});await assert.rejects(client.check('urgency','Buy now.'));
});
test('plain result descriptions distinguish quoted, marked, unmarked and density-limited results',()=>{
 for(const [kind,text,heading] of [['authority','"Experts agree".','appears in a quote'],['authority','Experts agree [1].','has a source marker'],['authority','Experts agree.','Authority wording found'],['urgency','Buy now. Nothing else. One more unit.','no overall match']])assert(explainMT(record(kind,text)).title.includes(heading));
});
test('bundle contains exact source, LICENSE, NOTICE and Unicode attribution',()=>{
 const raw=fs.readFileSync('site/public'+manifest.path);const value=JSON.parse(raw);
 for(const name of ['LICENSE','NOTICE','eval/vectors/unicode/LICENSE.txt'])assert.equal(value.files[name],fs.readFileSync(name,'utf8'));
});
