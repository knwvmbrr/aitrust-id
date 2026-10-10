const {writeReport}=require('./execution-report.cjs');
const fs=require('node:fs');
const assert=require('node:assert/strict');
const {chromium}=require('playwright');
const base=process.env.AITRUST_SITE_URL||'http://127.0.0.1:5174';
(async()=>{
 const {allTags}=await import('../site/src/catalog.js');
 const {performanceFor,validateEvidence}=await import('../site/src/performance-model.js');
 const evidence=JSON.parse(fs.readFileSync('eval/tag-performance-evidence.json','utf8'));
 const hash=p=>require('node:crypto').createHash('sha256').update(fs.readFileSync(p)).digest('hex');
 validateEvidence(evidence,hash);
 for(const change of [d=>d.method_sha256='0'.repeat(64),d=>d.counts.fp=1,d=>d.metrics[0].denominator++,d=>d.independently_labeled=true,d=>d.metrics[0].interval=[1,0],d=>d.metrics[0].interval=[.99,1],d=>d.category_metrics=[],d=>d.category_metrics.push(d.category_metrics[0]),d=>d.category_source_sha256='0'.repeat(64),d=>d.measurement_source_sha256='0'.repeat(64),d=>d.category_metrics[0].precision.interval=[.99,1],d=>d.category_metrics[0].calibration.ece=0,d=>d.mobile.engines[0].timing.p95_ms=999999,d=>d.mobile.engines[0].timing.samples.pop()]){const bad=structuredClone(evidence);change(bad);assert.throws(()=>validateEvidence(bad,hash));}
 for(const tag of allTags.filter(t=>t.id!=='PS')){const row=performanceFor(tag,evidence);assert.equal(row.accuracy_measured,false);assert.equal(row.metrics.length,0);assert.ok(row.next_test);}
 const categories=performanceFor(allTags.find(t=>t.id==='PS'),evidence).categories;assert.equal(categories.length,6);assert.equal(categories.reduce((n,c)=>n+c.n,0),86);
 const browser=await chromium.launch({headless:true});const violations=[],errors=[],outbound=[],transportErrors=[];
 const report={captured_at:new Date().toISOString(),base,pass:false,modals:0,static_pages:0,missing_data_not_zero:true,stale_evidence_rejected:true,automatic_collection_added:false};
 try{
  const context=await browser.newContext({viewport:{width:390,height:844},bypassCSP:true});const page=await context.newPage();page.on('pageerror',e=>errors.push(e.message));page.on('requestfailed',r=>transportErrors.push({url:r.url(),failure:r.failure()}));page.on('response',r=>{if(r.status()>=400)transportErrors.push({url:r.url(),status:r.status()});});page.on('request',r=>{if(!r.url().startsWith(base)&&!r.url().startsWith('data:'))outbound.push(r.url());});
  for(const theme of ['light','dark']){
   await page.goto(base);await page.getByRole('heading',{name:'AI TRUST ID',exact:true}).waitFor();await page.getByRole('switch',{name:'Dark mode',exact:true}).setChecked(theme==='dark');
   for(const tag of allTags){
    await page.goto(base+'/#'+tag.audience+'/'+tag.id);const panel=page.getByRole('region',{name:'Tag performance',exact:true});await panel.waitFor();
    const text=await panel.innerText();assert.ok(text.includes('Independent release validation: pending.'));
    if(tag.id==='PS'){await page.getByRole('dialog').locator('summary').filter({hasText:'Testing and evidence'}).click();assert.ok(text.includes('31/31')&&text.includes('89.0%')&&text.includes('93.0%'));assert.equal(await panel.locator('.performance-track').count(),2);assert.ok((await page.getByRole('dialog').innerText()).includes('iPhone WebKit')&&(await page.getByRole('dialog').innerText()).includes('Android Chromium'));
     const breakdown=page.getByRole('dialog').locator('summary').filter({hasText:/^Test breakdown$/}).locator('..');await breakdown.locator('summary').click();assert.equal(await breakdown.locator('dt').count(),6);for(const c of categories)assert.ok((await breakdown.innerText()).includes(c.label));
     const downloadEvent=page.waitForEvent('download');await page.getByRole('dialog').getByRole('link',{name:'Download measured data',exact:true}).click();const value=JSON.parse(fs.readFileSync(await(await downloadEvent).path(),'utf8'));assert.deepEqual(value.counts,evidence.counts);assert.equal(value.release_validated,false);
    }else{assert.equal(await panel.locator('.performance-track').count(),0);assert.ok(text.includes('not measured')||text.includes('No measured results'));assert.ok(!text.includes('100.0%'));}
    await panel.scrollIntoViewIfNeeded();await page.addScriptTag({path:require.resolve('axe-core/axe.min.js')});const a=await page.evaluate(()=>axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag22aa']}}));violations.push(...a.violations.map(v=>v.id));
    await page.setViewportSize({width:320,height:760});await page.evaluate(()=>document.documentElement.style.fontSize='200%');assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'Performance chart overflow');await page.evaluate(()=>document.documentElement.style.fontSize='');await page.setViewportSize({width:390,height:844});
    report.modals++;
   }
  }
  const nojs=await browser.newContext({javaScriptEnabled:false});const reference=await nojs.newPage();
  for(const tag of allTags){const path=tag.id.toLowerCase().replaceAll('_','-');await reference.goto(base+'/tags/'+path+'/');assert.equal(await reference.locator('[data-tag-performance]').count(),1);if(tag.id==='PS'){assert.ok((await reference.locator('[data-tag-performance]').innerText()).includes('31/31'));const breakdown=reference.locator('[data-tag-performance] details');assert.equal(await breakdown.locator('dt').count(),6);}report.static_pages++;}
  await nojs.close();assert.deepEqual(errors,[]);assert.deepEqual(outbound,[]);assert.deepEqual(violations,[]);report.pass=true;
 }catch(error){report.error=error.message;process.exitCode=1;}finally{await browser.close();report.errors=errors;report.transport_errors=transportErrors;report.outbound=outbound;report.axe_violations=violations;writeReport(process.env.AITRUST_PERFORMANCE_REPORT||'output/verification/performance-ui-local.json',report);console.log(JSON.stringify(report,null,2));}
})().catch(error=>{console.error(error);process.exitCode=1;});
