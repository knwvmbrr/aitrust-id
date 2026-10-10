'use strict';
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),os=require('node:os'),assert=require('node:assert/strict');
const {pathToFileURL}=require('node:url');
const {chromium,webkit}=require('playwright');
const {execFileSync}=require('node:child_process');
const root=path.resolve(__dirname,'..');
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
(async()=>{
 const python=process.env.AITRUST_VERIFY_PYTHON||'python3';
 execFileSync(python,['scripts/build-composition-tool.py'],{cwd:root});
 const file=path.join(root,'output/composition/editor.html'),first=fs.readFileSync(file);
 execFileSync(python,['scripts/build-composition-tool.py'],{cwd:root});assert.deepEqual(fs.readFileSync(file),first,'Build is not deterministic');
 const observations=[];
 for(const engine of [chromium,webkit]){
  const browser=await engine.launch();
  try{
   const context=await browser.newContext({viewport:{width:390,height:844}});const page=await context.newPage();
   const requests=[],errors=[];page.on('request',r=>{if(/^https?:/.test(r.url()))requests.push(r.url());});page.on('pageerror',e=>errors.push(e.message));
   await page.addInitScript(()=>{window.storageWrites=0;const original=Storage.prototype.setItem;Storage.prototype.setItem=function(...args){window.storageWrites++;return original.apply(this,args);};});
   await page.goto(pathToFileURL(file).href);assert(await page.locator('#editor').getAttribute('readonly')!==null);
   await page.getByRole('button',{name:'Start',exact:true}).click();
   await page.locator('#editor').pressSequentially('Private synthetic writing.');
   let record=JSON.parse(await page.locator('#summary').textContent());assert.equal(record.timing.status,'suppressed');assert(record.event_count>0);assert.equal(record.final_length,26);
   await page.locator('#editor').press('ControlOrMeta+a');await page.locator('#editor').pressSequentially('New words.');
   record=JSON.parse(await page.locator('#summary').textContent());assert(record.revision.deleted>=26);assert.equal(record.final_length,10);
   await page.getByRole('button',{name:'Pause',exact:true}).click();assert(await page.locator('#editor').getAttribute('readonly')!==null);
   await page.locator('summary').click();
   // Browser evaluation installs test instrumentation; shipped CSP remains enforced.
   await page.evaluate(fs.readFileSync(require.resolve('axe-core/axe.min.js'),'utf8'));
   const axe=await page.evaluate(async()=>await axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21a','wcag21aa']}}));assert.equal(axe.violations.length,0,JSON.stringify(axe.violations.map(x=>x.id)));
   const waiting=page.waitForEvent('download');await page.getByRole('button',{name:'Download this summary',exact:true}).click();
   const exported=JSON.parse(fs.readFileSync(await (await waiting).path(),'utf8'));assert.equal(exported.status,'paused');assert.equal(exported.source_sha256,sha(fs.readFileSync(path.join(root,'tools/composition/core.cjs'))));
   assert.equal(exported.artifact_sha256,sha(Buffer.from('New words.')));
   const artifactWaiting=page.waitForEvent('download');await page.getByRole('button',{name:'Download your text',exact:true}).click();
   const artifact=fs.readFileSync(await(await artifactWaiting).path());assert.equal(artifact.toString(),'New words.');
   const privateDir=fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(),'aitrust-editor-receipt-')));fs.chmodSync(privateDir,0o700);
   try{
    const p=n=>path.join(privateDir,n);fs.writeFileSync(p('artifact.txt'),artifact);fs.writeFileSync(p('observation.json'),JSON.stringify(exported));
    const call=args=>execFileSync(process.execPath,['scripts/receipt.cjs',...args],{cwd:root,env:{...process.env,AITRUST_VERIFY_PYTHON:python},encoding:'utf8'});
    call(['keygen','Ed25519',p('private.pem'),p('public.pem')]);call(['issue',p('artifact.txt'),p('observation.json'),p('private.pem'),p('receipt.json')]);
    const verified=JSON.parse(call(['verify',p('receipt.json'),p('public.pem'),p('artifact.txt')]));assert.equal(verified.artifact_binding,'matched');assert.equal(verified.certified_valid,false);
   }finally{fs.rmSync(privateDir,{recursive:true,force:true});}
   assert.equal(JSON.stringify(exported).includes('Private synthetic'),false);assert.deepEqual(exported.tags,[]);
   // A pending asynchronous hash must not export a session the user just deleted.
   await page.evaluate(()=>{window.originalDigest=crypto.subtle.digest.bind(crypto.subtle);crypto.subtle.digest=(...args)=>new Promise(resolve=>{window.finishDigest=()=>window.originalDigest(...args).then(resolve);});});
   let staleDownloads=0;const stale=()=>staleDownloads++;page.on('download',stale);
   await page.getByRole('button',{name:'Download this summary',exact:true}).click();
   await page.getByRole('button',{name:'Reset and delete',exact:true}).click();assert.equal(await page.locator('#editor').inputValue(),'');assert.equal(JSON.parse(await page.locator('#summary').textContent()).event_count,0);
   await page.evaluate(async()=>{await window.finishDigest();crypto.subtle.digest=window.originalDigest;});
   await page.evaluate(()=>new Promise(resolve=>setTimeout(resolve,100)));assert.equal(staleDownloads,0);page.off('download',stale);
   await page.locator('#mode').selectOption('physical');await page.getByRole('button',{name:'Start',exact:true}).click();await page.locator('#editor').pressSequentially('abcdef');
   record=JSON.parse(await page.locator('#summary').textContent());assert.equal(record.timing.status,'observed');assert(record.timing.samples>=6);
   await page.locator('#editor').evaluate(e=>e.dispatchEvent(new CompositionEvent('compositionstart',{bubbles:true,data:'synthetic'})));
   await page.locator('#editor').pressSequentially('gh');record=JSON.parse(await page.locator('#summary').textContent());assert.equal(record.timing.status,'suppressed');assert.equal(record.timing.samples,0);
   await page.getByRole('button',{name:'Reset and delete',exact:true}).click();
   await page.locator('#mode').selectOption('unknown');await page.getByRole('button',{name:'Start',exact:true}).click();
   await page.locator('#editor').evaluate(e=>{e.dispatchEvent(new InputEvent('beforeinput',{bubbles:true,inputType:'insertFromPaste'}));e.value='p'.repeat(64);e.dispatchEvent(new InputEvent('input',{bubbles:true,inputType:'insertFromPaste'}));});
   record=JSON.parse(await page.locator('#summary').textContent());assert.equal(record.insertion.bursts,1);assert.equal(record.insertion.origin_inferred,false);
   await page.getByRole('button',{name:'Reset and delete',exact:true}).click();
   assert.equal(await page.evaluate(async()=>{try{await fetch('https://example.invalid/blocked');return false;}catch{return true;}}),true,'CSP allowed network access');
   await page.reload();assert.equal(await page.locator('#editor').inputValue(),'');assert.equal(JSON.parse(await page.locator('#summary').textContent()).status,'not_started');
   assert.equal(await page.evaluate(()=>window.storageWrites),0);assert.equal(requests.length,0);assert.deepEqual(errors,[]);
   assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'Mobile overflow');
   observations.push({engine:engine.name(),engine_version:browser.version(),native_typing:true,revision:true,coarse_timing:true,composition_suppression:true,synthetic_paste_instrumentation:true,native_clipboard_test:false,CSP_network_refusal:true,manual_summary_export:true,manual_text_export:true,export_to_offline_receipt:true,reset_cancels_pending_export:true,pause_reset_reload:true,network_requests:0,storage_writes:0,axe_violations:0});
   await context.close();
  }finally{await browser.close();}
 }
 const record={captured_at:new Date().toISOString(),pass:true,method:'composition-observation/1.0.0',sources:Object.fromEntries(['core.cjs','editor.js','editor.html','style.css'].map(n=>['tools/composition/'+n,sha(fs.readFileSync(path.join(root,'tools/composition',n)))])),artifact_sha256:sha(first),deterministic_build:true,observations,actual_physical_phone:false,human_accessibility_review:false,independent_accuracy_evidence:false,tag_release_approved:false};
 execFileSync(python,['-c',"import json,sys;from protocol.reports import write_report;write_report(sys.argv[1],json.load(sys.stdin))",process.env.AITRUST_COMPOSITION_REPORT||'output/verification/composition-tool.json'],{cwd:root,input:JSON.stringify(record)});
 console.log(JSON.stringify(record));
})().catch(e=>{console.error(e);process.exitCode=1;});
