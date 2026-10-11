'use strict';
const fs=require('node:fs'),path=require('node:path'),http=require('node:http'),crypto=require('node:crypto'),assert=require('node:assert/strict');
const {chromium}=require('playwright'),{writeReport}=require('./execution-report.cjs');
const {parseHeaders,headersFor}=require('./static-headers.cjs');
const root=path.resolve(__dirname,'..'),dist=path.join(root,'site/dist');
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
(async()=>{
 let server;let base=process.env.AITRUST_SITE_URL;
 if(!base){
  const rules=parseHeaders(fs.readFileSync(path.join(dist,'_headers'),'utf8'));
  server=http.createServer((req,res)=>{
   let name;try{name=decodeURIComponent(new URL(req.url,'http://localhost').pathname);}catch{res.writeHead(400);res.end();return;}
   let file=path.resolve(dist,'.'+name);
   if(!file.startsWith(dist+path.sep)){res.writeHead(403);res.end();return;}
   try{if(fs.statSync(file).isDirectory())file=path.join(file,'index.html');const bytes=fs.readFileSync(file);
    res.setHeader('content-type',file.endsWith('.html')?'text/html':file.endsWith('.css')?'text/css':file.endsWith('.js')?'text/javascript':'application/octet-stream');
    for(const [key,value] of Object.entries(headersFor(rules,name)))res.setHeader(key,value);res.end(bytes);
   }catch{res.writeHead(404);res.end();}
  });await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));base='http://127.0.0.1:'+server.address().port;
 }
 let browser;
 try{
  browser=await chromium.launch();
  const page=await browser.newPage({viewport:{width:320,height:740}});await page.goto(base+'/reference/offline-tools/');
  assert(await page.getByRole('heading',{name:'Keep your work on your device.'}).isVisible());
  const wait=page.waitForEvent('download');await page.getByRole('link',{name:'Download the standalone editor',exact:true}).click();
  const item=await wait,download=fs.readFileSync(await item.path());assert.equal(sha(download),sha(fs.readFileSync(path.join(dist,'reference/offline-editor.html'))));
  assert.equal(item.suggestedFilename(),'AI-Trust-ID-offline-editor.html');
  await page.evaluate(fs.readFileSync(require.resolve('axe-core/axe.min.js'),'utf8'));
  const violations=await page.evaluate(async()=> (await axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21a','wcag21aa']}})).violations.length);assert.equal(violations,0);
  assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
  await page.goto(base+'/reference/conformance/');
  assert(await page.getByRole('heading',{name:'Show what your build has checked.',exact:true}).isVisible());
  const guides=[];
  for(const [label,name] of [['Download the guidelines and template','mark-usage'],['Read the optional-receipt rule','author-choice'],['Local reference comparison guide','corpus-support']]){
    const pending=page.waitForEvent('download');await page.getByRole('link',{name:label,exact:true}).click();
    const downloaded=await pending,raw=fs.readFileSync(await downloaded.path());
    assert.equal(sha(raw),sha(fs.readFileSync(path.join(root,'docs',name+'.md'))));guides.push({name,native_download:true,sha256:sha(raw)});
  }
  await page.evaluate(fs.readFileSync(require.resolve('axe-core/axe.min.js'),'utf8'));
  const conformanceAxe=await page.evaluate(async()=> (await axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21a','wcag21aa']}})).violations.length);assert.equal(conformanceAxe,0);
  assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
  const record={captured_at:new Date().toISOString(),pass:true,base,published:!!process.env.AITRUST_SITE_URL,download_sha256:sha(download),native_download:true,expected_filename:true,reference_320_reflow:true,axe_violations:violations,conformance_guides:guides,conformance_axe_violations:conformanceAxe,independent_accuracy_evidence:false,tag_release_approved:false};
  writeReport(process.env.AITRUST_OFFLINE_DOWNLOAD_REPORT||'output/verification/offline-download.json',record,root);console.log(JSON.stringify(record));
 }finally{if(browser)await browser.close();if(server)await new Promise(resolve=>server.close(resolve));}
})().catch(e=>{console.error(e);process.exitCode=1;});
