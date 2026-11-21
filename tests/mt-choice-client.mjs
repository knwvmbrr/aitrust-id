import fs from 'node:fs/promises';import path from 'node:path';import os from 'node:os';import {pathToFileURL} from 'node:url';import {execFileSync} from 'node:child_process';import assert from 'node:assert/strict';
const root=process.cwd(),tmp=await fs.mkdtemp(path.join(os.tmpdir(),'mt-choice-client-'));let groups=0;
try{
 for(const name of ['mt-choice-result.mjs','mt-choice-client.mjs'])await fs.copyFile(path.join(root,'site/src',name),path.join(tmp,name));
 await fs.copyFile(path.join(root,'protocol/normalization.mjs'),path.join(tmp,'normalization.mjs'));
 const {choiceContext,validateChoice,explainChoice}=await import(pathToFileURL(path.join(tmp,'mt-choice-result.mjs')));
 const {choiceClient}=await import(pathToFileURL(path.join(tmp,'mt-choice-client.mjs')));
 const cases=JSON.parse(execFileSync(process.env.AITRUST_VERIFY_PYTHON||'python3',['scripts/mt-choice-browser-cases.py'],{encoding:'utf8'}));
 const manifest={method:'caller-bound-choice-framing-observation/1.3.0',python_version:cases[0].expected.original.runtime.python_version,sources:cases[0].expected.source_sha256};
 for(const item of cases){const {context}=await choiceContext(item.request,manifest);const value=validateChoice(structuredClone(item.expected),context,manifest);assert(explainChoice(value).title);assert(Object.isFrozen(value.original));}groups++;
 const baseline=cases[0],bound=await choiceContext(baseline.request,manifest);
 for(const mode of ['subject','reference','request','source','kind','marker','counts','quiet_omission','raw_extra','bool']){
  const record=structuredClone(baseline.expected);
  if(mode==='subject')record.original.subject_sha256='0'.repeat(64);
  if(mode==='reference')record.original.observations[0].additional_reference.document_sha256='0'.repeat(64);
  if(mode==='request')record.request_sha256='0'.repeat(64);
  if(mode==='source')record.source_sha256['tools/choice_framing.py']='0'.repeat(64);
  if(mode==='kind')record.original.observations[0].construction='either_or';
  if(mode==='marker')record.original.observations[0].additive_marker_spans[0][0]++;
  if(mode==='counts')record.counts.additive_frames=0;
  if(mode==='quiet_omission'){record.state=record.original.state='NO_SUPPORTED_PATTERN';record.original.observations=[];record.original.unmatched_selected_frames=[[0,record.subject_characters]];record.counts={matched_frames:0,additive_frames:0,other_paired_frames:0,unmatched_frames:1};}
  if(mode==='raw_extra')record.original.private_input='PRIVATE_CANARY';
  if(mode==='bool')record.counts.matched_frames=true;
  assert.throws(()=>validateChoice(record,bound.context,manifest),mode);
 }groups++;
 const unicode=cases.find(r=>r.id==='unicode_NFC'),changed={...unicode.request,subject:unicode.request.subject.normalize('NFC')};const rebound=await choiceContext(changed,manifest);assert.throws(()=>validateChoice(structuredClone(unicode.expected),rebound.context,manifest));groups++;
 assert.throws(()=>explainChoice(structuredClone(baseline.expected)));let called=false;const getter=structuredClone(baseline.expected);Object.defineProperty(getter.original.observations[0],'construction',{enumerable:true,get(){called=true;return 'not_only_but_also';}});assert.throws(()=>validateChoice(getter,bound.context,manifest));assert(!called);for(const key of ['frame_span','negation_marker_spans','choice_spans']){const bad=structuredClone(baseline.expected);const array=bad.original.observations[0][key];if(!array.length)array.push([0,3]);Object.defineProperty(array,'0',{enumerable:true,get(){called=true;return key==='frame_span'?0:[0,3];}});assert.throws(()=>validateChoice(bad,bound.context,manifest));assert(!called);}groups++;
 let terminated=0,posted=0;class Good{constructor(){setTimeout(()=>this.onmessage?.({data:{type:'ready'}}),0);}postMessage({id}){posted++;setTimeout(()=>this.onmessage?.({data:{type:'result',id,record:structuredClone(baseline.expected)}}),0);}terminate(){terminated++;}}
 const client=choiceClient(manifest,{createWorker:()=>new Good(),loadTimeout:100,checkTimeout:100});assert((await client.check(baseline.request)).counts.additive_frames===1);assert.equal(terminated,1);assert.equal(posted,1);groups++;
 const invalid=choiceClient(manifest,{createWorker:()=>{throw Error('must not launch');}});await assert.rejects(invalid.check({...baseline.request,whole_frame:false}));await assert.rejects(invalid.check({...baseline.request,subject:'x'.repeat(2001)}));groups++;
 class Late{constructor(){setTimeout(()=>this.onmessage?.({data:{type:'ready'}}),0);}postMessage({id}){setTimeout(()=>this.onmessage?.({data:{type:'result',id,record:structuredClone(baseline.expected)}}),25);}terminate(){terminated++;}}
 const cancelled=choiceClient(manifest,{createWorker:()=>new Late(),loadTimeout:100,checkTimeout:100});const promise=cancelled.check(baseline.request);setTimeout(()=>cancelled.stop(),5);await assert.rejects(promise);await new Promise(r=>setTimeout(r,30));groups++;
 class Never{constructor(){setTimeout(()=>this.onmessage?.({data:{type:'ready'}}),0);}postMessage(){}terminate(){terminated++;}}
 await assert.rejects(choiceClient(manifest,{createWorker:()=>new Never(),loadTimeout:50,checkTimeout:5}).check(baseline.request));groups++;
 console.log(JSON.stringify({pass:true,groups,canonical_cases:cases.length,corrupt_records_refused:10,physical_or_independent_accuracy:false}));
}finally{await fs.rm(tmp,{recursive:true,force:true});}
