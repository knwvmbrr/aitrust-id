import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {readFileSync} from 'node:fs';
import {webcrypto} from 'node:crypto';
import {imageContext,validateImageRecord,explainImage,PARSERS,MAX_INPUT} from '../site/src/image-metadata-result.mjs';
import {imageClient,loadImageManifest,validateImageManifest} from '../site/src/image-metadata-client.mjs';
globalThis.crypto??=webcrypto;
const rows=JSON.parse(execFileSync(process.env.AITRUST_VERIFY_PYTHON||'python3',['-I','-S','-B','scripts/image-metadata-device-cases.py'],{encoding:'utf8',timeout:10000}));
const bytes=row=>Uint8Array.from(Buffer.from(row.bytes_base64,'base64')).buffer;
const wrap=row=>({format:'image-metadata-device-record/v1',kind:row.kind,source_sha256:PARSERS[row.kind].source_sha256,projection_sha256:PARSERS[row.kind].projection_sha256,record:structuredClone(row.expected)});
let groups=0;
for(const row of rows){const context=await imageContext(bytes(row)),value=validateImageRecord(wrap(row),context);assert.deepEqual(value.record,row.expected);assert.doesNotThrow(()=>explainImage(value));assert(Object.isFrozen(value.record));}
groups++;
const row=rows.find(r=>r.id==='png_private'),context=await imageContext(bytes(row));let refused=0;
for(const mutate of [v=>{v.record.raw_metadata='PRIVATE_FORGED_METADATA';},v=>{v.source_sha256='0'.repeat(64);},v=>{v.projection_sha256='0'.repeat(64);},v=>{v.record.asset_sha256='0'.repeat(64);},v=>{v.record.asset_bytes++;},v=>{v.record.image.width++;},v=>{v.record.tags=['FA'];},v=>{v.record.AI_origin='AI';},v=>{v.record.metadata_sections.plain_text=true;},v=>{v.record.content_truth_established=true;}]){const bad=wrap(row);mutate(bad);assert.throws(()=>validateImageRecord(bad,context));refused++;}
assert.throws(()=>validateImageRecord(wrap(rows[0]),context));assert.throws(()=>explainImage(wrap(row)));let getterReads=0;const getter=wrap(row);Object.defineProperty(getter.record,'raw_input',{enumerable:true,get(){getterReads++;return 'PRIVATE';}});assert.throws(()=>validateImageRecord(getter,context));assert.equal(getterReads,0);groups++;
class Reader{readyState=0;result=null;aborted=0;readAsArrayBuffer(blob){this.readyState=1;Blob.prototype.arrayBuffer.call(blob).then(raw=>{if(this.readyState!==1)return;this.result=raw;this.readyState=2;this.onload?.();});}abort(){this.aborted++;this.readyState=2;this.onabort?.();}}
const readers=[],workers=[];const createReader=()=>{const r=new Reader();readers.push(r);return r;};
function fakeWorker(record,fault){const w={terminated:0,postMessage(data){this.sent=data;queueMicrotask(()=>this.onmessage?.({data:fault||{type:'result',id:data.id,record:structuredClone(record)}}));},terminate(){this.terminated++;}};workers.push(w);queueMicrotask(()=>w.onmessage?.({data:{type:'ready'}}));return w;}
for(const row of [rows[0],rows.find(r=>r.id==='jpeg_private')]){const client=imageClient({createReader,createWorker:()=>fakeWorker(wrap(row))});const value=await client.check(new Blob([bytes(row)],{type:'text/plain'}));assert.deepEqual(value.record,row.expected);assert.equal(workers.at(-1).terminated,1);assert.deepEqual(Object.keys(workers.at(-1).sent).sort(),['bytes','id','kind']);assert(!('name'in workers.at(-1).sent));}
groups++;
let started=0,readStarted=0;const capped=imageClient({createReader(){readStarted++;return new Reader();},createWorker(){started++;throw Error('must not start');}});
await assert.rejects(capped.check(new Blob([])));await assert.rejects(capped.check(new Blob([new Uint8Array(MAX_INPUT+1)])));assert.equal(readStarted,0);assert.equal(started,0);
await assert.rejects(capped.check(new Blob(['not an image'])));assert.equal(started,0);groups++;
const held={readyState:0,aborted:0,readAsArrayBuffer(){this.readyState=1;},abort(){this.readyState=2;this.aborted++;this.onabort?.();}};
const cancel=imageClient({createReader:()=>held,createWorker(){started++;throw Error('no worker');}});const pending=cancel.check(new Blob([bytes(rows[0])]));cancel.stop();await assert.rejects(pending);assert.equal(held.aborted,1);assert.equal(started,0);assert.equal(held.onload,null);groups++;
const timed={readyState:0,aborted:0,readAsArrayBuffer(){this.readyState=1;},abort(){this.aborted++;this.readyState=2;this.onabort?.();}};await assert.rejects(imageClient({createReader:()=>timed,loadTimeout:20}).check(new Blob([bytes(rows[0])])));assert.equal(timed.aborted,1);groups++;
let badWorker;const wrong=imageClient({createReader,createWorker:()=>badWorker=fakeWorker(wrap(rows[0]))});await assert.rejects(wrong.check(new Blob([bytes(row)])));assert.equal(badWorker.terminated,1);const healthy=imageClient({createReader,createWorker:()=>fakeWorker(wrap(rows[0]))});assert.equal((await healthy.check(new Blob([bytes(rows[0])]))).record.state,'OBSERVED');groups++;
const delayed=imageClient({createReader,createWorker:()=>{const w=fakeWorker(wrap(rows[0]));w.postMessage=function(data){this.sent=data;};return w;},checkTimeout:20});await assert.rejects(delayed.check(new Blob([bytes(rows[0])])));assert.equal(workers.at(-1).terminated,1);groups++;
const runtime=JSON.parse(readFileSync('sbom/nested-runtime/pyodide-wasm-release.json')).runtime_members;
const manifest={format:'image-metadata-device-manifest/v1',source_commit:'8e1b1a23a1bef0659bf1ec567ceef647b5cd76a5',runtime:'314.0.7',python_version:'3.14.2',runtime_path:'/device/runtime-314.0.7/',runtime_files:runtime,bundle:'method-'+'a'.repeat(64)+'.json',bundle_sha256:'a'.repeat(64),bundle_bytes:100,parsers:PARSERS,max_input_bytes:MAX_INPUT,build_inputs:{'trusted.py':'b'.repeat(64)},experimental:true};assert.equal(validateImageManifest(manifest),manifest);assert.throws(()=>validateImageManifest({...manifest,raw_file:'PRIVATE'}));assert.throws(()=>validateImageManifest({...manifest,parsers:{...PARSERS,png:{...PARSERS.png,projection_sha256:'c'.repeat(64)}}}));groups++;
const originalFetch=globalThis.fetch,originalTimer=globalThis.setTimeout;
try{
 globalThis.fetch=async()=>new Response(JSON.stringify(manifest));assert.deepEqual(await loadImageManifest(),manifest);
 globalThis.fetch=async()=>new Response('x'.repeat(65537));await assert.rejects(loadImageManifest());
 let defaultBudget;globalThis.setTimeout=(callback,ms,...args)=>{if(ms===10000)defaultBudget=ms;return originalTimer(callback,ms===10000?15:ms,...args);};globalThis.fetch=()=>new Promise(()=>{});await assert.rejects(loadImageManifest());assert.equal(defaultBudget,10000);
 const abort=new AbortController();abort.abort();await assert.rejects(loadImageManifest({signal:abort.signal}));
}finally{globalThis.fetch=originalFetch;globalThis.setTimeout=originalTimer;}
groups++;
console.log(JSON.stringify({pass:true,groups,canonical_records:rows.length,corrupt_records_refused:refused+1,private_getter_reads:getterReads,size_gate_before_reader_and_worker:true,capture_abort_deadline:true,independent_client_recovery:true,no_external_process_or_SDK:true}));
