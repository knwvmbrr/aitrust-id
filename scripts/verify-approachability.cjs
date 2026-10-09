const fs=require('node:fs'),assert=require('node:assert/strict');
const {chromium}=require('playwright');
(async()=>{
 const {allTags}=await import('../site/src/catalog.js');
 const {presentation}=await import('../site/src/presentation.js');
 const base=process.env.AITRUST_SITE_URL||'http://127.0.0.1:5174';
 const browser=await chromium.launch();const context=await browser.newContext({viewport:{width:390,height:844},acceptDownloads:true});
 const page=await context.newPage();const errors=[],transport=[];page.on('pageerror',e=>errors.push(e.message));page.on('requestfailed',r=>transport.push({url:r.url(),error:r.failure()?.errorText}));
 fs.mkdirSync('output/playwright',{recursive:true});
 const records=[];
 try {
  for(const tag of allTags){
   await page.goto(base+'/#'+tag.audience+'/'+tag.id);
   const dialog=page.getByRole('dialog',{name:tag.name,exact:true});await dialog.waitFor();
   const intro=presentation(tag);
   assert.equal(await dialog.locator('[data-tag-summary]').innerText(),intro.summary);
   assert.equal(await dialog.locator('[data-tag-example]').innerText(),'For example: '+intro.example);
   assert.equal(await dialog.locator('[data-tag-limit]').innerText(),intro.limit);
   assert(await dialog.locator('[data-tag-example]').isVisible());
   assert.equal(await dialog.locator('[data-tag-today]').count(),tag.today?1:0);
   const action=await dialog.locator('[data-tag-usage]').boundingBox();const chart=await dialog.locator('[data-tag-performance]').boundingBox();
   assert(action.y<chart.y,'The action should come before performance data: '+tag.id);
   if(tag.id==='PS')assert(await dialog.getByRole('button',{name:'Check on this device',exact:true}).isVisible());
   assert(await dialog.evaluate(e=>e.scrollWidth<=e.clientWidth),'390px overflow: '+tag.id);
   if(['PS','fleet','audit','sso'].includes(tag.id))await page.screenshot({path:'output/playwright/approachable-'+tag.id+'.png'});
   await dialog.locator('summary').filter({hasText:'Privacy and full details'}).click();
   const event=page.waitForEvent('download');await dialog.getByRole('button',{name:'Download details',exact:true}).click();
   const exportFile=await event;const saved=JSON.parse(fs.readFileSync(await exportFile.path(),'utf8'));
   assert.equal(saved.record_type,'catalogue_description');assert.equal(saved.evaluated_result,false);assert.equal(saved.id,tag.id);
   for(const field of Object.keys(tag))assert.deepEqual(saved[field],tag[field]);
   for(const field of ['subject_hash','assertions','abstentions'])assert(!(field in saved));
   await page.goto(base+'/tags/'+tag.id.toLowerCase().replaceAll('_','-')+'/');
   assert.equal(await page.locator('[data-tag-summary]').innerText(),intro.summary);
   assert.equal(await page.locator('[data-tag-example]').innerText(),'For example: '+intro.example);
   if(tag.today)assert.equal(await page.locator('[data-tag-today]').innerText(),tag.today);
   records.push({id:tag.id,introduction:true,everyday_example:true,action_before_chart:true,catalogue_export_distinct:true,complete_fields:true,static_parity:true});
  }
  const nojs=await browser.newContext({javaScriptEnabled:false});const plain=await nojs.newPage();await plain.goto(base);
  assert.equal(await plain.locator('[data-tag-example]').count(),20);await nojs.close();
  assert.equal(errors.length,0,errors.join('; '));
  const report={captured_at:new Date().toISOString(),url:base,records,no_script_examples:20,viewport_width:390,physical_phone:false,human_usability_test:false,errors};
  fs.writeFileSync(process.env.AITRUST_APPROACHABILITY_REPORT||'runs/2026-10-09-approachable-local.json',JSON.stringify(report,null,2)+'\n');
  console.log(JSON.stringify({pass:true,records:records.length,static_parity:20,complete_exports:20,no_script_examples:20}));
 }catch(error){const diagnostics={captured_at:new Date().toISOString(),url:base,pass:false,failed_at_url:page.url(),error:error.message,page_errors:errors,transport,body_excerpt:(await page.locator('body').innerText().catch(()=>'' )).slice(0,1200)};fs.writeFileSync(process.env.AITRUST_APPROACHABILITY_REPORT||'runs/2026-10-09-approachable-local.json',JSON.stringify(diagnostics,null,2)+'\n');throw error;
 }finally{await context.close();await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
