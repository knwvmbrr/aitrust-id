import test from 'node:test';import assert from 'node:assert/strict';import fs from 'node:fs';import {execFileSync} from 'node:child_process';
import {hpDeviceClient,validHPInput,manifest} from '../site/src/hp-device-client.js';
import {hpSubject,validHPRecord,explainHP} from '../site/src/hp-device-result.js';
const record=text=>JSON.parse(execFileSync(process.env.AITRUST_VERIFY_PYTHON||'python3',['-c','import sys;from tools.hp_device import inspect_hp_device;print(inspect_hp_device(sys.argv[1]))',text],{encoding:'utf8'}));
class WorkerFixture{constructor(reply){this.reply=reply;this.terminated=false;}ready(){this.onmessage({data:{type:'ready'}});}postMessage(data){this.reply?.(this,data);}terminate(){this.terminated=true;}}
test('bounded input and frozen identity reject malformed values',async()=>{
 for(const text of ['',null,'x'.repeat(8001),'\0','\ud800'])assert.throws(()=>validHPInput(text));
 validHPInput('😀'.repeat(8000));const context=await hpSubject('Cafe\u0301 12.');assert(context.raw_characters>context.subject_characters);
});
test('client does not start at creation and owns a fresh worker per explicit run',async()=>{
 let made=0,w;const client=hpDeviceClient({createWorker:()=>{made++;return w=new WorkerFixture((self,data)=>self.onmessage({data:{type:'result',id:data.id,record:record(data.text)}}));}});
 assert.equal(made,0);for(const text of ['There are 12 items.','There are 12 items [1].']){const pending=client.check(text);w.ready();const value=await pending;assert.equal(value.counts.supported_detail_count,1);assert(w.terminated);}assert.equal(made,2);
});
test('wrong subject and NFC-equivalent but different raw input cannot reuse a result',async()=>{
 for(const [sent,requested] of [['There are 12 items.','A plain unrelated paragraph.'],['Café has 12 items.','Cafe\u0301 has 12 items.']]){
  let w;const canonical=record(sent);const client=hpDeviceClient({createWorker:()=>w=new WorkerFixture((self,d)=>self.onmessage({data:{type:'result',id:d.id,record:canonical}}))});
  const pending=client.check(requested);w.ready();await assert.rejects(pending);assert(w.terminated);
 }
});
test('clear/stop affects only its own worker and late messages cannot revive it',async()=>{
 let a,b;const first=hpDeviceClient({createWorker:()=>a=new WorkerFixture()}),second=hpDeviceClient({createWorker:()=>b=new WorkerFixture()});
 const p=first.check('12 items.'),q=second.check('25 items.');const pReject=assert.rejects(p);first.stop();await pReject;assert(a.terminated&&!b.terminated);
 a.onmessage({data:{type:'result',id:1,record:record('12 items.')}});const qReject=assert.rejects(q);second.stop();await qReject;
});
test('loading/evaluation/termination failures reject and never become a quiet result',async()=>{
 let w;const loading=hpDeviceClient({createWorker:()=>w=new WorkerFixture(),loadTimeout:10});await assert.rejects(loading.check('12 items.'));assert(w.terminated);
 const run=hpDeviceClient({createWorker:()=>w=new WorkerFixture(),checkTimeout:10});const p=run.check('12 items.');w.ready();await assert.rejects(p);assert(w.terminated);
 const bad=hpDeviceClient({createWorker:()=>{throw Error('Unsupported Worker');}});await assert.rejects(bad.check('12 items.'));
});
test('closed canonical/nested schema refuses raw fields, altered sources/counts/spans and false interpretation',async()=>{
 const text='There are 12 items [1].',context=await hpSubject(text);
 const mutations=[r=>r.raw_input='SYNTHETIC_PRIVATE_CANARY',r=>r.original.raw_input='SYNTHETIC_PRIVATE_CANARY',r=>r.original.details[0].text='SYNTHETIC_PRIVATE_CANARY',
 r=>r.original.parameters.extra='SYNTHETIC_PRIVATE_CANARY',r=>r.original.privacy='SYNTHETIC_PRIVATE_CANARY',r=>r.original.source_file_sha256['tools/quantitative_observations.py']='0'.repeat(64),
 r=>r.source_sha256['tools/hp_device.py']='0'.repeat(64),r=>r.raw_bytes++,r=>r.raw_sha256='0'.repeat(64),r=>r.subject_characters++,
 r=>r.original.details[0].span=[-1,99999],r=>r.original.details[0].unit_span=[0,1],r=>r.original.details[0].source_marker_spans=[[0,1]],
 r=>r.original.details[0].source_marker_spans=[[999,1000]],r=>r.original.details[0].kind='verified_date',r=>r.original.parameters.max_details=999,
 r=>r.original.with_same_unit_marker=0,r=>r.counts.supported_detail_count=0,r=>r.original.truth_established=true,r=>r.tags.push('HP')];
 for(const mutate of mutations){const value=record(text);mutate(value);assert.throws(()=>validHPRecord(value,context));}
 assert.throws(()=>validHPRecord(record(text)));assert.throws(()=>explainHP(record(text)));
});
test('data accessors and malformed dense collections are refused before rendering',async()=>{
 const context=await hpSubject('12 items.');let calls=0;const value=record('12 items.');Object.defineProperty(value.original,'method',{enumerable:true,get(){calls++;return manifest.method;}});
 assert.throws(()=>validHPRecord(value,context));assert.equal(calls,0);
 const extra=record('12 items.');extra.original.details.foo='SYNTHETIC_PRIVATE_CANARY';assert.throws(()=>validHPRecord(extra,context));
});
test('literal/date, marker and long-s source semantics stay canonical, with immutable safe descriptions',async()=>{
 for(const text of ['12 items.','12 items [0].','Date:2026-99-88.','12 items httpſ://example.invalid.','é123 表456.']){
  const value=validHPRecord(record(text),await hpSubject(text));assert.doesNotThrow(()=>explainHP(value));assert(Object.isFrozen(value.original.details));assert.throws(()=>value.original.raw_input='SYNTHETIC_PRIVATE_CANARY');
 }
});
test('all existing frozen NFC version witnesses bind raw and normalized identities',async()=>{
 const texts=JSON.parse(fs.readFileSync('runs/2026-10-10-normalization-version-gap.json')).examples.map(w=>w.input+' There are 12 items.');
 const native=JSON.parse(execFileSync('python3',['-c',"import json,sys;from tools.hp_device import inspect_hp_device;print(json.dumps([json.loads(inspect_hp_device(t)) for t in json.load(sys.stdin)]))"],{input:JSON.stringify(texts),encoding:'utf8'}));
 for(let i=0;i<texts.length;i++)validHPRecord(native[i],await hpSubject(texts[i]));
});
test('bundle carries exact project NOTICE, LICENSE and Unicode attribution',()=>{
 const bundle=JSON.parse(fs.readFileSync('site/public'+manifest.path));for(const name of ['LICENSE','NOTICE','eval/vectors/unicode/LICENSE.txt'])assert.equal(bundle.files[name],fs.readFileSync(name,'utf8'));
});
