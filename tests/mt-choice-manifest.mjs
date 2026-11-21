/* Focused correction controls: manifest allocation boundary and polite failure. */
import fs from 'node:fs/promises';import path from 'node:path';import os from 'node:os';import {pathToFileURL} from 'node:url';import assert from 'node:assert/strict';
const tmp=await fs.mkdtemp(path.join(os.tmpdir(),'mt-choice-manifest-'));const original=globalThis.fetch;let groups=0;
try{
 for(const name of ['mt-choice-result.mjs','mt-choice-client.mjs'])await fs.copyFile(path.join('site/src',name),path.join(tmp,name));
 await fs.copyFile('protocol/normalization.mjs',path.join(tmp,'normalization.mjs'));
 const {loadManifest,MANIFEST_TIMEOUT_MS}=await import(pathToFileURL(path.join(tmp,'mt-choice-client.mjs')));
 const value={format:'mt-choice-practice-manifest/v1',runtime:'314.0.7',method:'caller-bound-choice-framing-observation/1.3.0',runtime_path:'./runtime/',bundle:'method-'+'a'.repeat(64)+'.json',bundle_bytes:1};
 function fake(chunks,header=null){let read=0,cancelled=0,released=0;globalThis.fetch=async()=>({ok:true,headers:{get:()=>header},body:{getReader:()=>({async read(){return read<chunks.length?{value:chunks[read++],done:false}:{done:true};},async cancel(){cancelled++;},releaseLock(){released++;}})},text(){throw Error('Full-body decode forbidden');}});return()=>({read,cancelled,released});}
 let info=fake([new TextEncoder().encode(JSON.stringify(value))]);assert.deepEqual(await loadManifest(),value);assert.equal(info().released,1);groups++;
 for(const header of [null,'1']){info=fake([new Uint8Array(65536),new Uint8Array(1),new Uint8Array(65536)] ,header);await assert.rejects(loadManifest());assert.deepEqual(info(),{read:2,cancelled:1,released:1});}groups++;
 info=fake([new Uint8Array(65537),new Uint8Array(65536)]);await assert.rejects(loadManifest());assert.deepEqual(info(),{read:1,cancelled:1,released:1});groups++;
 info=fake([new Uint8Array(1)],'65537');await assert.rejects(loadManifest());assert.equal(info().read,0);groups++;
 info=fake([Uint8Array.of(0xff)]);await assert.rejects(loadManifest());assert.equal(info().released,1);groups++;
 const html=await fs.readFile('site/src/mt-choice-practice.html','utf8');assert.match(html,/id="unavailable" role="status" aria-live="polite"/);assert(!/role="alert"|aria-live="assertive"/.test(html));groups++;
 const realSetTimeout=globalThis.setTimeout,realClearTimeout=globalThis.clearTimeout,realParse=JSON.parse;
 const tick=async()=>{for(let i=0;i<6;i++)await Promise.resolve();};
 try{
  assert.equal(MANIFEST_TIMEOUT_MS,10000);
  for(const mode of ['headers','body']){
   let deadline,cleared=0,signal,release,readerOpened=0,cancelled=0,released=0,parsed=0,lateBytesRead=0;
   const timer={};globalThis.setTimeout=(callback,ms)=>{assert.equal(ms,10000);deadline=callback;return timer;};globalThis.clearTimeout=id=>{assert.equal(id,timer);cleared++;};
   JSON.parse=(...args)=>{parsed++;return realParse(...args);};
   const response={ok:true,headers:{get:()=>null},body:{getReader(){readerOpened++;return{read:()=>new Promise(resolve=>{release=()=>resolve({done:false,value:{get byteLength(){lateBytesRead++;return 1;}}});}),cancel(){cancelled++;return new Promise(()=>{});},releaseLock(){released++;}};}}};
   globalThis.fetch=(_url,options)=>{signal=options.signal;return mode==='headers'?new Promise(resolve=>{release=()=>resolve(response);}):Promise.resolve(response);};
   let readiness=false;const pending=loadManifest().then(()=>{readiness=true;},error=>{assert.equal(error.message,'Practice files unavailable.');});await tick();assert.equal(typeof deadline,'function');deadline();await pending;
   assert(signal.aborted);assert.equal(cleared,1);assert(!readiness);assert.equal(parsed,0);
   if(mode==='body'){assert.equal(cancelled,1);assert.equal(released,1);}
   release();await tick();assert(!readiness);assert.equal(parsed,0);assert.equal(lateBytesRead,0);assert.equal(readerOpened,mode==='body'?1:0);groups++;
  }
  let deadline,cleared=0,signal,cancelled=0,released=0,read=0;
  globalThis.setTimeout=(callback,ms)=>{assert.equal(ms,10000);deadline=callback;return 17;};globalThis.clearTimeout=id=>{assert.equal(id,17);cleared++;};JSON.parse=realParse;
  globalThis.fetch=async(_url,options)=>{signal=options.signal;return{ok:true,headers:{get:()=>null},body:{getReader:()=>({async read(){return read++?{done:true}:{done:false,value:new TextEncoder().encode(JSON.stringify(value))};},cancel(){cancelled++;return Promise.resolve();},releaseLock(){released++;}})}};};
  assert.deepEqual(await loadManifest(),value);assert.equal(cleared,1);assert(signal.aborted);assert.equal(cancelled,1);assert.equal(released,1);assert.equal(typeof deadline,'function');groups++;
  let cancelledOnError=0,releasedOnError=0;globalThis.fetch=async()=>({ok:true,headers:{get:()=>null},body:{getReader:()=>({read:async()=>{throw Error('PRIVATE_TRANSPORT_CANARY');},cancel(){cancelledOnError++;throw Error('PRIVATE_CLEANUP_CANARY');},releaseLock(){releasedOnError++;throw Error('PRIVATE_RELEASE_CANARY');}})}});
  await assert.rejects(loadManifest(),error=>error.message==='Practice files unavailable.');assert.equal(cancelledOnError,1);assert.equal(releasedOnError,1);groups++;
 }finally{globalThis.setTimeout=realSetTimeout;globalThis.clearTimeout=realClearTimeout;JSON.parse=realParse;}
 console.log(JSON.stringify({pass:true,groups,manifest_budget_ms:MANIFEST_TIMEOUT_MS,header_and_body_deadline_abort:true,late_parse_and_readiness_refused:true,overflow_cancelled_before_join_or_decode:true,polite_only:true}));
}finally{globalThis.fetch=original;await fs.rm(tmp,{recursive:true,force:true});}
