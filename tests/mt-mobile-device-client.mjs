import test from 'node:test';import assert from 'node:assert/strict';import {execFileSync} from 'node:child_process';import fs from 'node:fs';import {createHash} from 'node:crypto';
import {mtMobileSubject,validMTMobileRecord,explainMTMobile} from '../site/src/mt-mobile-device-result.js';
import {mtDeviceClient,validMTInput,explainMTSelection} from '../site/src/mt-device-client.js';
const rows=JSON.parse(execFileSync(process.env.AITRUST_VERIFY_PYTHON||'python3',['-B','scripts/mt-mobile-device-cases.py'],{encoding:'utf8'}));
const row=rows.find(r=>r.id==='phone'),copy=()=>structuredClone(row.expected);
class WorkerFixture{constructor(reply){this.reply=reply;this.terminated=false;}ready(){this.onmessage({data:{type:'ready'}});}postMessage(d){this.reply?.(this,d);}terminate(){this.terminated=true;}}
test('all complete canonical records validate and unsupported grammar is not guessed',async()=>{
 for(const row of rows){if(row.expected){const r=validMTMobileRecord(structuredClone(row.expected),await mtMobileSubject(row.text));assert(Object.isFrozen(r.original.parameters));assert(explainMTMobile(r).title);}
 else if(!['record_cap'].includes(row.id))await assert.rejects(mtMobileSubject(row.text));}
});
test('raw identity refuses canonically equivalent but different input',async()=>{
 const source=rows.find(r=>r.id==='combining_non_bmp');assert.throws(()=>validMTMobileRecord(source.expected,undefined));const c=await mtMobileSubject(source.text.normalize('NFC'));assert.throws(()=>validMTMobileRecord(structuredClone(source.expected),c));
});
test('closed records refuse private fields, sources, grammar, positions and promotion',async()=>{
 const context=await mtMobileSubject(row.text),mutations=[
 r=>r.raw_input='PRIVATE_CANARY',r=>r.original.raw_input='PRIVATE_CANARY',r=>r.original.parameters.extra='PRIVATE_CANARY',
 r=>r.raw_sha256='0'.repeat(64),r=>r.raw_bytes++,r=>r.subject_characters++,r=>r.source_sha256['tools/mt_mobile_device.py']='0'.repeat(64),
 r=>r.original.source_sha256['tools/authority_mobile_quotation.py']='0'.repeat(64),r=>r.original.parameters.quote_style='ASCII',
 r=>r.original.quote_spans=[[0,2]],r=>r.original.quoted_phrases[0].phrase_span=[-1,99999],
 r=>r.original.quoted_phrases[0].source_marker_spans=[[0,1]],r=>r.original.quoted_phrases[0].extra='PRIVATE_CANARY',
 r=>r.counts.quoted_phrase_count=0,r=>r.original.quote_endorsement_interpreted=true,r=>r.tag_asserted=true,r=>r.tags=['MT'],
 r=>Object.defineProperty(r,'raw_input',{get(){throw Error('Getter invoked');},enumerable:true})];
 for(const mutate of mutations){const r=copy();mutate(r);assert.throws(()=>validMTMobileRecord(r,context));}
});
test('existing client explicitly selects candidate and binds whole input',async()=>{
 validMTInput('authority-curly',row.text);let worker,made=0;const client=mtDeviceClient({createWorker:()=>{made++;return worker=new WorkerFixture((w,d)=>w.onmessage({data:{type:'result',id:d.id,record:copy()}}));}});
 assert.equal(made,0);const pending=client.check('authority-curly',row.text);worker.ready();const result=await pending;assert(worker.terminated);assert((await explainMTSelection(result,'authority-curly')).body.includes('1 quoted'));
 const wrong=client.check('authority-curly','An ordinary sentence.');worker.ready();await assert.rejects(wrong);assert(worker.terminated);
});
test('candidate cancellation and cleanup failure do not hang or poison a peer',async()=>{
 let w;const one=mtDeviceClient({createWorker:()=>w=new WorkerFixture()});const p=one.check('authority-curly',row.text);const done=assert.rejects(p);one.stop();await done;assert(w.terminated);
 let bad;const cleanup=mtDeviceClient({createWorker:()=>{bad=new WorkerFixture();bad.terminate=()=>{throw Error('PRIVATE_CLEANUP_CANARY');};return bad;}});const r=cleanup.check('authority-curly',row.text);const refusal=assert.rejects(r,/cleanup unavailable/);assert.doesNotThrow(()=>cleanup.stop());await refusal;
 const again=cleanup.check('authority-curly',row.text);const refused=assert.rejects(again);cleanup.stop();await refused;
});
test('legacy canonical sources and public manifest retain baseline hashes',()=>{
 const baseline=JSON.parse(fs.readFileSync('runs/2026-11-21-mt-mobile-quotes-before.json'));for(const [name,hash] of Object.entries(baseline.sources))assert.equal(createHash('sha256').update(fs.readFileSync(name)).digest('hex'),hash);
});
