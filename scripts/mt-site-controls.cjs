// Actual built-modal integration; method parity remains in the separate fixture.
const fs=require('node:fs');
const crypto=require('node:crypto');
const assert=(ok,message)=>{if(!ok)throw Error(message);};
async function verifyMTSite(browser,base){
 const origin=new URL(base).origin,context=await browser.newContext({viewport:{width:390,height:844}});
 let workerCount=0;const requests=[],errors=[];
 try{
  const page=await context.newPage();
  page.on('worker',()=>workerCount++);page.on('pageerror',e=>errors.push(e.message));
  page.on('request',r=>requests.push({url:r.url(),method:r.method(),body:r.postData()||''}));
  await page.goto(base+'/#person/MT');
  const form=page.locator('[data-mt-explorer]');await form.waitFor();
  assert(await form.getByLabel('Look for',{exact:true}).inputValue()==='','MT selected a method by default');
  assert(workerCount===0,'Opening MT started analysis');
  assert(await form.getByLabel('Look for',{exact:true}).evaluate(el=>el.required)&&await form.getByLabel('English text',{exact:true}).evaluate(el=>el.required),'MT required inputs are not announced');
  assert((await form.innerText()).includes('No MT tag is issued.'),'MT preview lost its tag boundary');
  const cases=[['urgency','Buy now.','Instruction + time wording found'],['authority','The example says "Experts agree".','Authority wording appears in a quote']];
  for(const [kind,text,title] of cases){
   await form.getByLabel('Look for',{exact:true}).selectOption(kind);
   await form.getByLabel('English text',{exact:true}).fill(text);
   await form.getByRole('button',{name:'Explore wording',exact:true}).click();
   const result=form.getByRole('region',{name:'Wording result',exact:true});
   await result.getByRole('heading',{name:title,exact:true}).waitFor({timeout:60000});
   await result.locator('summary').click();
   const record=JSON.parse(await result.getByLabel('Private wording evidence',{exact:true}).innerText());
   assert(record.check===kind&&record.subject_sha256===crypto.createHash('sha256').update(text).digest('hex')&&record.subject_characters===Array.from(text).length,'MT result lost its actual input binding');
   assert(record.tags.length===0&&record.intent_established===false&&record.independent_accuracy_evidence===false&&record.subject_text_included===false,'MT emitted an unsupported claim');
   assert(!JSON.stringify(record).includes(text),'MT details copied the submitted text');
   await result.locator('summary').click();
  }
  await page.setViewportSize({width:320,height:844});
  await page.evaluate(()=>{document.documentElement.style.fontSize='200%';});
  assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),'MT broke narrow enlarged-text reflow');
  const modal=page.getByRole('dialog',{name:'Pressure cues',exact:true});
  assert((await modal.locator('.modal-header').boundingBox()).height<=220,'Enlarged modal header consumes the reading area');
  assert(await form.getByRole('heading',{name:'Authority wording appears in a quote',exact:true}).evaluate(h=>{
   const range=document.createRange();range.setStart(h.firstChild,0);range.setEnd(h.firstChild,'Authority'.length);return range.getClientRects().length===1;
  }),'Enlarged MT result splits ordinary words into fragments');

  fs.mkdirSync('output/playwright',{recursive:true});
  await form.scrollIntoViewIfNeeded();await page.screenshot({path:'output/playwright/mt-production-modal.png'});
  await page.evaluate(()=>{document.documentElement.style.fontSize='';});
  await page.setViewportSize({width:390,height:844});
  await form.evaluate(el=>{
   const modal=el.closest('[data-ai-dialog]'),header=modal.querySelector('.modal-header');
   modal.scrollTop+=el.getBoundingClientRect().top-header.getBoundingClientRect().bottom-8;
  });
  await page.screenshot({path:'output/playwright/mt-production-phone.png'});

  await form.getByRole('button',{name:'Clear wording',exact:true}).click();
  assert(await form.getByLabel('English text',{exact:true}).inputValue()===''&&await form.getByRole('region',{name:'Wording result',exact:true}).count()===0,'MT clear retained private state');
  const guide=await context.request.get(base+'/reference/mt-device-explorer.md');
  assert(guide.status()===200&&(await guide.text())===fs.readFileSync('docs/mt-device-explorer.md','utf8'),'MT guide is missing or stale');
  for(const text of cases.map(row=>row[1])){
   assert(!requests.some(r=>r.url.includes(text)||r.body.includes(text)),'MT submitted input over the network');
   assert(!await page.evaluate(value=>[...Object.values(localStorage),...Object.values(sessionStorage)].some(x=>x.includes(value)),text),'MT persisted input');
  }
  assert(requests.every(r=>['GET','HEAD'].includes(r.method)&&(['data:','blob:'].some(p=>r.url.startsWith(p))||new URL(r.url).origin===origin)),'MT made an unexpected request');
  assert(errors.length===0,'MT raised an unhandled page error');
 }finally{await context.close();}
 // A missing optional MT chunk must leave the existing app and PS route usable.
 const failure=await browser.newContext({viewport:{width:390,height:844}});
 try{
  let refused=false;
  await failure.route(/\/assets\/MTExplorer-[^/]+\.js$/,async route=>{refused=true;await route.fulfill({status:404,contentType:'text/plain',body:'Fixture: optional chunk unavailable'});});
  const page=await failure.newPage();await page.goto(base+'/#person/MT');
  await page.locator('[data-mt-unavailable]').waitFor({timeout:20000});assert(refused,'Missing-chunk control did not intercept the real MT child');
  await page.evaluate(()=>{location.hash='#person/PS';});
  await page.getByRole('dialog',{name:'Command risk',exact:true}).waitFor();
  assert(await page.getByRole('button',{name:'Check on this device',exact:true}).isVisible(),'MT failure disabled PS controls');
 }finally{await failure.close();}
 return {pass:true,actual_methods:2,ordinary_csp_context:true,input_bound_results:true,private_details_opt_in:true,input_upload_observed:false,input_storage_observed:false,missing_mt_chunk_leaves_ps_usable:true,mobile_320_enlarged_text:true,independent_accuracy_evidence:false,physical_phone_tested:false};
}
module.exports={verifyMTSite};
