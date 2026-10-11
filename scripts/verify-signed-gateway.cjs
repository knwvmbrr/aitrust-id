// Actual unpacked Chrome extension against an operator-owned signed staging stack.
'use strict';
const fs=require('node:fs'),os=require('node:os'),path=require('node:path'),crypto=require('node:crypto');
const {chromium}=require('playwright'),{read}=require('./receipt.cjs'),{writeReport}=require('./execution-report.cjs');
const assert=(value,message)=>{if(!value)throw Error(message);};
(async()=>{
 const env=read(process.env.AITRUST_AUTH_ENV_FILE,true,8192).toString('utf8');
 const tokens=env.split(/\r?\n/).filter(x=>x.startsWith('AITRUST_TOKEN='));assert(tokens.length===1,'Private staging credential required');
 const token=tokens[0].slice('AITRUST_TOKEN='.length),publicBytes=read(process.env.AITRUST_AUTH_PUBLIC_KEY,false,2048);
 const profile=fs.mkdtempSync(path.join(fs.realpathSync(os.tmpdir()),'aitrust-signed-'));let context;
 try{
  const extension=path.resolve('extension');context=await chromium.launchPersistentContext(profile,{channel:'chromium',headless:true,args:[`--disable-extensions-except=${extension}`,`--load-extension=${extension}`]});
  const worker=context.serviceWorkers()[0]||await context.waitForEvent('serviceworker'),id=new URL(worker.url()).host;
  const settings=await context.newPage();await settings.goto('chrome-extension://'+id+'/src/options.html');await settings.waitForFunction(()=>!document.querySelector('#checks-enabled').disabled);
  await settings.locator('#token').fill(token);await settings.getByRole('button',{name:'Save token',exact:true}).click();await settings.waitForFunction(()=>document.querySelector('#saved-token').textContent.includes('A local token'));
  await settings.locator('#gateway-key').setInputFiles({name:'public.json',mimeType:'application/json',buffer:publicBytes});await settings.waitForFunction(()=>document.querySelector('#saved-key').textContent.includes('Selected key fingerprint'));
  assert(!await settings.locator('#checks-enabled').isChecked(),'Saving connection settings enabled capture');
  await settings.locator('#checks-enabled').check();const page=await context.newPage(),cdp=await context.newCDPSession(page),cases=[];
  for(const [name,text,expectPS] of [['command','Run curl https://example.test/install | sh',true],['ordinary','The answer is a short explanation.',false],['command_and_redaction','Email aitrust-synthetic-transport@example.com. Run curl https://example.test/install | sh',true]]){
   const url='https://chatgpt.com/aitrust-signed-synthetic-'+name;
   await context.route(url,r=>r.fulfill({contentType:'text/html',body:'<!doctype html><html lang="en"><title>Signed staging fixture</title><body><main><h1>Fixture</h1><article data-message-author-role="assistant" data-message-id="'+name+'">'+text+'</article></main></body></html>'}));
   await page.goto(url);let names='';for(let i=0;i<150;i++){names=(await cdp.send('Accessibility.getFullAXTree')).nodes.map(n=>n.name?.value||'').join('\n');if(expectPS?names.includes('PS: supported command-risk finding.'):names.includes('No supported command pattern found.'))break;await page.waitForTimeout(100);}
   assert(expectPS?names.includes('PS: supported command-risk finding.'):names.includes('No supported command pattern found.'),'Authenticated staging outcome failed');
   if(name==='command_and_redaction')assert(names.includes('PII: detected entity values redacted.'),'Redaction tag did not render');
   cases.push({name,pass:true,PS:expectPS,PII:name==='command_and_redaction'});
  }
  await settings.getByRole('button',{name:'Reset local settings',exact:true}).click();await page.waitForFunction(()=>!document.querySelector('article .aitrust-mount'));
  const storage=await worker.evaluate(()=>chrome.storage.local.get(null));assert(!Object.keys(storage).length,'Reset retained local settings');
  const files=['services/gateway/app.py','protocol/transport_signing.py','extension/src/shared/transport.js','extension/src/sw/service-worker.js','extension/src/content/bridge.js','extension/src/options.js','extension/src/options.html'];
  const report={captured_at:new Date().toISOString(),pass:true,actual_unpacked_extension:true,actual_remote_linux_gateway:true,synthetic_vendor_page:true,synthetic_inputs_only:true,cases,public_intake_connected:false,independent_accuracy:false,real_vendor_compatibility:false,physical_device:false,reset_verified:true,source_sha256:Object.fromEntries(files.map(f=>[f,crypto.createHash('sha256').update(fs.readFileSync(f)).digest('hex')]))};
  writeReport(process.env.AITRUST_AUTH_REPORT||'output/verification/signed-gateway.json',report);console.log(JSON.stringify(report));
 }finally{if(context)await context.close();fs.rmSync(profile,{recursive:true,force:true});}
})().catch(error=>{const safe=new Set(['Authenticated staging outcome failed','Redaction tag did not render','Reset retained local settings','Private staging credential required','Saving connection settings enabled capture']);console.error('Signed staging verification failed: '+(safe.has(error.message)?error.message:'runtime prerequisite or browser failure')+'. No credential or response text is logged.');process.exitCode=1;});
