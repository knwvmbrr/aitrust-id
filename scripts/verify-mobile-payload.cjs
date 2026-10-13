// Built browser controls: no physical-phone or detector-accuracy claim.
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {chromium,webkit}=require('playwright');
const {writeReport}=require('./execution-report.cjs');
const {createHash}=require('node:crypto');
const http=require('node:http');
const {parseHeaders,headersFor}=require('./static-headers.cjs');
const sourcePaths=['site/src/scope-data.js','site/src/ScopeData.jsx','site/src/scope-manifest.json',
  'site/src/public-scope.json','site/src/main.jsx','site/src/workflows/Scope.jsx',
  'site/scripts/prepare.mjs','site/scripts/prepare-offline.mjs','scripts/verify-mobile-payload.cjs'];
const sourceInventory=()=>Object.fromEntries(sourcePaths.map(name=>[name,createHash('sha256')
  .update(fs.readFileSync(path.join(__dirname,'..',name))).digest('hex')]));
const sources=sourceInventory();
const base=process.env.AITRUST_SITE_URL;
const dist=path.resolve(__dirname,'../site/dist');
const expected=JSON.parse(fs.readFileSync(path.join(__dirname,'../site/src/public-scope.json')));
const file=fs.readdirSync(path.join(dist,'assets')).find(name=>/^public-scope-.*\.json$/.test(name));
assert(file,'Scope must be a separate build-hashed asset');
const asset='/assets/'+file,bytes=fs.readFileSync(path.join(dist,asset));
const html=fs.readFileSync(path.join(dist,'index.html'),'utf8');
const initial=[...html.matchAll(/<script[^>]+type="module"[^>]+src="([^"]+)"/g)].map(match=>match[1]);
assert(initial.length>0,'No built initial JavaScript found');
const initialBytes=initial.reduce((n,name)=>n+fs.statSync(path.join(dist,name)).size,0);
assert(initialBytes<600000,'Initial JavaScript exceeds the explicit mobile payload budget');
async function panel(page){await page.goto(base+'/#person/PS');
  const active=page.getByRole('dialog');await active.waitFor();return active;}
async function details(dialog){await dialog.locator('summary').filter({hasText:'Privacy and full details'}).click();}
async function exportDetails(page,dialog,tag){const event=page.waitForEvent('download');await dialog.getByRole('button',{name:'Download details',exact:true}).click();
  const saved=JSON.parse(fs.readFileSync(await (await event).path(),'utf8'));
  const selected=[...['F-001','F-003','F-004','F-005','F-007','F-008','F-009','N-005','N-006'],...tag.features];
  assert.deepEqual(saved.scopeFeatures,selected.map(id=>expected.records.find(record=>record.id===id)).filter(Boolean));
  for(const key of Object.keys(tag))assert.deepEqual(saved[key],tag[key]);
  assert.equal(saved.evaluated_result,false);return saved.scopeFeatures.length;}
