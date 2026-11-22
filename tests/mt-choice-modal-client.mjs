import assert from 'node:assert/strict';
import fs from 'node:fs';
import {execFileSync}from'node:child_process';
import {choiceContext,validateChoice,explainChoice}from'../site/src/mt-choice-result.mjs';
import {choiceClient,loadManifest,MANIFEST_TIMEOUT_MS}from'../site/src/mt-choice-client.mjs';
const py=process.env.AITRUST_VERIFY_PYTHON||'python3';
const rows=JSON.parse(execFileSync(py,['-I','-S','-B','scripts/mt-choice-device-cases.py'],{encoding:'utf8',timeout:10000}));
const artifact=JSON.parse(fs.readFileSync('site/public/device/mt-choice/manifest.json'));
const nativeManifest={...artifact,python_version:rows[0].expected.original.runtime.python_version};
const base=rows.find(r=>r.id==='additive');let groups=0;
for(const row of rows){const {context}=await choiceContext(row.request,nativeManifest);const record=validateChoice(structuredClone(row.expected),context,nativeManifest);assert(Object.isFrozen(record));assert(explainChoice(record).title);}
groups++;
const bound=await choiceContext(base.request,nativeManifest);
for(const change of [r=>{r.original.raw_input='PRIVATE_CANARY';},r=>{r.counts.additive_frames=0;},r=>{r.original.observations[0].choice_spans[0]=[-1,999];},r=>{r.source_sha256['tools/choice_framing.py']='0'.repeat(64);},r=>{r.original.method_sha256='0'.repeat(64);},r=>{r.tags=['MT'];},r=>{r.intent_established=0;},r=>{r.original.observations[0].construction='either_or';}]){const r=structuredClone(base.expected);change(r);assert.throws(()=>validateChoice(r,bound.context,nativeManifest));}
const other=await choiceContext({...base.request,subject:'Either tea or coffee.'},nativeManifest);assert.throws(()=>validateChoice(base.expected,other.context,nativeManifest));groups++;
let getter=0;const privateRecord=structuredClone(base.expected);Object.defineProperty(privateRecord.original,'raw_input',{enumerable:true,get(){getter++;return'PRIVATE_CANARY';}});assert.throws(()=>validateChoice(privateRecord,bound.context,nativeManifest));assert.equal(getter,0);groups++;
for(const change of [{subject:'x'.repeat(2001)},{reference:'x'.repeat(2001)},{whole_frame:false},{first:'coffee',second:'tea'},{first:'tea',second:'tea'}])await assert.rejects(choiceContext({...base.request,...change},nativeManifest));groups++;
function workerFor(record,{wrongID=false}={}){const state={terminated:0};const w={terminate(){state.terminated++;},postMessage(d){queueMicrotask(()=>w.onmessage({data:{type:'result',id:wrongID?d.id+1:d.id,record:structuredClone(record)}}));}};queueMicrotask(()=>w.onmessage({data:{type:'ready'}}));return{w,state};}
let made=[];const c=choiceClient(nativeManifest,{createWorker(){const x=workerFor(base.expected);made.push(x);return x.w;}});assert.equal((await c.check(base.request)).counts.additive_frames,1);assert.equal(made[0].state.terminated,1);assert.equal((await c.check(base.request)).counts.additive_frames,1);assert.equal(made.length,2);assert.equal(made[1].state.terminated,1);groups++;
const faulty=choiceClient(nativeManifest,{createWorker(){throw Error('PRIVATE_EXCEPTION');}});await assert.rejects(faulty.check(base.request));assert.equal((await c.check(base.request)).state,'OBSERVATIONS');groups++;
let beforeCreate=0;const cancelled=choiceClient(nativeManifest,{createWorker(){beforeCreate++;return workerFor(base.expected).w;}});const pending=cancelled.check(base.request);cancelled.stop();await assert.rejects(pending);await new Promise(r=>setTimeout(r,20));assert.equal(beforeCreate,0);groups++;
let badId;const incorrect=choiceClient(nativeManifest,{createWorker:()=>{badId=workerFor(base.expected,{wrongID:true});return badId.w;}});await assert.rejects(incorrect.check(base.request));assert.equal(badId.state.terminated,1);groups++;
// A stalled crypto binding is inside the unchanged startup deadline and creates no worker.
const subtle=crypto.subtle,digest=Object.getOwnPropertyDescriptor(subtle,'digest');Object.defineProperty(subtle,'digest',{configurable:true,value:()=>new Promise(()=>{})});
try{let count=0;const stalled=choiceClient(nativeManifest,{loadTimeout:20,createWorker(){count++;return workerFor(base.expected).w;}});await assert.rejects(stalled.check(base.request));assert.equal(count,0);}finally{if(digest)Object.defineProperty(subtle,'digest',digest);else delete subtle.digest;}groups++;
const realFetch=globalThis.fetch,realSetTimeout=globalThis.setTimeout;let timerBudgets=[];
try{
 globalThis.fetch=async()=>new Response(JSON.stringify(artifact));assert.equal((await loadManifest()).bundle,artifact.bundle);
 globalThis.fetch=async()=>new Response(JSON.stringify({...artifact,raw_input:'PRIVATE_CANARY'}));await assert.rejects(loadManifest());
 globalThis.fetch=async()=>new Response('x'.repeat(65537));await assert.rejects(loadManifest());
 globalThis.fetch=()=>new Promise(()=>{});globalThis.setTimeout=(fn,ms,...args)=>{timerBudgets.push(ms);return realSetTimeout(fn,15,...args);};await assert.rejects(loadManifest());assert(timerBudgets.includes(MANIFEST_TIMEOUT_MS));
 globalThis.setTimeout=realSetTimeout;const controller=new AbortController();const request=loadManifest({signal:controller.signal});controller.abort();await assert.rejects(request);
}finally{globalThis.fetch=realFetch;globalThis.setTimeout=realSetTimeout;}
groups++;
console.log(JSON.stringify({pass:true,groups,canonical_records:rows.length,corrupt_records_refused:9,private_getter_reads:getter,manifest_deadline_ms:MANIFEST_TIMEOUT_MS,legacy_code_changed:false}));
