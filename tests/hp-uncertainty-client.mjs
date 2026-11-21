import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {webcrypto} from 'node:crypto';
import {uncertaintyContext,validUncertaintyRecord,explainUncertainty} from '../site/src/hp-uncertainty-result.js';
import {hpUncertaintyClient} from '../site/src/hp-uncertainty-client.js';
if(!globalThis.crypto)globalThis.crypto=webcrypto;
const cases=JSON.parse(execFileSync(process.env.AITRUST_VERIFY_PYTHON||'python3',['-B','scripts/hp-uncertainty-cases.py'],{encoding:'utf8'}));let groups=0;
for(const row of cases){let context;try{context=await uncertaintyContext(row.text,true);}catch{assert.equal(row.expected,null,row.id);continue;}
 if(row.expected)assert.equal(validUncertaintyRecord(structuredClone(row.expected),context).method,row.expected.method,row.id);else assert.throws(()=>validUncertaintyRecord({},context),row.id);
}groups++;
const base=cases.find(c=>c.id==='present'),context=await uncertaintyContext(base.text,true);
for(const mutate of [r=>r.raw_sha256='0'.repeat(64),r=>r.subject_sha256='0'.repeat(64),r=>r.annotation.uncertainty=[[0,1]],r=>r.annotation.sources=[[0,1]],r=>r.original.measurements.contexts[0].hedge_spans=[],r=>r.original.measurements.contexts[0].hedge_spans=[[0,1]],r=>r.original.raw_input='PRIVATE_CANARY',r=>r.source_sha256['tools/language_observations.py']='0'.repeat(64),r=>r.tag_asserted=true,r=>r.uncertainty_needed_established=true]){const record=structuredClone(base.expected);mutate(record);assert.throws(()=>validUncertaintyRecord(record,context));}groups++;
assert.throws(()=>explainUncertainty(structuredClone(base.expected)));assert.throws(()=>validUncertaintyRecord(base.expected,{}));assert.throws(()=>validUncertaintyRecord(Object.defineProperty({},'x',{enumerable:true,get(){throw Error('getter');}}),context));groups++;
const unicode=cases.find(c=>c.id==='canonical_nfc');assert.throws(()=>validUncertaintyRecord(unicode.expected,context));assert.throws(()=>validUncertaintyRecord(unicode.expected,awaitWrong()));function awaitWrong(){return {};}
const canonicalEquivalent=await uncertaintyContext(unicode.text.normalize('NFC'),true);assert.throws(()=>validUncertaintyRecord(unicode.expected,canonicalEquivalent));assert.throws(()=>{context.annotation.uncertainty[0][1]=1;});groups++;
let workers=[];const make=record=>()=>{const worker={terminated:false,terminate(){this.terminated=true;},postMessage(d){queueMicrotask(()=>this.onmessage?.({data:{type:'result',id:d.id,record:structuredClone(record)}}));}};workers.push(worker);queueMicrotask(()=>worker.onmessage?.({data:{type:'ready'}}));return worker;};
let client=hpUncertaintyClient({createWorker:make(base.expected)});assert.equal((await client.check(base.text,true)).method,base.expected.method);assert(workers.at(-1).terminated);groups++;
client=hpUncertaintyClient({createWorker:make(base.expected)});await assert.rejects(client.check('A different passage.',true));assert(workers.at(-1).terminated);groups++;
let touched=false;client=hpUncertaintyClient({createWorker:()=>{touched=true;throw Error();}});await assert.rejects(client.check(base.text,false));await assert.rejects(client.check('x'.repeat(8001),true));assert.equal(touched,false);groups++;
let hanging;client=hpUncertaintyClient({createWorker:()=>hanging={terminated:false,terminate(){this.terminated=true;},postMessage(){}},loadTimeout:10});await assert.rejects(client.check(base.text,true));assert(hanging.terminated);groups++;
client=hpUncertaintyClient({createWorker:()=>hanging={terminated:false,terminate(){this.terminated=true;},postMessage(){}}});const pending=client.check(base.text,true);client.stop();await assert.rejects(pending);assert(hanging.terminated);groups++;
client=hpUncertaintyClient({createWorker:()=>{throw Error('missing optional worker');}});await assert.rejects(client.check(base.text,true));client=hpUncertaintyClient({createWorker:make(base.expected)});assert.equal((await client.check(base.text,true)).state,base.expected.state);groups++;
console.log(JSON.stringify({pass:true,groups,authored_cases:cases.length,complete_records:cases.filter(c=>c.expected).length,refusals:cases.filter(c=>!c.expected).length,independent_accuracy_evidence:false}));
