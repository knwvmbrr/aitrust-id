const fs=require('node:fs');
const {chromium}=require('playwright');
const base=process.env.AITRUST_SITE_URL||'http://127.0.0.1:5174';
const scopeIds=JSON.parse(fs.readFileSync('docs/master-scope.json','utf8')).records.map(record=>record.id);
(async()=>{
 const browser=await chromium.launch({channel:'chromium',headless:true});
 try{
  // Axe injection needs a test-only CSP bypass; separately verify the real policy below.
  const context=await browser.newContext({viewport:{width:1440,height:1100},bypassCSP:true,permissions:['clipboard-read','clipboard-write']});const page=await context.newPage();
  const errors=[],outside=[];page.on('pageerror',e=>errors.push(e.message));page.on('request',r=>{if(!r.url().startsWith(base)&&!r.url().startsWith('data:'))outside.push(r.url());});
  const assert=(x,m)=>{if(!x)throw Error(m);};
 async function appearance(target,value){
  if(value==='system'){await target.getByRole('button',{name:'Use device theme',exact:true}).click();return;}
  const control=target.getByRole('switch',{name:'Dark mode',exact:true});
  // An explicit choice must fire a change even if the device already has that theme.
  if(await control.isChecked()===(value==='dark'))await control.setChecked(value!=='dark');
  await control.setChecked(value==='dark');
 }

  await page.goto(base);await page.getByRole('heading',{name:'AI TRUST ID',exact:true}).waitFor();
  await appearance(page,'light');
  await page.evaluate(()=>document.fonts.ready);assert(await page.evaluate(()=>document.fonts.check('16px "Nunito Sans"')),'Self-hosted font not loaded');assert((await page.locator('body').evaluate(e=>getComputedStyle(e).fontFamily)).includes('Nunito Sans'),'Approachable font not applied');
  assert(await page.locator('html').getAttribute('data-theme')==='light','Light preference did not apply');
  assert(await page.locator('[data-tag-id]').count()===14,'Person must default to all 14 records');
  assert(await page.locator('[data-tag-id="PS"]').evaluate(e=>e.getBoundingClientRect().height<=128),'Tags are not compact');
  assert(await page.locator('[data-tag-id="PS"]').innerText()==='PS','Tag tile contains extra visible text');
  assert(await page.getByRole('link',{name:'Tag reference',exact:true}).getAttribute('href')==='/tags/','Crawlable reference link missing');
  await page.addScriptTag({path:require.resolve('axe-core/axe.min.js')});
  let violations=[];async function axe(){if(!await page.evaluate(()=>typeof window.axe!=='undefined'))await page.addScriptTag({path:require.resolve('axe-core/axe.min.js')});const result=await page.evaluate(()=>axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag22aa']}}));violations.push(...result.violations.map(v=>({id:v.id,impact:v.impact,targets:v.nodes.map(n=>n.target)})));}
  await axe();let checked=0;
  for(const audience of ['person','enterprise']){
   await page.getByRole('tab',{name:audience==='person'?'Person':'Enterprise',exact:true}).click();
   const ids=await page.locator('[data-tag-id]').evaluateAll(nodes=>nodes.map(n=>n.dataset.tagId));
   assert(ids.length===(audience==='person'?14:6),'Audience filtering failed');
   for(const id of ids){
    const tile=page.locator(`[data-tag-id="${id}"]`);await tile.click();const dialog=page.getByRole('dialog');await dialog.waitFor();
    assert(await dialog.locator('[data-tag-summary]').innerText()&&await dialog.locator('[data-tag-limit]').innerText(),id+' missing plain-language summary or limitation');
    const validation=await dialog.getByRole('region',{name:'Validation status'}).innerText();assert(validation.includes('Every tag must pass its own published validation gate before release.'),'Release gate missing');assert(validation.includes(['PS','PII_REDACTED'].includes(id)?'Validation in progress':'Validation required before release'),'Wrong validation stage');
    assert(await dialog.locator('details').count()===(['PS','PII_REDACTED'].includes(id)?4:3),id+' must have its compact disclosures and applicable setup');
    const use=dialog.locator('[data-tag-usage]');assert(await use.count()===1,id+' use instructions missing');
    if(['PS','PII_REDACTED'].includes(id)){await use.locator('summary').click();assert(await use.locator('ol li').count()===4,'Setup must have four steps');await use.getByRole('button',{name:'Copy step 1 commands'}).click();assert(await page.evaluate(()=>navigator.clipboard.readText())==='git clone https://github.com/knwvmbrr/aitrust-id.git\ncd aitrust-id','Command copy differs from displayed instructions');await use.locator('summary').click();}
    else{assert((await use.innerText()).includes('Coming Soon')||(await use.innerText()).includes('Research proposal'),'Unavailable tag overclaims installation');assert(await use.getByRole('link',{name:'Download source',exact:true}).count()===0,'Unavailable tag has fake download');}
    assert(await dialog.locator('details[open]').count()===0,id+' details must start collapsed');
    for(const title of ['How it works','Testing and evidence','Privacy, access and all features']){
     const summary=dialog.locator('summary').filter({hasText:title});await summary.focus();await page.keyboard.press('Enter');
     assert(await summary.evaluate(e=>e.parentElement.open),id+' disclosure is not keyboard operable');
    }
    for(const heading of ['What it can say','Method','What has been checked','Privacy','Who is responsible','Before release'])assert(await dialog.getByRole('heading',{name:heading,exact:true}).isVisible(),id+' incomplete');
    if(id==='PS'){
     await dialog.getByRole('button',{name:'Download details',exact:true}).scrollIntoViewIfNeeded();
     const downloadEvent=page.waitForEvent('download');await dialog.getByRole('button',{name:'Download details',exact:true}).click();
     const exported=JSON.parse(fs.readFileSync(await (await downloadEvent).path(),'utf8'));
     const catalog=await import('../site/src/catalog.js');const expected=catalog.allTags.find(t=>t.id==='PS');
     for(const key of Object.keys(expected))assert(JSON.stringify(exported[key])===JSON.stringify(expected[key]),'Full detail export lost '+key);
    }

    if(id==='PS'){
     assert(await dialog.getByRole('link',{name:'Download source',exact:true}).getAttribute('href')==='https://github.com/knwvmbrr/aitrust-id/archive/refs/heads/main.zip','PS download path missing');
     assert(await dialog.getByRole('link',{name:'Try locally',exact:true}).getAttribute('href')==='https://github.com/knwvmbrr/aitrust-id/blob/main/docs/open-validation-path.md','Local installation guide missing');
     await axe();
     await dialog.getByRole('button',{name:'Report an issue',exact:true}).click();const report=page.getByRole('dialog',{name:'Report',exact:true});await report.waitFor();
     await report.getByRole('button',{name:'Download draft',exact:true}).click();assert(await report.getByRole('alert').innerText()==='Describe what happened and what you expected.','Required description not enforced');
     const description=report.getByLabel('What happened?',{exact:true});await description.fill('Synthetic issue <img src=x onerror="window.injected=true">');await report.getByLabel('What did you expect?',{exact:true}).fill('A bounded reproducible finding.');
     assert(await report.getByRole('link',{name:'Open public GitHub report',exact:true}).getAttribute('href')==='https://github.com/knwvmbrr/aitrust-id/issues/new?template=tag-review.yml','Public report destination missing or contains draft data');
     await report.getByLabel('Report type').selectOption('Security or privacy');
     assert(await report.getByRole('link',{name:'Open private security report',exact:true}).getAttribute('href')==='https://github.com/knwvmbrr/aitrust-id/security/advisories/new','Security report routed publicly');
     await report.getByLabel('Report type').selectOption('Wrong or misleading tag');
     await axe();const waiting=page.waitForEvent('download');await report.getByRole('button',{name:'Download draft',exact:true}).click();const item=await waiting;const draft=JSON.parse(fs.readFileSync(await item.path(),'utf8'));
     assert(draft.tag==='PS'&&draft.status==='draft_not_submitted','Draft bound to wrong tag or false submission');assert(!await page.evaluate(()=>window.injected),'Injected content executed');
     await page.keyboard.press('Escape');assert(await page.getByRole('dialog',{name:'Report',exact:true}).count()===0,'Nested Escape failed');
     const reportTrigger=dialog.getByRole('button',{name:'Report an issue'});
     await page.waitForFunction(element=>document.activeElement===element,await reportTrigger.elementHandle());
     assert(await reportTrigger.evaluate(e=>e===document.activeElement),'Nested dialog did not restore focus');
    }
    await page.keyboard.press('Tab');assert(await page.evaluate(()=>document.activeElement.closest('[role=dialog]')!==null),'Focus escaped modal');
    await page.keyboard.press('Escape');await page.waitForFunction(element=>document.activeElement===element,await tile.elementHandle());assert(await tile.evaluate(e=>e===document.activeElement),'Focus not restored to '+id);checked++;
   }
  }
  for(const label of ['Report','Assist','Townhall','Teamwork','How tags work','Scope','About','Legal']){
   const link=page.getByRole('navigation',{name:'Company and community'}).getByRole('link',{name:label,exact:true});await link.click();
   await page.getByRole('dialog',{name:label,exact:true}).waitFor();await axe();await page.keyboard.press('Escape');
   await page.getByRole('dialog',{name:label,exact:true}).waitFor({state:'hidden'});
   await page.waitForFunction(element=>document.activeElement===element,await link.elementHandle());
   assert(await link.evaluate(e=>e===document.activeElement),'Footer focus not restored: '+label);
  }
  const nativeModelContext=await page.evaluate(()=>typeof document.modelContext?.registerTool==='function');
  await page.goto(base+'/#enterprise/proprietary');await page.getByRole('dialog',{name:'Proprietary tag package',exact:true}).waitFor();await page.keyboard.press('Escape');
  await page.goto(base+'/#%E0%A4%A');await page.getByRole('heading',{name:'AI TRUST ID',exact:true}).waitFor();assert(await page.locator('[data-tag-id]').count()===14,'Malformed fragment crashed site');
  await page.setViewportSize({width:320,height:720});await page.goto(base);assert(await page.evaluate(()=>document.documentElement.scrollWidth<=320),'Mobile grid overflow');
  await page.locator('[data-tag-id="PS"]').click();await axe();assert(await page.getByRole('dialog').evaluate(e=>e.scrollWidth<=e.clientWidth),'Mobile modal overflow');
  await page.screenshot({path:'output/playwright/site-mobile-modal.png'});await page.keyboard.press('Escape');
  await page.evaluate(()=>document.documentElement.style.fontSize='32px');assert(await page.evaluate(()=>document.documentElement.scrollWidth<=320),'200% text enlargement overflow');
  await page.locator('[data-tag-id="PS"]').click();assert(await page.getByRole('dialog').evaluate(e=>e.scrollWidth<=e.clientWidth),'200% modal overflow');await page.keyboard.press('Escape');
  const nojs=await browser.newContext({javaScriptEnabled:false});const plain=await nojs.newPage();await plain.goto(base);assert(await plain.locator('details').count()===20,'No-JavaScript tag reference missing');await plain.locator('summary').first().click();assert(await plain.locator('details').first().getAttribute('open')!==null,'No-JavaScript detail not operable');await nojs.close();
  const publicScope=await context.request.get(base+'/reference/public-scope.json');
  const publicIds=(await publicScope.json()).records.map(record=>record.id);
  assert(publicIds.length===scopeIds.length&&new Set(publicIds).size===publicIds.length&&scopeIds.every(id=>publicIds.includes(id)),'Full scope omitted or duplicated');
  await page.setViewportSize({width:1440,height:1100});await page.goto(base);
  await appearance(page,'dark');await axe();
  await page.reload();assert(await page.locator('html').getAttribute('data-theme')==='dark','Dark preference did not persist');
  await page.screenshot({path:'output/playwright/site-redesign-dark.png'});
  for(const id of ['PS','PII_REDACTED']){
   await page.locator(`[data-tag-id="${id}"]`).click();await axe();
   if(id==='PS'){await page.getByRole('button',{name:'Report an issue'}).click();await axe();await page.keyboard.press('Escape');}
   await page.keyboard.press('Escape');
  }
  const sibling=await context.newPage();await sibling.goto(base);await appearance(sibling,'light');
  await page.waitForFunction(()=>document.documentElement.dataset.theme==='light');
  assert(!await page.getByRole('switch',{name:'Dark mode'}).isChecked(),'Cross-tab switch state stale');await sibling.close();
  const themeSwitch=page.getByRole('switch',{name:'Dark mode'});await themeSwitch.focus();await page.keyboard.press('Space');
  assert(await themeSwitch.isChecked(),'Switch not operable by Space');
  await page.getByRole('tab',{name:'Enterprise',exact:true}).click();await axe();
  await page.locator('[data-tag-id="proprietary"]').click();await axe();await page.keyboard.press('Escape');
  await page.emulateMedia({colorScheme:'light'});assert(await page.locator('html').getAttribute('data-theme')==='dark','Explicit preference lost to OS scheme');
  await appearance(page,'system');assert(await page.locator('html').getAttribute('data-theme')==='light','System light preference failed');
  await page.emulateMedia({colorScheme:'dark'});await page.waitForFunction(()=>document.documentElement.dataset.theme==='dark');
  await appearance(page,'light');await page.getByRole('tab',{name:'Person',exact:true}).click();
  await page.screenshot({path:'output/playwright/site-redesign-light.png'});
  await page.setViewportSize({width:320,height:720});await axe();
  await appearance(page,'dark');await axe();
  assert(await page.evaluate(()=>document.documentElement.scrollWidth<=320),'Dark mobile overflow');
  await page.emulateMedia({forcedColors:'active',reducedMotion:'reduce'});
  assert(await page.locator('[data-tag-id="PS"]').evaluate(e=>getComputedStyle(e).borderTopStyle==='solid'),'High-contrast tag boundary missing');
  await page.emulateMedia({forcedColors:'none',reducedMotion:'no-preference'});
  const blocked=await browser.newContext();await blocked.addInitScript(()=>{Object.defineProperty(window,'localStorage',{get(){throw new Error('blocked');}});});
  const blockedPage=await blocked.newPage();await blockedPage.goto(base);await appearance(blockedPage,'dark');assert(await blockedPage.locator('html').getAttribute('data-theme')==='dark','Theme failed with blocked storage');await blocked.close();
  const homeHTML=await (await context.request.get(base+'/')).text();
  assert(homeHTML.includes('<link rel="canonical" href="https://aitrustid.com/"'),'Home canonical missing');
  assert(!homeHTML.includes('noindex'),'Home blocked from indexing');
  const robots=await (await context.request.get(base+'/robots.txt')).text();assert(robots.includes('Allow: /')&&robots.includes('Sitemap: https://aitrustid.com/sitemap.xml'),'Crawler policy missing');
  const sitemap=await (await context.request.get(base+'/sitemap.xml')).text();const canonicalURLs=[...sitemap.matchAll(/<loc>([^<]+)<\/loc>/g)].map(m=>m[1]);
  assert(canonicalURLs.length===32&&new Set(canonicalURLs).size===32,'Sitemap omits or duplicates tag URLs');
  const canonicalTitles=new Set();const canonicalDescriptions=new Set();
  for(const url of canonicalURLs){
   const response=await context.request.get(base+new URL(url).pathname);assert(response.status()===200,'Crawlable page not served: '+url);
   const html=await response.text();assert(html.includes(`<link rel="canonical" href="${url}"`),'Wrong canonical: '+url);
   const title=html.match(/<title>(.*?)<\/title>/)?.[1];assert(title&&!canonicalTitles.has(title),'Missing or duplicate title');canonicalTitles.add(title);const description=html.match(/<meta name="description" content="([^"]+)"/)?.[1];assert(description&&!canonicalDescriptions.has(description),'Missing or duplicate description');canonicalDescriptions.add(description);
   const json=html.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/)?.[1];const data=JSON.parse(json);assert(data['@context']==='https://schema.org','Structured metadata invalid');
   assert(!json.includes('aggregateRating')&&!json.includes('Review')&&!json.includes('offers'),'Invented commercial/rating metadata');
   if(new URL(url).pathname.startsWith('/tags/'))assert(html.includes('Every tag must pass its own published validation gate before release.'),'Reference drops release rule');assert(!html.includes('No tag is independently release validated, and no certification program is operating.'),'Blanket status copy reintroduced');
   assert(html.includes('property="og:image" content="https://aitrustid.com/share-card.png"'),'Share image metadata missing');
  }
  const share=await context.request.get(base+'/share-card.png');const png=await share.body();assert(share.status()===200&&png.readUInt32BE(16)===1200&&png.readUInt32BE(20)===630,'Social PNG missing or wrong size');
  const plainReferences=await browser.newContext({javaScriptEnabled:false});const staticPage=await plainReferences.newPage();
  await staticPage.goto(base+'/tags/');assert(await staticPage.locator('main a[href^="/tags/"]').count()===20,'No-script index cannot discover every tag');
  await staticPage.goto(base+'/tags/ps/');assert(await staticPage.getByRole('heading',{name:'PS — Command risk',exact:true}).count()===1,'No-script PS reference missing');assert(await staticPage.getByRole('heading',{name:'Accuracy and validation',exact:true}).count()===1,'No-script reference incomplete');await plainReferences.close();
  await page.setViewportSize({width:1440,height:1100});await page.goto(base+'/tags/ps/');await axe();await appearance(page,'light');await axe();
  assert(errors.length===0,'Browser errors: '+errors.join('; '));assert(outside.length===0,'Unexpected outbound traffic: '+JSON.stringify([...new Set(outside)]));assert(violations.length===0,'Accessibility violations: '+JSON.stringify(violations));
  let productionPolicyVerified=false;
  if(base.startsWith('https://')){
   const ordinary=await browser.newContext();const normal=await ordinary.newPage();
   const response=await normal.goto(base);const headers=response.headers();
   assert(headers['content-security-policy']?.includes("script-src 'self'"),'Production CSP missing');
   assert(headers['x-content-type-options']==='nosniff','Production nosniff missing');
   assert(headers['referrer-policy']==='no-referrer','Production referrer policy missing');
   assert(headers['x-frame-options']==='DENY','Production framing restriction missing');
   assert(headers['cache-control']?.includes('no-transform'),'Production no-transform missing');
   await normal.locator('[data-tag-id="PS"]').click();await normal.getByRole('dialog',{name:'Command risk',exact:true}).waitFor();
   await normal.keyboard.press('Escape');await normal.getByRole('tab',{name:'Enterprise',exact:true}).click();
   assert(await normal.locator('[data-tag-id]').count()===6,'Production CSP blocked catalogue interaction');
   await appearance(normal,'dark');
   assert(await normal.locator('html').getAttribute('data-theme')==='dark','Production CSP blocked theme control');
   await normal.goto(base+'/tags/ps/');
   assert(await normal.getByRole('heading',{name:'PS — Command risk',exact:true}).count()===1,'Production reference not available');
   assert(await normal.locator('html').getAttribute('data-theme')==='dark','Production reference lost theme preference');
   const missing=await ordinary.request.get(base+'/tags/not-a-real-tag/');assert(missing.status()===404,'Unknown tag is a soft 404');
   productionPolicyVerified=true;await ordinary.close();
  }
  const report={date:'2026-10-08',url:base,builtSite:true,tagModalsChecked:checked,personRecords:14,enterpriseOfferings:6,preservedScopeRecords:scopeIds.length,deepLinks:true,malformedFragmentSafe:true,keyboardFocusTrap:true,escapeRestoresFocus:true,nestedReportFocus:true,draftExport:true,noFalseSubmission:true,noScriptReference:true,mobile320:true,textEnlargement200:true,axeViolations:0,unexpectedOutboundRequests:0,footerModalsChecked:8,nativeModelContextAvailable:nativeModelContext,nativeModelToolsValidated:false,manualScreenReader:false,remoteIntake:false,published:base.startsWith('https://'),axeInjectionOnlyCSPBypass:true,productionPolicyVerified,compactTagTiles:true,plainLanguageTagSummaries:20,visibleValidationStatus:20,compactDisclosures:true,perTagUseInstructions:20,workingTagSetupGuides:2,selfHostedFont:true,completeDetailExport:true,themeSwitch:true,switchKeyboardSpace:true,crossTabThemeSync:true,lightDarkSystem:true,themePersistence:true,blockedStorageSafe:true,forcedColors:true,crawlableTagReferences:20,canonicalSitemapURLs:32,uniqueTitlesAndDescriptions:true,structuredDataJSONParsed:true,structuredDataTypesReviewed:true,googleRichResultsTestVerified:false,socialPreviewPNG:true,googleIndexingVerified:false,searchConsoleVerified:false};
  fs.writeFileSync(process.env.AITRUST_SITE_REPORT||'runs/2026-10-08-site-verification.json',JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report));await context.close();
 }finally{await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
