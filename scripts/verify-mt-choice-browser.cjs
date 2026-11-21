/* Finite local-only practice proof; not physical-device or independent accuracy. */
const fs=require('node:fs'),path=require('node:path'),http=require('node:http'),crypto=require('node:crypto');
const {execFileSync}=require('node:child_process');const {chromium,webkit}=require('playwright');
const folder=path.resolve(process.env.AITRUST_CHOICE_FIXTURE||'output/mt-choice-browser-frozen');
const destination=process.env.AITRUST_CHOICE_REPORT||'output/verification/mt-choice-browser.json';
const manifest=JSON.parse(fs.readFileSync(folder+'/manifest.json'));
const cases=JSON.parse(execFileSync(process.env.AITRUST_VERIFY_PYTHON||'python3',['scripts/mt-choice-browser-cases.py'],{encoding:'utf8'}));
const files=[...Object.keys(manifest.build_inputs),'scripts/mt-choice-browser-cases.py','scripts/verify-mt-choice-browser.cjs','tests/test_mt_choice_device.py','tests/mt-choice-client.mjs','docs/mt-choice-browser-plan.md'];
const digest=p=>crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');const inventory=()=>Object.fromEntries([...new Set(files)].sort().map(p=>[p,digest(p)]));const before=inventory();
const assert=(ok,message)=>{if(!ok)throw Error(message);};
const report={captured_at:new Date().toISOString(),pass:false,profile:'mt-choice-practice-browser/v1',source_sha256:before,artifact_manifest_sha256:digest(folder+'/manifest.json'),runtime:'314.0.7',engines:[],physical_phone_tested:false,independent_accuracy_evidence:false,production_deployed:false};
const types={'.html':'text/html','.mjs':'text/javascript','.css':'text/css','.json':'application/json','.wasm':'application/wasm','.svg':'image/svg+xml','.txt':'text/plain','.md':'text/plain','.zip':'application/zip'};
const server=http.createServer((req,res)=>{
 let name;try{name=decodeURIComponent(new URL(req.url,'http://127.0.0.1').pathname);}catch{res.writeHead(400).end();return;}
 const file=path.resolve(folder,'.'+(name==='/'?'/index.html':name));
 if(req.method!=='GET'||!file.startsWith(folder+path.sep)||!fs.existsSync(file)||!fs.statSync(file).isFile()){res.writeHead(404).end();return;}
 res.writeHead(200,{'content-type':types[path.extname(file)]||'application/octet-stream','cache-control':'no-store','x-content-type-options':'nosniff'});fs.createReadStream(file).pipe(res);
});
const instrument=()=>{window.__choiceWorkers=[];const Real=window.Worker;window.Worker=class extends Real{constructor(...args){super(...args);this.state={terminated:false};window.__choiceWorkers.push(this.state);}terminate(){this.state.terminated=true;super.terminate();}};};
function compareRecord(actual,expected){
 assert(actual.original.runtime.implementation==='CPython'&&actual.original.runtime.python_version===manifest.python_version,'Wrong pinned Python runtime');
 const nativeRuntime=expected.original.runtime,browserRuntime=actual.original.runtime;
 const normalized=structuredClone(expected);normalized.original.runtime=browserRuntime;
 assert(JSON.stringify(actual)===JSON.stringify(normalized),'Canonical record differs beyond disclosed native/browser runtime metadata');
 return {native:nativeRuntime,browser:browserRuntime};
}
(async()=>{
 await new Promise(r=>server.listen(0,'127.0.0.1',r));const base='http://127.0.0.1:'+server.address().port;
 let stage='start',activeEngine;
 try{
  for(const [name,engine]of[['Chromium',chromium],['WebKit',webkit]]){
   activeEngine=name;let browser;
   try{
    stage='launch';browser=await engine.launch({headless:true});const context=await browser.newContext({viewport:{width:390,height:844}});await context.addInitScript(instrument);
    const page=await context.newPage(),requests=[],logs=[];page.on('request',r=>requests.push({url:r.url(),method:r.method(),body:r.postData()}));page.on('console',m=>logs.push(m.text()));
    stage='default_no_analysis';await page.goto(base);await page.waitForFunction(()=>!document.querySelector('#check').disabled);
    assert(await page.evaluate(()=>window.__choiceWorkers.length)===0,'Worker launched before Check');
    assert(!requests.some(r=>r.url.includes('/runtime/')||r.url.includes('/method-')),'Runtime/method fetched before Check');
    stage='full_canonical_worker_records';
    const records=await page.evaluate(async cases=>{
     const manifest=await(await fetch('./manifest.json')).json();const {choiceContext,validateChoice}=await import('./mt-choice-result.mjs');
     const worker=new Worker('./mt-choice-worker.mjs',{type:'module'}),records=[];
     try{
      await new Promise((resolve,reject)=>{const timer=setTimeout(()=>reject(Error('Runtime deadline')),45000);worker.onerror=()=>{clearTimeout(timer);reject(Error('Worker startup'));};worker.onmessage=({data})=>{clearTimeout(timer);data.type==='ready'?resolve():reject(Error('Runtime unavailable'));};});
      for(let i=0;i<cases.length;i++){
       const value=await new Promise((resolve,reject)=>{const timer=setTimeout(()=>reject(Error('Case deadline')),6000);worker.onmessage=({data})=>{clearTimeout(timer);data.type==='result'&&data.id===i+1?resolve(data.record):reject(Error('Case unavailable'));};worker.postMessage({id:i+1,request:cases[i].wire});});
       const bound=await choiceContext(cases[i].request,manifest);validateChoice(value,bound.context,manifest);records.push(value);
      }return records;
     }finally{worker.terminate();}
    },cases);
    const runtimeMetadata=records.map((row,i)=>compareRecord(row,cases[i].expected));
    stage='actual_practice_and_consent';const privacyCase=cases.find(c=>c.id==='privacy_prefix');
    await page.locator('#subject').fill(privacyCase.request.subject);await page.locator('#first').fill('tea');await page.locator('#second').fill('coffee');await page.locator('#reference').fill(privacyCase.request.reference);
    const count=await page.evaluate(()=>window.__choiceWorkers.length);await page.getByRole('button',{name:'Check selected wording',exact:true}).click();await page.locator('#unavailable').waitFor();assert(await page.evaluate(()=>window.__choiceWorkers.length)===count,'Missing declaration launched a worker');
    await page.locator('#whole-frame').check();await page.getByRole('button',{name:'Check selected wording',exact:true}).click();const result=page.getByRole('region',{name:'Selected wording result'});await result.waitFor({timeout:52000});
    assert((await result.innerText()).includes('Additive wording observed'),'Additive brief missing');assert(await page.getByLabel('Private selected wording evidence',{exact:true}).count()===0,'Private evidence mounted by default');
    assert(await page.evaluate(()=>window.__choiceWorkers.every(w=>w.terminated)),'Completed worker retained');
    await page.getByRole('button',{name:'Show exact record',exact:true}).click();const actual=JSON.parse(await page.getByLabel('Private selected wording evidence',{exact:true}).innerText());compareRecord(actual,privacyCase.expected);assert(!JSON.stringify(actual).includes('PRIVATE_MT_CHOICE_CANARY'),'Exact record contains source text');
    await page.getByRole('button',{name:'Hide exact record',exact:true}).click();assert(await page.getByLabel('Private selected wording evidence',{exact:true}).count()===0,'Closed details remain mounted');
    stage='appearance_and_reflow';await page.screenshot({path:'output/verification/mt-choice-'+name.toLowerCase()+'-light.png',fullPage:true});await page.emulateMedia({colorScheme:'dark'});await page.screenshot({path:'output/verification/mt-choice-'+name.toLowerCase()+'-dark.png',fullPage:true});
    await page.setViewportSize({width:320,height:760});await page.evaluate(()=>document.documentElement.style.fontSize='200%');assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'Enlarged text overflows');await page.evaluate(()=>document.documentElement.style.fontSize='100%');await page.setViewportSize({width:390,height:844});
    for(const id of ['subject','first','second','reference','check','clear','example'])assert((await page.locator('#'+id).boundingBox()).height>=44,'Small target: '+id);
    await page.evaluate(fs.readFileSync(require.resolve('axe-core/axe.min.js'),'utf8'));const a11y=await page.evaluate(()=>axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag22aa']}}));assert(a11y.violations.length===0,'Accessibility issues: '+a11y.violations.map(v=>v.id).join(','));
    stage='edit_clear_and_whole_oversized_paste';await page.locator('#subject').fill('x'.repeat(2001));assert(!await result.isVisible(),'Old result survived editing');const beforeBig=await page.evaluate(()=>window.__choiceWorkers.length);await page.getByRole('button',{name:'Check selected wording',exact:true}).click();await page.locator('#unavailable').waitFor();assert((await page.locator('#subject').inputValue()).length===2001&&await page.evaluate(()=>window.__choiceWorkers.length)===beforeBig,'Oversized input clipped or launched');
    await page.getByRole('button',{name:'Clear practice',exact:true}).click();assert(await page.locator('#subject').inputValue()===''&&!await page.locator('#whole-frame').isChecked(),'Clear retained input');
    stage='legacy_form_and_example_requires_declaration';await page.locator('#example').selectOption('either');assert(!await page.locator('#whole-frame').isChecked(),'Example accepted declaration');await page.locator('#whole-frame').check();await page.getByRole('button',{name:'Check selected wording',exact:true}).click();await result.waitFor({timeout:52000});assert((await result.innerText()).includes('Paired wording observed'),'Legacy form unavailable');
    stage='storage_and_network_boundary';const storage=await page.evaluate(async()=>({local:Object.keys(localStorage),session:Object.keys(sessionStorage),indexed:await indexedDB.databases(),caches:await caches.keys()}));assert(!storage.local.length&&!storage.session.length&&!storage.indexed.length&&!storage.caches.length,'Storage created');
    assert(requests.every(r=>r.url.startsWith(base)&&r.method==='GET'&&!r.body&&!r.url.includes('PRIVATE_MT_CHOICE_CANARY')),'Input-bearing or external request');assert(!logs.some(s=>s.includes('PRIVATE_MT_CHOICE_CANARY')),'Input in console');
    stage='corrupt_results_before_display';
    for(const mode of ['wrong_request','raw_extra','kind','marker','quiet_omission']){
     const bad=await browser.newContext();await bad.addInitScript(({mode,baseline})=>{window.__stopped=false;window.Worker=class{constructor(){setTimeout(()=>this.onmessage?.({data:{type:'ready'}}),0);}postMessage({id}){const record=structuredClone(baseline);if(mode==='wrong_request')record.request_sha256='0'.repeat(64);if(mode==='raw_extra')record.original.private_input='PRIVATE_MT_CHOICE_CANARY';if(mode==='kind')record.original.observations[0].construction='either_or';if(mode==='marker')record.original.observations[0].additive_marker_spans[0][0]++;if(mode==='quiet_omission'){record.state=record.original.state='NO_SUPPORTED_PATTERN';record.original.observations=[];record.original.unmatched_selected_frames=[[0,record.subject_characters]];record.counts={matched_frames:0,additive_frames:0,other_paired_frames:0,unmatched_frames:1};}this.onmessage?.({data:{type:'result',id,record}});}terminate(){window.__stopped=true;}};},{mode,baseline:records[0]});
     const p=await bad.newPage();await p.goto(base);await p.waitForFunction(()=>!document.querySelector('#check').disabled);await p.locator('#example').selectOption('additive');await p.locator('#whole-frame').check();await p.getByRole('button',{name:'Check selected wording',exact:true}).click();await p.getByRole('alert').waitFor({timeout:8000});assert(!await p.getByRole('region',{name:'Selected wording result'}).isVisible()&&!await p.getByLabel('Private selected wording evidence',{exact:true}).count()&&await p.evaluate(()=>window.__stopped),'Corrupt result reached display');await bad.close();
    }
    stage='cancel_and_stale_reply';const late=await browser.newContext();await late.addInitScript(baseline=>{window.__stopped=false;window.Worker=class{constructor(){setTimeout(()=>this.onmessage?.({data:{type:'ready'}}),0);}postMessage({id}){window.__lateReply=()=>this.onmessage?.({data:{type:'result',id,record:baseline}});}terminate(){window.__stopped=true;}};},records[0]);
    const lp=await late.newPage();await lp.goto(base);await lp.waitForFunction(()=>!document.querySelector('#check').disabled);await lp.locator('#example').selectOption('additive');await lp.locator('#whole-frame').check();await lp.getByRole('button',{name:'Check selected wording',exact:true}).click();await lp.waitForFunction(()=>Boolean(window.__lateReply));await lp.getByRole('button',{name:'Cancel check',exact:true}).click();await lp.evaluate(()=>window.__lateReply());assert(!await lp.getByRole('region',{name:'Selected wording result'}).isVisible()&&await lp.evaluate(()=>window.__stopped),'Late result revived after Cancel');await late.close();
    stage='source_404_unavailable_then_recovery';const missing=await browser.newContext();await missing.route('**/method-*.json',route=>route.fulfill({status:404,body:'Unavailable'}));const mp=await missing.newPage();await mp.goto(base);await mp.waitForFunction(()=>!document.querySelector('#check').disabled);await mp.locator('#example').selectOption('additive');await mp.locator('#whole-frame').check();await mp.getByRole('button',{name:'Check selected wording',exact:true}).click();await mp.getByRole('alert').waitFor({timeout:52000});assert(!await mp.getByRole('region',{name:'Selected wording result'}).isVisible(),'Unavailable became zero observations');await mp.getByRole('button',{name:'Clear practice',exact:true}).click();assert(await mp.locator('#subject').inputValue()==='','Peer controls disabled');await missing.unroute('**/method-*.json');await mp.locator('#example').selectOption('additive');await mp.locator('#whole-frame').check();await mp.getByRole('button',{name:'Check selected wording',exact:true}).click();await mp.getByRole('region',{name:'Selected wording result'}).waitFor({timeout:52000});await missing.close();
    report.engines.push({name,pass:true,canonical_records:records.length,all_fields_match_except_disclosed_runtime_metadata:true,runtime:runtimeMetadata[0],actual_practice_and_legacy_form:true,default_no_analysis:true,explicit_declaration_required:true,private_details_opt_in:true,completed_worker_terminated:true,edit_clear_and_cancel_stale_guards:true,whole_oversized_input_refused_before_worker:true,corrupt_results_refused_before_display:5,actual_method_404_unavailable_then_recovered:true,other_page_controls_survive:true,no_input_in_requests_storage_console:true,storage,light_dark_and_320px_200percent_reflow:true,axe_violations:0});
    console.log(name+': bounded practice proof passed.');await context.close();
   }finally{await browser?.close();}
  }
  assert(JSON.stringify(before)===JSON.stringify(inventory()),'Source changed during browser proof');report.source_stable=true;report.pass=true;
 }catch(error){report.failure={engine:activeEngine,stage,error_sha256:crypto.createHash('sha256').update(String(error.stack||error)).digest('hex')};fs.writeFileSync(destination.replace(/\.json$/,'.private-error.log'),String(error.stack||error));process.exitCode=1;}
 finally{await new Promise(r=>server.close(r));fs.mkdirSync(path.dirname(destination),{recursive:true});if(fs.existsSync(destination))throw Error('Refuse to overwrite proof');fs.writeFileSync(destination,JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify({pass:report.pass,engines:report.engines.length,failure:report.failure||null,report_sha256:digest(destination)}));}
})();
