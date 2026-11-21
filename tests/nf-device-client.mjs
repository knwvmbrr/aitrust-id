import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {webcrypto} from 'node:crypto';
import {nfInputs,validLiteralRecord,explainNF} from '../site/src/nf-device-result.js';
import {validCosineRecord} from '../site/src/nf-cosine-result.js';
import {nfDeviceClient} from '../site/src/nf-device-client.js';
if(!globalThis.crypto)globalThis.crypto=webcrypto;
const cases=JSON.parse(execFileSync(process.env.AITRUST_VERIFY_PYTHON||'python3',['scripts/nf-device-cases.py'],{encoding:'utf8'}));
let groups=0;
for(const row of cases){
 let context;try{context=await nfInputs(row.claim,row.passage,row.check);}catch{assert.equal(row.expected,null);continue;}
 const validate=row.check==='literal'?validLiteralRecord:validCosineRecord;
 if(row.expected)assert.equal(validate(structuredClone(row.expected),context).check,row.check,row.id);
 else assert.throws(()=>validate({},context));
}groups++;
const baseline=cases.find(c=>c.id==='literal_same'),overlap=cases.find(c=>c.id==='negation_overlap');
for(const row of [baseline,overlap]){
 const validate=row.check==='literal'?validLiteralRecord:validCosineRecord,c=await nfInputs(row.claim,row.passage,row.check);
 for(const mutate of [r=>r.claim.raw_sha256='0'.repeat(64),r=>r.passage.raw_sha256='0'.repeat(64),r=>r.passage.normalized_sha256='0'.repeat(64),r=>r.claim.normalized_sha256='0'.repeat(64),r=>r.check='unknown',r=>r.source_sha256['tools/nf_device.py']='0'.repeat(64),r=>r.original.raw_input='PRIVATE_CORRUPTION_CANARY',r=>r.truth_established=true,r=>r.original.matches?r.original.matches=[]:r.original.findings=[],r=>r.original.matches?r.original.matches[0].source_span=[0,99]:r.original.findings[0].score=1]){
  const record=structuredClone(row.expected);mutate(record);assert.throws(()=>validate(record,c));
 }
}groups++;
const tie=cases.find(c=>c.id==='ties_even'),tieContext=await nfInputs(tie.claim,tie.passage,'cosine');
assert.equal(tie.expected.original.findings[0].score,0.991821289062);
validCosineRecord(structuredClone(tie.expected),tieContext);
const forgedTie=structuredClone(tie.expected);forgedTie.original.findings[0].score=0.991821289063;
assert.throws(()=>validCosineRecord(forgedTie,tieContext));groups++;
assert.throws(()=>validLiteralRecord(baseline.expected,{}));
assert.throws(()=>explainNF(structuredClone(baseline.expected)));
const getterContext=await nfInputs(baseline.claim,baseline.passage,'literal');
assert.throws(()=>validLiteralRecord(Object.defineProperty({},'bad',{get(){throw Error('getter must not run');},enumerable:true}),getterContext));groups++;
const equivalent=await nfInputs('e\u0301','é','literal'),different=await nfInputs('é','é','literal');
const unicode=cases.find(c=>c.id==='canonical_unicode');assert.throws(()=>validLiteralRecord(unicode.expected,equivalent));assert.throws(()=>validLiteralRecord(unicode.expected,different));groups++;
function workerFor(record,{hang=false}={}){return ()=>{const w={terminated:false,terminate(){this.terminated=true;},postMessage(message){if(message.type==='init')queueMicrotask(()=>this.onmessage({data:{type:'ready'}}));else if(!hang)queueMicrotask(()=>this.onmessage({data:{type:'result',id:message.id,record:structuredClone(record)}}));}};workers.push(w);return w;};}
const workers=[];
let client=nfDeviceClient({createWorker:workerFor(baseline.expected)});assert.equal((await client.check(baseline.claim,baseline.passage,'literal')).check,'literal');assert(workers.at(-1).terminated);groups++;
client=nfDeviceClient({createWorker:workerFor(overlap.expected),loadValidator:()=>Promise.reject(Error('optional missing'))});await assert.rejects(client.check(overlap.claim,overlap.passage,'cosine'));assert(workers.at(-1).terminated);
client=nfDeviceClient({createWorker:workerFor(baseline.expected),loadValidator:()=>{throw Error('Literal must not import optional');}});assert.equal((await client.check(baseline.claim,baseline.passage,'literal')).check,'literal');groups++;
client=nfDeviceClient({createWorker:workerFor(baseline.expected,{hang:true}),checkTimeout:10});await assert.rejects(client.check(baseline.claim,baseline.passage,'literal'));assert(workers.at(-1).terminated);groups++;
client=nfDeviceClient({createWorker:workerFor(baseline.expected,{hang:true})});const cancelled=client.check(baseline.claim,baseline.passage,'literal');client.stop();await assert.rejects(cancelled);assert(workers.at(-1).terminated);groups++;
client=nfDeviceClient({createWorker:()=>{throw Error('no worker');}});await assert.rejects(client.check(baseline.claim,baseline.passage,'literal'));groups++;
console.log(JSON.stringify({pass:true,groups,authored_canonical_cases:cases.length,independent_accuracy_evidence:false}));
