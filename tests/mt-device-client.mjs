import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {execFileSync} from 'node:child_process';
import {mtDeviceClient,validMTInput,manifest} from '../site/src/mt-device-client.js';
import {validMTRecord,explainMT,mtSubject} from '../site/src/mt-device-result.js';
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
test('plain result descriptions distinguish quoted, marked, unmarked and density-limited results',async()=>{
 for(const [kind,text,heading] of [['authority','"Experts agree".','appears in a quote'],['authority','Experts agree [1].','has a source marker'],['authority','Experts agree.','Authority wording found'],['urgency','Buy now. Nothing else. One more unit.','no overall match']])assert(explainMT(validMTRecord(record(kind,text),kind,await mtSubject(text))).title.includes(heading));
});
test('bundle contains exact source, LICENSE, NOTICE and Unicode attribution',()=>{
 const raw=fs.readFileSync('site/public'+manifest.path);const value=JSON.parse(raw);
 for(const name of ['LICENSE','NOTICE','eval/vectors/unicode/LICENSE.txt'])assert.equal(value.files[name],fs.readFileSync(name,'utf8'));
});


test('canonical observation for another input is rejected despite matching request ID',async()=>{
 let worker;const canonical=record();const client=mtDeviceClient({createWorker:()=>worker=new WorkerFixture((w,d)=>w.onmessage({data:{type:'result',id:d.id,record:canonical}}))});
 const pending=client.check('urgency','A plain unrelated paragraph.');worker.ready();await assert.rejects(pending);assert(worker.terminated);
});
test('closed urgency records reject raw fields, counts, spans and internal association corruption',async()=>{
 const context=await mtSubject('Buy now.');const mutations=[
  r=>r.original.raw_input='SYNTHETIC_PRIVATE_CANARY',r=>r.raw_input='SYNTHETIC_PRIVATE_CANARY',
  r=>r.original.measurements.raw_input='SYNTHETIC_PRIVATE_CANARY',r=>r.original.findings[0].raw_input='SYNTHETIC_PRIVATE_CANARY',
  r=>r.original.measurements.paired_units[0].raw_input='SYNTHETIC_PRIVATE_CANARY',
  r=>r.original.findings[0].spans=[[-100,999999]],r=>r.original.findings[0].spans=[[0,0]],
  r=>r.original.measurements.directive_spans=[[0,999999]],r=>r.original.measurements.paired_units[0].unit_span=[1,2],
  r=>r.original.measurements.paired_units[0].time_pressure_spans=[[0,3]],
  r=>r.original.measurements.directive_density=.9,r=>r.original.measurements.directive_units=-1,
  r=>r.original.measurements.minimum_density=.01,r=>r.original.subject_characters=999,r=>r.subject_characters=999,
  r=>r.counts.paired_units=0,r=>r.original.measurements.unpaired_time_pressure_spans=[[4,7]],
  r=>r.original.findings[0].meaning='SYNTHETIC_PRIVATE_CANARY',r=>r.original.tags.push('MT'),
 ];
 for(const mutate of mutations){const value=record();mutate(value);assert.throws(()=>validMTRecord(value,'urgency',context));}
 assert.throws(()=>validMTRecord(record(),'urgency'));
});
test('authority nested sources, parameters, quotes, markers and classification counts are closed',async()=>{
 const text='"Experts agree [1]"; studies show benefits.';const context=await mtSubject(text);
 const mutations=[r=>r.original.source_sha256['tools/authority_quotation.py']='0'.repeat(64),
  r=>r.original.parameters.raw_input='SYNTHETIC_PRIVATE_CANARY',r=>r.original.quoted_phrases[0].raw_input='SYNTHETIC_PRIVATE_CANARY',
  r=>r.original.quoted_phrases[0].phrase_span=[-1,3],r=>r.original.quoted_phrases[0].source_marker_spans=[[0,999]],
  r=>r.original.quoted_phrases[0].quote_span=[1,4],r=>r.original.quote_spans=[[0,2]],
  r=>r.original.outside_markerless_phrases[0].quote_span=[0,18],r=>r.original.outside_markerless_phrases[0].source_marker_spans=[[15,18]],
  r=>r.original.parameters.max_quotes=999,r=>r.original.quoted_phrase_count=99,r=>r.counts.supported_quote_count=-1,
  r=>r.original.source_lookup_performed=true,r=>r.original.outside_marked_phrases.push(r.original.outside_markerless_phrases[0])];
 for(const mutate of mutations){const value=record('authority',text);mutate(value);assert.throws(()=>validMTRecord(value,'authority',context));}
});
test('frozen NFC binds equivalent text, canonical overlapping urgency spans and immutable rendering',async()=>{
 const text='Read Cafe\u0301 details now. Install the viewer.';const value=validMTRecord(record('urgency',text),'urgency',await mtSubject(text));
 assert(value.subject_characters<Array.from(text).length);assert(Object.isFrozen(value.original.measurements.paired_units[0].unit_span));
 assert.throws(()=>value.original.raw_input='SYNTHETIC_PRIVATE_CANARY');assert.doesNotThrow(()=>explainMT(value));
 const overlapping=validMTRecord(record('urgency','Act fast.'),'urgency',await mtSubject('Act fast.'));assert(overlapping.original.findings[0].spans.length===2);
 const witnesses=JSON.parse(fs.readFileSync('runs/2026-10-10-normalization-version-gap.json')).examples;
 const texts=witnesses.map(w=>w.input+' Buy now.');
 const native=JSON.parse(execFileSync('python3',['-c',"import sys,json;from tools.mt_device import inspect_mt_device;print(json.dumps([json.loads(inspect_mt_device('urgency',t)) for t in json.load(sys.stdin)]))"],{input:JSON.stringify(texts),encoding:'utf8'}));
 const contexts=await Promise.all(texts.map(mtSubject));
 for(let i=0;i<texts.length;i++)assert.doesNotThrow(()=>validMTRecord(native[i],'urgency',contexts[i]));
});
test('validation refuses accessor and comma-combined unknown keys before values can run',async()=>{
 const context=await mtSubject('Buy now.');let calls=0;const value=record();
 Object.defineProperty(value.original,'method',{enumerable:true,get(){calls++;return manifest.methods.urgency;}});
 assert.throws(()=>validMTRecord(value,'urgency',context));assert.equal(calls,0);
 const raw=record();delete raw.counts.finding_groups;delete raw.counts.paired_units;raw.counts['finding_groups,paired_units']=1;
 assert.throws(()=>validMTRecord(raw,'urgency',context));
 const authorityText='Experts agree.';const a=record('authority',authorityText),authorityContext=await mtSubject(authorityText);
 a.original.parameters.language={toJSON(){calls++;return 'en';}};
 assert.throws(()=>validMTRecord(a,'authority',authorityContext));assert.equal(calls,0);
});

// UI must retain native paste; the existing client is the authoritative pre-worker bound.
test('complete oversized emoji and ASCII refuse before any worker for every existing selection',async()=>{
 for(const kind of ['urgency','authority','authority-curly'])for(const text of ['😀'.repeat(8001),'x'.repeat(16001)]){
  let made=0;const client=mtDeviceClient({createWorker:()=>{made++;throw Error('Worker must not start');}});
  assert.throws(()=>validMTInput(kind,text));await assert.rejects(client.check(kind,text));assert.equal(made,0);
 }
});
