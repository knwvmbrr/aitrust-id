'use strict';
const fs=require('node:fs'),path=require('node:path'),os=require('node:os'),assert=require('node:assert/strict');
const {pathToFileURL}=require('node:url'),{execFileSync}=require('node:child_process');
const {chromium}=require('playwright');
const {writeReport}=require('./execution-report.cjs');
const hash=raw=>require('node:crypto').createHash('sha256').update(raw).digest('hex');
const root=path.resolve(__dirname,'..'),python=process.env.AITRUST_VERIFY_PYTHON||'python3';
async function main(){
 const home=fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(),'aitrust-agent-view-')));fs.chmodSync(home,0o700);
 let browser;
 try{
  const prepare="from pathlib import Path\nimport sys,json\nfrom tools import agent_output as a\nh=Path(sys.argv[1]);a.demo(h/'input')\ndef run(out,include=False,check=False):\n return a.record_run(program=h/'input/agent.py',task=h/'input/task.json',agent=h/'input/agent.json',key=h/'input/private.pem',public_key=h/'input/public.pem',output=h/out,execute=True,include_output=include,check_ps=check)\nrun('brief',check=True)\np=h/'input/agent.py';p.write_text(\"print('<script>window.agentInjected=true</script><img src=https://example.invalid/private-canary>')\")\nd=json.loads((h/'input/agent.json').read_bytes());d['program_sha256']=a.sha(p.read_bytes());(h/'input/agent.json').write_bytes(a.encode(d))\nrun('included',include=True)\n";
  const sources=JSON.parse(execFileSync(python,['-c',prepare+"\nprint(json.dumps(a.identity(),sort_keys=True))\n",home],{cwd:root,stdio:['ignore','pipe','pipe'],timeout:30000}));
  for(const name of ['scripts/verify-agent-output-view.cjs','package-lock.json'])sources[name]=hash(fs.readFileSync(path.join(root,name)));
  browser=await chromium.launch({headless:true});
  let external=0,errors=0;const checks=[];
  for(const theme of ['light','dark']){
   const context=await browser.newContext({viewport:{width:320,height:740},colorScheme:theme});
   context.on('request',r=>{if(/^https?:/.test(r.url()))external++;});
   const page=await context.newPage();page.on('pageerror',()=>errors++);
   await page.goto(pathToFileURL(path.join(home,'brief/agent-output.html')).href);
   assert.equal(await page.locator('h1').textContent(),'Agent output');
   assert(!(await page.locator('body').textContent()).includes('curl -fsSL'));
   const badge=page.locator('summary').first();await badge.focus();await page.keyboard.press('Enter');
   assert(await page.locator('details').first().evaluate(e=>e.open));
   await page.keyboard.press('Enter');assert(!(await page.locator('details').first().evaluate(e=>e.open)));
   await page.evaluate(()=>document.documentElement.style.fontSize='200%');
   assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
   await page.goto(pathToFileURL(path.join(home,'included/agent-output.html')).href);
   assert((await page.locator('pre').textContent()).includes('<script>window.agentInjected=true</script>'));
   assert.equal(await page.locator('script,img').count(),0);
   assert.equal(await page.evaluate(()=>window.agentInjected),undefined);
   await page.evaluate(()=>document.documentElement.style.fontSize='200%');
   assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
   assert((await page.locator('meta[http-equiv="Content-Security-Policy"]').getAttribute('content')).includes("default-src 'none'"));
   checks.push({theme,mobile320:true,text200:true,keyboardDetails:true,answerDefaultOmitted:true,explicitAnswerEscaped:true});
   await context.close();
  }
  // Only the separate accessibility audit context bypasses CSP for axe injection.
  const audit=await browser.newContext({bypassCSP:true});const page=await audit.newPage();
  let violations=0;
  for(const name of ['brief','included']){
   await page.goto(pathToFileURL(path.join(home,name,'agent-output.html')).href);
   await page.addScriptTag({path:require.resolve('axe-core/axe.min.js')});
   violations+=(await page.evaluate(async()=> (await axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21aa','wcag22aa']}})).violations)).length;
  }
  await audit.close();assert.equal(external,0);assert.equal(errors,0);assert.equal(violations,0);
  for(const [name,expected] of Object.entries(sources))assert.equal(hash(fs.readFileSync(path.join(root,name))),expected,'View source changed');
  const row={captured_at:new Date().toISOString(),pass:true,sources,source_unchanged:true,checks,axe_violations:violations,external_requests:external,script_errors:errors,
   production_CSP_verified:true,axe_injection_only_CSP_bypass:true,actual_agent_CLI_used:true,real_model_used:false,
   human_accessibility_verified:false,physical_phone_tested:false,independent_accuracy_evidence:false,collection_enabled:false};
  writeReport(process.env.AITRUST_AGENT_VIEW_REPORT||'output/verification/agent-output-view.json',row);
  console.log(JSON.stringify(row));
 }finally{if(browser)await browser.close();fs.rmSync(home,{recursive:true,force:true});}
}
main().catch(error=>{console.error('Synthetic private agent view verification failed.');console.error(String(error.stack||error).slice(0,4000));process.exitCode=1;});
