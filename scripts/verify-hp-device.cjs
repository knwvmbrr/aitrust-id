/* Actual isolated HP fixture, same-origin CSP, sequential desktop-hosted engines. */
const fs=require('node:fs'),path=require('node:path'),http=require('node:http'),crypto=require('node:crypto');
const {execFileSync}=require('node:child_process');
const {chromium,webkit}=require('playwright');
const {writeReport}=require('./execution-report.cjs');
const {parseHeaders,headersFor}=require('./static-headers.cjs');
const root=path.resolve('output/hp-device-fixture');
const manifest=JSON.parse(fs.readFileSync('site/src/hp-device-manifest.json'));
const cases=JSON.parse(execFileSync(process.env.AITRUST_VERIFY_PYTHON||'python3',['scripts/hp-device-cases.py'],{encoding:'utf8'}));
const workerPath='/assets/'+fs.readdirSync(root+'/assets').find(n=>/^hp-device-worker-.*\.js$/.test(n));
const headers=parseHeaders(fs.readFileSync('site/public/_headers','utf8'));
const sources=['protocol/normalization.mjs','protocol/normalization-core.js','protocol/unicode15-data.json','protocol/normalization.py','LICENSE','NOTICE','eval/vectors/unicode/LICENSE.txt','tools/hp_device.py','tools/quantitative_observations.py','tools/language_observations.py','protocol/corpus.py','scripts/build-hp-device.py','scripts/build-hp-device-fixture.mjs','scripts/hp-device-cases.py','scripts/verify-hp-device.cjs','site/src/HPExplorer.jsx','site/src/HPExplorerSlot.jsx','site/src/hp-device-client.js','site/src/hp-device-worker.js','site/src/hp-device-result.js','site/src/hp-device-manifest.json','site/public'+manifest.path,'site/public/hp-device/notices.txt','tests/test_hp_device.py','tests/hp-device-client.mjs'];
const inventory=()=>Object.fromEntries(sources.map(p=>[p,crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex')]));
const before=inventory();
const assert=(ok,message)=>{if(!ok)throw Error(message);};
const report={captured_at:new Date().toISOString(),pass:false,profile:'hp-literal-detail-explorer/1.0.0',bundle_sha256:manifest.bundle_sha256,sources:before,physical_device_tested:false,independent_accuracy_evidence:false,engines:[],errors:[]};
const mime={'.html':'text/html','.js':'text/javascript','.mjs':'text/javascript','.css':'text/css','.wasm':'application/wasm','.json':'application/json','.svg':'image/svg+xml','.woff2':'font/woff2','.txt':'text/plain'};
const server=http.createServer((req,res)=>{
 let name;try{name=decodeURIComponent(new URL(req.url,'http://127.0.0.1').pathname);}catch{res.writeHead(400).end();return;}
 const file=path.resolve(root,'.'+(name==='/'?'/index.html':name));
 if(!file.startsWith(root+path.sep)||!fs.existsSync(file)||!fs.statSync(file).isFile()){res.writeHead(404).end();return;}
 res.writeHead(200,{'content-type':mime[path.extname(file)]||'application/octet-stream',...headersFor(headers,name)});fs.createReadStream(file).pipe(res);
});
const instrumentation=()=>{
 window.__hpWorkers=[];const Original=window.Worker;
 window.Worker=class extends Original{constructor(...args){super(...args);this.probe={url:String(args[0]),terminated:false};window.__hpWorkers.push(this.probe);}terminate(){this.probe.terminated=true;super.terminate();}};
};
(async()=>{
 await new Promise(r=>server.listen(0,'127.0.0.1',r));const base='http://127.0.0.1:'+server.address().port;
 try{
  for(const [name,engine] of [['Chromium',chromium],['WebKit',webkit]]){
   let stage='launch',browser;
   try{
    browser=await engine.launch({headless:true});const context=await browser.newContext({viewport:{width:390,height:844},deviceScaleFactor:1});
    await context.addInitScript(instrumentation);const page=await context.newPage();const requests=[],errors=[],logs=[];
    page.on('request',r=>requests.push({url:r.url(),method:r.method(),body:r.postData()}));page.on('pageerror',e=>errors.push(e.message));page.on('console',m=>logs.push(m.text()));
    stage='lazy_mount';await page.goto(base);await page.locator('[data-hp-explorer]').waitFor();
    assert(await page.evaluate(()=>window.__hpWorkers.length)===0,'Worker started at mount');
    assert(!requests.some(r=>/\/device\/runtime|\/hp-device\/method/.test(r.url)),'Runtime or method fetched before explicit run');
    await page.getByRole('button',{name:'Find details',exact:true}).click();await page.getByRole('alert').filter({hasText:'Paste English text'}).waitFor();
    assert(await page.getByLabel('English text',{exact:true}).evaluate(e=>e===document.activeElement),'Missing-input focus');
    stage='full_python_browser_parity';
    const parity=await page.evaluate(async({workerPath,cases})=>{
     const worker=new Worker(workerPath,{type:'module'}),values=[];let sequence=0;
     try{
      await new Promise((resolve,reject)=>{const timer=setTimeout(()=>reject(Error('Runtime load deadline')),45000);worker.onmessage=({data})=>{clearTimeout(timer);data.type==='ready'?resolve():reject(Error('Runtime unavailable'));};worker.onerror=()=>{clearTimeout(timer);reject(Error('Worker error'));};});
      for(const row of cases){values.push(await new Promise((resolve,reject)=>{const id=++sequence,timer=setTimeout(()=>reject(Error('Case deadline')),6000);worker.onmessage=({data})=>{clearTimeout(timer);if(data.id!==id)return reject(Error('Wrong input identity'));resolve(data.type==='result'?data.record:null);};worker.postMessage({id,text:row.text});}));}
      for(let i=0;i<cases.length;i++)if(values[i]){const context=await window.__hpValidation.subject(cases[i].text);window.__hpValidation.validate(values[i],context);}
      return values;
     }finally{worker.terminate();}
    },{workerPath,cases});
    for(let i=0;i<cases.length;i++)assert(JSON.stringify(parity[i])===JSON.stringify(cases[i].expected),'Full native/browser record mismatch: '+cases[i].id);
    stage='form_and_private_details';const input=page.getByLabel('English text',{exact:true});
    await input.fill('PRIVATE_HP_CANARY\nThe total is 12.');await input.press(name==='WebKit'?'Alt+Tab':'Tab');assert(await page.getByRole('button',{name:'Find details',exact:true}).evaluate(e=>e===document.activeElement),'Native keyboard order');await page.keyboard.press('Enter');
    const result=page.getByRole('region',{name:'Detail result'});await result.waitFor({timeout:50000});assert((await result.innerText()).includes('1 literal detail found'),'Literal detail result absent');
    assert(await page.evaluate(()=>window.__hpWorkers.every(w=>w.terminated)),'Completed worker retained');
    assert(!await page.getByLabel('Private detail evidence',{exact:true}).count(),'Private detail rendered automatically');
    await page.getByText('Method and exact positions',{exact:true}).click();const detail=JSON.parse(await page.getByLabel('Private detail evidence',{exact:true}).innerText());assert(detail.original.details.length&&!JSON.stringify(detail).includes('PRIVATE_HP_CANARY'),'Exact evidence missing or includes input');
    await input.fill('The total is 12 [1].');assert(await result.count()===0,'Edited input retained prior result');await page.getByRole('button',{name:'Find details',exact:true}).click();await result.waitFor({timeout:50000});assert((await result.innerText()).includes('1 literal detail found'),'Marked literal result unclear');
    stage='screenshots_and_reflow';for(const label of ['English text'])assert((await page.getByLabel(label,{exact:true}).boundingBox()).height>=44,'Small labeled control target: '+label);
    await page.screenshot({path:'output/verification/hp-device-'+name.toLowerCase()+'-light.png',fullPage:true});
    await page.emulateMedia({colorScheme:'dark'});await page.screenshot({path:'output/verification/hp-device-'+name.toLowerCase()+'-dark.png',fullPage:true});
    await page.setViewportSize({width:320,height:760});await page.evaluate(()=>document.documentElement.style.fontSize='200%');assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'320px enlarged-text overflow');
    for(const label of ['Find details','Clear details'])assert((await page.getByRole('button',{name:label,exact:true}).boundingBox()).height>=44,'Small control target');
    await page.evaluate(()=>document.documentElement.style.fontSize='100%');await page.setViewportSize({width:390,height:844});
    stage='accessibility';await page.evaluate(fs.readFileSync(require.resolve('axe-core/axe.min.js'),'utf8'));const accessibility=await page.evaluate(()=>axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag22aa']}}));assert(accessibility.violations.length===0,'axe issues: '+accessibility.violations.map(v=>v.id).join(','));
    stage='refusal_and_recovery';await input.fill('1 '.repeat(257));await page.getByRole('button',{name:'Find details',exact:true}).click();await page.getByRole('alert').filter({hasText:'couldn’t finish'}).waitFor({timeout:50000});assert(await result.count()===0,'Unavailable became quiet result');
    await input.fill('The total is 12.');await page.getByRole('button',{name:'Find details',exact:true}).click();await result.waitFor({timeout:50000});assert((await result.innerText()).includes('1 literal detail found'),'Refusal prevented recovery');
    await page.getByRole('button',{name:'Clear details',exact:true}).click();assert(await result.count()===0&&(await input.inputValue())==='','Clear retained input/result');
    await input.fill('x'.repeat(8001));await page.getByRole('button',{name:'Find details',exact:true}).click();await page.getByRole('alert').filter({hasText:'8,000'}).waitFor();
    stage='edit_clear_unmount_cancellation';await page.route('**/hp-device/method-*.json',async route=>{await new Promise(r=>setTimeout(r,650));try{await route.continue();}catch{}});
    await input.fill('The total is 12.');await page.getByRole('button',{name:'Find details',exact:true}).click();await input.fill('New text');await page.waitForTimeout(900);assert(await result.count()===0&&await page.evaluate(()=>window.__hpWorkers.every(w=>w.terminated)),'Edited input received stale result');
    await page.getByRole('button',{name:'Find details',exact:true}).click();await page.getByRole('button',{name:'Clear details',exact:true}).click();await page.waitForTimeout(900);assert(await result.count()===0&&await page.evaluate(()=>window.__hpWorkers.every(w=>w.terminated)),'Clear left a worker/result');
    await input.fill('The total is 12.');await page.getByRole('button',{name:'Find details',exact:true}).click();await page.getByRole('button',{name:'Unmount preview',exact:true}).click();await page.waitForTimeout(900);assert(await page.evaluate(()=>window.__hpWorkers.every(w=>w.terminated)),'Unmount left a worker');await page.getByRole('button',{name:'Mount preview',exact:true}).click();
    stage='privacy';const storage=await page.evaluate(async()=>({local:Object.keys(localStorage),session:Object.keys(sessionStorage),caches:await caches.keys(),databases:typeof indexedDB.databases==='function'?(await indexedDB.databases()).map(v=>v.name):null}));
    assert(!storage.local.length&&!storage.session.length&&!storage.caches.length&&(storage.databases===null||!storage.databases.length),'Input/application storage appeared');
    assert(requests.every(r=>r.url.startsWith(base)&&r.method==='GET'&&!r.body&&!r.url.includes('PRIVATE_HP_CANARY')),'Content left page');assert(!logs.some(v=>v.includes('PRIVATE_HP_CANARY')),'Input in console');assert(!errors.length,'Page errors: '+errors.join(','));
    await context.close();
    stage='invalid_bundle';const failed=await browser.newContext({viewport:{width:390,height:844}});const fp=await failed.newPage();await fp.route('**/hp-device/method-*.json',r=>r.fulfill({status:200,contentType:'application/json',body:'UNTRUSTED_BUNDLE'}));await fp.goto(base);await fp.getByLabel('English text',{exact:true}).fill('The total is 12.');await fp.getByRole('button',{name:'Find details',exact:true}).click();await fp.getByRole('alert').filter({hasText:'couldn’t finish'}).waitFor({timeout:50000});assert(await fp.getByRole('region',{name:'Detail result'}).count()===0,'Invalid bundle became a result');await fp.getByRole('button',{name:'Other tool probe',exact:true}).click();await fp.getByRole('button',{name:'Other tool remains available',exact:true}).waitFor();await failed.close();
    stage='import_render_isolation';const broken=await browser.newContext();const bp=await broken.newPage();await bp.goto(base);await bp.locator('[data-hp-explorer]').waitFor();for(const probe of ['Import failure probe','Render failure probe']){await bp.getByRole('button',{name:probe,exact:true}).click();await bp.locator('[data-hp-unavailable]').waitFor();await bp.getByRole('button',{name:/Other tool (?:probe|remains available)/}).click();await bp.getByRole('button',{name:'Other tool remains available',exact:true}).waitFor();await bp.getByRole('button',{name:'Restore preview',exact:true}).click();await bp.locator('[data-hp-explorer]').waitFor();}await broken.close();
    stage='actual_missing_chunk';const missing=await browser.newContext();const mp=await missing.newPage();await mp.route('**/assets/HPExplorer-*.js',r=>r.fulfill({status:404,contentType:'text/javascript',body:'Unavailable'}));await mp.goto(base);await mp.locator('[data-hp-unavailable]').waitFor();assert(await mp.locator('[data-hp-explorer]').count()===0,'Missing chunk rendered broken HP');await mp.getByRole('button',{name:'Other tool probe',exact:true}).click();await mp.getByRole('button',{name:'Other tool remains available',exact:true}).waitFor();await missing.close();
    stage='oversized_bundle';const oversized=await browser.newContext();const op=await oversized.newPage();await op.route('**/hp-device/method-*.json',r=>r.fulfill({status:200,contentType:'application/json',body:'x'.repeat(1000001)}));await op.goto(base);await op.getByLabel('English text',{exact:true}).fill('The total is 12.');await op.getByRole('button',{name:'Find details',exact:true}).click();await op.getByRole('alert').filter({hasText:'couldn’t finish'}).waitFor({timeout:50000});assert(await op.getByRole('region',{name:'Detail result'}).count()===0,'Oversized bundle became result');await oversized.close();
    stage='corrupt_result_privacy';const corruptionModes=['wrong_subject','unknown_raw','invalid_span','inner_source','wrong_count'];
    for(const mode of corruptionModes){
     const corrupt=await browser.newContext();const baseline=cases.find(c=>c.id==='unmarked').expected;
     await corrupt.addInitScript(({mode,baseline})=>{window.__corruptTerminated=false;window.Worker=class{constructor(){setTimeout(()=>this.onmessage?.({data:{type:'ready'}}),0);}postMessage({id}){const record=structuredClone(baseline);if(mode==='unknown_raw')record.original.raw_input='SYNTHETIC_PRIVATE_CANARY';if(mode==='invalid_span')record.original.details[0].span=[-100,999999];if(mode==='inner_source')record.original.source_file_sha256['tools/quantitative_observations.py']='0'.repeat(64);if(mode==='wrong_count')record.subject_characters++;this.onmessage?.({data:{type:'result',id,record}});}terminate(){window.__corruptTerminated=true;}};},{mode,baseline});
     const cp=await corrupt.newPage(),privateLogs=[];cp.on('console',m=>privateLogs.push(m.text()));await cp.goto(base);await cp.getByLabel('English text',{exact:true}).fill(mode==='wrong_subject'?'A plain unrelated paragraph.':'The total is 12.');await cp.getByRole('button',{name:'Find details',exact:true}).click();await cp.getByRole('alert').filter({hasText:'couldn’t finish'}).waitFor({timeout:8000});
     assert(await cp.getByRole('region',{name:'Detail result'}).count()===0&&await cp.getByLabel('Private detail evidence',{exact:true}).count()===0,'Corrupt result reached rendering/details: '+mode);assert(!(await cp.locator('body').innerText()).includes('SYNTHETIC_PRIVATE_CANARY')&&!privateLogs.some(m=>m.includes('SYNTHETIC_PRIVATE_CANARY')),'Unknown raw field leaked: '+mode);assert(await cp.evaluate(()=>window.__corruptTerminated),'Corrupt-result worker remained active');await cp.getByRole('button',{name:'Other tool probe',exact:true}).click();await cp.getByRole('button',{name:'Other tool remains available',exact:true}).waitFor();await corrupt.close();
    }
    stage='unsupported_worker';const unsupported=await browser.newContext();await unsupported.addInitScript(()=>window.Worker=undefined);const up=await unsupported.newPage();await up.goto(base);await up.getByLabel('English text',{exact:true}).fill('The total is 12.');await up.getByRole('button',{name:'Find details',exact:true}).click();await up.getByRole('alert').filter({hasText:'couldn’t finish'}).waitFor();await unsupported.close();
    stage='evaluation_deadline';const timeout=await browser.newContext();await timeout.addInitScript(()=>window.Worker=class{constructor(){setTimeout(()=>this.onmessage?.({data:{type:'ready'}}),0);}postMessage(){}terminate(){window.__terminatedProbe=true;}});const tp=await timeout.newPage();await tp.goto(base);await tp.getByLabel('English text',{exact:true}).fill('The total is 12.');await tp.getByRole('button',{name:'Find details',exact:true}).click();await tp.getByRole('alert').filter({hasText:'couldn’t finish'}).waitFor({timeout:8000});assert(await tp.evaluate(()=>window.__terminatedProbe),'Evaluation timeout left worker');await timeout.close();
    report.engines.push({name,pass:true,full_native_python_record_parity:cases.length,requested_input_frozen_nfc_identity_bound:true,closed_original_records_validated:true,corrupt_results_refused_before_render:5,default_no_analysis:true,separate_per_run_worker_terminated:true,detail_cap_refusal_then_valid_input_recovered:true,private_details_opt_in:true,edit_clear_unmount_cancelled:true,invalid_bundle_refused:true,unsupported_worker_refused:true,evaluation_deadline_refused:true,other_tool_probe_survived:true,hp_import_and_render_failure_contained:true,actual_missing_hp_chunk_contained:true,oversized_bundle_refused:true,keyboard_navigation:name==='WebKit'?'Option+Tab (Safari full-control navigation)':'Tab',actual_ps_worker_retested:false,no_input_in_requests_storage_console:true,reflow_320_at_200_percent:true,labeled_controls_minimum_44px:true,axe_violations:0,storage});
   }catch(error){report.errors.push({engine:name,stage,message:error.message});throw error;}
   finally{await browser?.close();}
  }
  assert(JSON.stringify(before)===JSON.stringify(inventory()),'Source changed during browser check');report.source_unchanged_during_execution=true;report.pass=true;
 }catch{process.exitCode=1;}
 finally{await new Promise(r=>server.close(r));writeReport(process.env.AITRUST_HP_DEVICE_REPORT||'output/verification/hp-device-browser.json',report);console.log(JSON.stringify(report,null,2));}
})();