async function main(){
  assert(base,'Use only an owned verification server');
  const {allTags}=await import('../site/src/catalog.js');const ps=allTags.find(tag=>tag.id==='PS');
  const engines=[],failures=[];
  for(const [name,type] of [['chromium',chromium],['webkit',webkit]]){
    const browser=await type.launch();const context=await browser.newContext({viewport:{width:390,height:844},acceptDownloads:true});
    try{
      const page=await context.newPage();const requests=[],errors=[];
      page.on('request',request=>requests.push(new URL(request.url()).pathname));page.on('pageerror',error=>errors.push(error.message));
      const dialog=await panel(page);assert(!requests.includes(asset),'Opening PS must not eagerly load complete scope');
      await details(dialog);await dialog.getByRole('button',{name:'Download details',exact:true}).waitFor();
      assert.equal(requests.filter(url=>url===asset).length,1);
      const count=await exportDetails(page,dialog,ps);
      await page.keyboard.press('Escape');await page.goto(base+'/#scope');
      await page.getByLabel('Search preserved scope').fill('F-019c');
      // Exact ID lookup selects the signal; its preserved grouping has its own ID.
      await page.getByRole('status').filter({hasText:'1 records match'}).waitFor();
      assert.equal(await page.getByRole('dialog').locator('li details').count(),1);
      assert.equal(await page.getByRole('dialog').locator('summary[data-record-id="F-019c"]').count(),1,'Exact signal record missing');
      assert.equal(requests.filter(url=>url===asset).length,1,'One build must reuse one verified in-memory scope');
      assert.equal(errors.length,0,errors.join('; '));
      engines.push({engine:name,viewport_width:390,no_eager_scope_request:true,complete_export_records:count,scope_search:true,verified_scope_cache:true,page_errors:errors});
    }finally{await context.close();await browser.close();}
  }
  const browser=await chromium.launch();
  try{
    for(const fault of ['network','http','truncated','oversized','altered','timeout']){
      const context=await browser.newContext({viewport:{width:390,height:844},acceptDownloads:true});
      try{
        const page=await context.newPage();let count=0;
        await page.route(base+asset,async route=>{count++;if(fault==='network')return route.abort();
          if(fault==='timeout')return; // The real loader's AbortController must end this stalled request.
          let body=bytes;if(fault==='truncated')body=bytes.subarray(0,bytes.length-1);
          if(fault==='oversized')body=Buffer.concat([bytes,Buffer.from(' ')]);
          if(fault==='altered'){body=Buffer.from(bytes);const at=body.indexOf('Tag types');assert(at>=0);body[at]='X'.charCodeAt(0);}
          return route.fulfill({status:fault==='http'?503:200,contentType:'application/json',body});});
        const dialog=await panel(page);await details(dialog);
        await dialog.locator('[data-scope-load-error]').waitFor();assert.equal(count,1);
        assert.equal(await dialog.getByRole('button',{name:'Download details',exact:true}).count(),0,'Bad scope must not export');
        assert(await dialog.getByRole('button',{name:'Check on this device',exact:true}).isVisible(),'Scope failure disabled PS');
        await page.unroute(base+asset);await dialog.getByRole('button',{name:'Try loading again',exact:true}).click();
        await dialog.getByRole('button',{name:'Download details',exact:true}).waitFor();await exportDetails(page,dialog,ps);
        failures.push({fault,refused:true,checker_available:true,retry_with_complete_export:true});
      }finally{await context.close();}
    }
    // Browser routing disables its HTTP cache. This real owned server does not:
    // return one corrupt cacheable 200, repair the origin, then require recovery.
    let reads=0;
    const rules=parseHeaders(fs.readFileSync(path.join(dist,'_headers'),'utf8'));
    const cacheServer=http.createServer((request,response)=>{
      try {
        const pathname=decodeURIComponent(new URL(request.url,'http://localhost').pathname);
        let location=path.resolve(dist,'.'+pathname);
        if(location!==dist&&!location.startsWith(dist+path.sep))throw Error('Path refused');
        if(fs.statSync(location).isDirectory())location=path.join(location,'index.html');
        const mime={'.html':'text/html','.js':'text/javascript','.json':'application/json','.css':'text/css','.woff2':'font/woff2','.svg':'image/svg+xml'};
        const headers={'content-type':mime[path.extname(location)]||'application/octet-stream',...headersFor(rules,pathname)};
        let body=fs.readFileSync(location);
        if(pathname===asset){reads++;headers['cache-control']='public, max-age=31536000';
          if(reads===1){body=Buffer.from(bytes);const at=body.indexOf('Tag types');assert(at>=0);body[at]=88;}}
        response.writeHead(200,headers);response.end(body);
      }catch{response.writeHead(404);response.end();}
    });
    await new Promise((resolve,reject)=>{cacheServer.once('error',reject);cacheServer.listen(0,'127.0.0.1',resolve);});
    const cacheContext=await browser.newContext({viewport:{width:390,height:844},acceptDownloads:true});
    try{
      const page=await cacheContext.newPage();await page.goto('http://127.0.0.1:'+cacheServer.address().port+'/#person/PS');
      const dialog=page.getByRole('dialog');await dialog.waitFor();await details(dialog);
      await dialog.locator('[data-scope-load-error]').waitFor();assert.equal(reads,1);
      await dialog.getByRole('button',{name:'Try loading again',exact:true}).click();
      await dialog.getByRole('button',{name:'Download details',exact:true}).waitFor();await exportDetails(page,dialog,ps);
      assert.equal(reads,2,'Retry reused a corrupt HTTP-cache entry');
      failures.push({fault:'actual_cacheable_corrupt_response',playwright_routes_used:false,origin_requests:reads,retry_with_complete_export:true});
    }finally{await cacheContext.close();cacheServer.closeAllConnections();await new Promise(resolve=>cacheServer.close(resolve));}
    const context=await browser.newContext({viewport:{width:390,height:844},acceptDownloads:true});
    try{
      const page=await context.newPage();await panel(page);
      await page.evaluate(async()=>{await navigator.serviceWorker.register('/offline-worker.js');await navigator.serviceWorker.ready;});
      await page.waitForFunction(()=>!!navigator.serviceWorker.controller);
      await context.setOffline(true);await page.reload();const dialog=page.getByRole('dialog');await dialog.waitFor();await details(dialog);
      await dialog.getByRole('button',{name:'Download details',exact:true}).waitFor();await exportDetails(page,dialog,ps);
      const release=JSON.parse(fs.readFileSync(path.join(dist,'offline-release.json')));
      assert(release.assets.includes(asset),'New scope asset missing from frozen offline release');
      failures.push({fault:'offline_after_install',complete_export:true,frozen_scope_asset:true});
    }finally{await context.close();}
  }finally{await browser.close();}
  assert.deepEqual(sourceInventory(),sources,'Sources changed during mobile verification');
  const report={captured_at:new Date().toISOString(),pass:true,sources,source_unchanged_during_execution:true,initial_javascript_bytes:initialBytes,initial_budget_bytes:600000,full_scope_asset_bytes:bytes.length,preserved_records:expected.records.length,engines,controls:failures,physical_phone:false,human_accessibility_acceptance:false,independent_accuracy_evidence:false};
  writeReport(process.env.AITRUST_MOBILE_PAYLOAD_REPORT||'output/verification/mobile-payload.json',report);console.log(JSON.stringify(report));
}
main().catch(error=>{console.error(error);process.exitCode=1;});
