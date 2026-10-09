const fs=require('node:fs');
const http=require('node:http');
const path=require('node:path');
const vm=require('node:vm');
const {chromium}=require('playwright');
const root=path.resolve(__dirname,'..');
(async()=>{
 const server=http.createServer((req,res)=>{
   const file=path.resolve(root,'.'+decodeURIComponent(req.url.split('?')[0]));
   if(!file.startsWith(root+path.sep)){res.writeHead(403);return res.end();}
   try{res.setHeader('Content-Type',file.endsWith('.js')?'text/javascript':file.endsWith('.html')?'text/html':'text/plain');res.end(fs.readFileSync(file));}catch{res.writeHead(404);res.end();}
 });
 await new Promise(resolve=>server.listen(8799,'127.0.0.1',resolve));
 let browser;
 try { browser=await chromium.launch({headless:true,channel:process.env.AITRUST_BROWSER_CHANNEL||"chromium"}); } catch(error) {server.close();throw error;}
 try{
   const page=await browser.newPage();
   fs.mkdirSync(path.join(root,'output/playwright'),{recursive:true});
   const check=vm.runInNewContext(fs.readFileSync(path.join(root,'scripts/browser-acceptance.js'),'utf8'));
   const compactUI=await check(page);
   const observedCheck=vm.runInNewContext(fs.readFileSync(path.join(root,'scripts/live-dom-acceptance.js'),'utf8'));
   const observedDOM=await observedCheck(page);
   await page.goto('http://127.0.0.1:8799/extension/test/badge-fixture.html?open-shadow');
   await page.waitForFunction(()=>fixtureRequests.length===2);
   await page.evaluate(()=>{fixtureResponders.forEach((resolve,i)=>resolve(fixtureResult(fixtureRequests[i].text)));});
   await page.waitForTimeout(100);
   await page.getByRole('button',{name:/^PS:/}).first().click();
   await page.addScriptTag({path:require.resolve('axe-core/axe.min.js')});
   const axe=await page.evaluate(()=>axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag22aa']}}));
   const serious=axe.violations.filter(v=>['serious','critical'].includes(v.impact));
   if(serious.length)throw new Error(JSON.stringify(serious.map(v=>({id:v.id,nodes:v.nodes.map(n=>n.target)}))));
   await page.emulateMedia({forcedColors:'active',reducedMotion:'reduce'});
   await page.setViewportSize({width:320,height:640});
   if(await page.evaluate(()=>document.documentElement.scrollWidth>320))throw new Error('320px reflow overflow');
   await page.screenshot({path:'output/playwright/command-tag-reflow.png',fullPage:true});
   const report={syntheticBrowserChecks:true,compactUI,observedDOM,axeSerious:serious.length,axeCritical:0,axeTotalViolations:axe.violations.length,reflow320:true,forcedColors:true,reducedMotion:true,closedShadowBehaviorTested:true,axeUsesTestOnlyOpenShadow:true,manualScreenReader:false,liveVendorCompatibility:false};
   fs.writeFileSync(path.join(root,'runs/2026-10-08-browser-checks.json'),JSON.stringify(report,null,2)+'\n');
   console.log(JSON.stringify(report));
 }finally{await browser.close();server.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
