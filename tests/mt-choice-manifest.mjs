/* Focused correction controls: manifest allocation boundary and polite failure. */
import fs from 'node:fs/promises';import path from 'node:path';import os from 'node:os';import {pathToFileURL} from 'node:url';import assert from 'node:assert/strict';
const tmp=await fs.mkdtemp(path.join(os.tmpdir(),'mt-choice-manifest-'));const original=globalThis.fetch;let groups=0;
try{
 for(const name of ['mt-choice-result.mjs','mt-choice-client.mjs'])await fs.copyFile(path.join('site/src',name),path.join(tmp,name));
 await fs.copyFile('protocol/normalization.mjs',path.join(tmp,'normalization.mjs'));
 const {loadManifest}=await import(pathToFileURL(path.join(tmp,'mt-choice-client.mjs')));
 const value={format:'mt-choice-practice-manifest/v1',runtime:'314.0.7',method:'caller-bound-choice-framing-observation/1.3.0',runtime_path:'./runtime/',bundle:'method-'+'a'.repeat(64)+'.json',bundle_bytes:1};
 function fake(chunks,header=null){let read=0,cancelled=0,released=0;globalThis.fetch=async()=>({ok:true,headers:{get:()=>header},body:{getReader:()=>({async read(){return read<chunks.length?{value:chunks[read++],done:false}:{done:true};},async cancel(){cancelled++;},releaseLock(){released++;}})},text(){throw Error('Full-body decode forbidden');}});return()=>({read,cancelled,released});}
 let info=fake([new TextEncoder().encode(JSON.stringify(value))]);assert.deepEqual(await loadManifest(),value);assert.equal(info().released,1);groups++;
 for(const header of [null,'1']){info=fake([new Uint8Array(65536),new Uint8Array(1),new Uint8Array(65536)] ,header);await assert.rejects(loadManifest());assert.deepEqual(info(),{read:2,cancelled:1,released:1});}groups++;
 info=fake([new Uint8Array(65537),new Uint8Array(65536)]);await assert.rejects(loadManifest());assert.deepEqual(info(),{read:1,cancelled:1,released:1});groups++;
 info=fake([new Uint8Array(1)],'65537');await assert.rejects(loadManifest());assert.equal(info().read,0);groups++;
 info=fake([Uint8Array.of(0xff)]);await assert.rejects(loadManifest());assert.equal(info().released,1);groups++;
 const html=await fs.readFile('site/src/mt-choice-practice.html','utf8');assert.match(html,/id="unavailable" role="status" aria-live="polite"/);assert(!/role="alert"|aria-live="assertive"/.test(html));groups++;
 console.log(JSON.stringify({pass:true,groups,overflow_cancelled_before_join_or_decode:true,polite_only:true}));
}finally{globalThis.fetch=original;await fs.rm(tmp,{recursive:true,force:true});}
