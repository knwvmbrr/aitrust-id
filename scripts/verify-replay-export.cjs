// Owned browser, synthetic actual-service record. No vendor page or private input.
const fs=require('node:fs'),path=require('node:path'),http=require('node:http'),crypto=require('node:crypto'),{spawnSync}=require('node:child_process');
const {chromium}=require('playwright'),{assess}=require('./axe-gate.cjs'),{writeReport}=require('./execution-report.cjs');
const assert=(v,m)=>{if(!v)throw Error(m)};
async function verify(){
 const receipt=JSON.parse(fs.readFileSync(process.env.AITRUST_REPLAY_RECEIPT||JSON.parse(fs.readFileSync('eval/route-boundaries.json')).replay_evidence));
 assert(receipt.pass===true&&receipt.synthetic_only===true&&receipt.actual_pipeline_and_cli_executed===true,'Require executed synthetic service evidence');
 const a=receipt.synthetic_browser_fixture;assert(a&&a.tags.length===2,'Missing both-tag synthetic fixture');
 const root=path.resolve(__dirname,'..');let browser;
 const server=http.createServer((req,res)=>{const p=path.resolve(root,'.'+req.url.split('?')[0]);if(!p.startsWith(root+path.sep)){res.writeHead(403);res.end();return}try{res.setHeader('Content-Type',p.endsWith('.js')?'text/javascript':'text/html');res.end(fs.readFileSync(p))}catch{res.writeHead(404);res.end()}});
 await new Promise(r=>server.listen(0,'127.0.0.1',r));
 try{
  browser=await chromium.launch({headless:true,channel:'chromium'});
  const page=await browser.newPage({viewport:{width:320,height:740}}),errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto(`http://127.0.0.1:${server.address().port}/extension/test/badge-fixture.html?open-shadow`);
  await page.waitForFunction(()=>fixtureRequests.length===2);
  await page.evaluate(a=>{fixtureResponders[0]({status:'ok',assertion:a});fixtureResponders[1](fixtureResult(fixtureRequests[1].text));},a);
  await page.getByRole('button',{name:/^PS:/}).click();
  const holder=page.locator('#first .aitrust-mount').first();
  const before=await page.locator('#first').boundingBox();
  const details=holder.locator('details').filter({hasText:'Reproduce this check'});
  assert(await details.count()===1,'Replay disclosure missing');
  assert(!await details.evaluate(e=>e.open),'Replay metadata initially expanded');
  await details.locator('summary').click();
  const permission=details.locator('.replay-consent'),button=details.locator('.replay-export');
  assert(!await permission.isChecked()&&await button.isDisabled(),'Replay download lacks separate permission');
  assert((await details.innerText()).includes('all findings')&&(await details.innerText()).includes('Repeatability does not establish accuracy'),'Replay scope unclear');
  await permission.focus();await page.keyboard.press('Space');assert(await permission.isChecked()&&await button.isEnabled(),'Keyboard permission failed');
  await button.focus();const waiting=page.waitForEvent('download');await page.keyboard.press('Enter');
  const file=await waiting,bytes=fs.readFileSync(await file.path()),record=JSON.parse(bytes);
  assert(file.suggestedFilename()==='ai-trust-id-replay.json','Wrong record format');
  assert(record.tags.map(t=>t.code).sort().join(',')==='PII_REDACTED,PS','Replay lost independent findings');
  assert(record.evaluator.models.length===3&&record.evaluator.preprocessing.sha256===a.evaluator.preprocessing.sha256,'Replay lost method identity');
  assert(JSON.stringify(record.tags)===JSON.stringify(a.tags)&&JSON.stringify(record.abstentions)===JSON.stringify(a.abstentions),'Export changed findings');
  assert(!bytes.includes(Buffer.from('alice@example.com'))&&!bytes.includes(Buffer.from('example.test/install')),'Export disclosed synthetic original');
  const i=process.argv.indexOf('--python');const python=process.env.AITRUST_PYTHON||(i>=0?process.argv[i+1]:'python3');
  const checked=spawnSync(python,['-c','import json,sys;from protocol.replay import inspect_record; a=json.load(sys.stdin);assert inspect_record(a) is None; print("validated")'],{input:bytes,cwd:root,encoding:'utf8'});
  assert(checked.status===0&&checked.stdout.trim()==='validated','Downloaded assertion or digest invalid');
  await page.addScriptTag({path:require.resolve('axe-core/axe.min.js')});
  const axe=await page.evaluate(()=>axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag22aa']}}));assert(assess(axe).pass,'Replay accessibility gate failed');
  assert(!await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),'320px overflow');
  await holder.locator('.close').click();await page.getByRole('button',{name:/^PS:/}).click();
  assert(!await holder.locator('.replay-consent').isChecked()&&await holder.locator('.replay-export').isDisabled(),'Permission persisted on reopen');
  const after=await page.locator('#first').boundingBox();assert(before.height===after.height,'Dialog moved output');
  await holder.locator('.close').click();
  await page.getByRole('button',{name:/^PII:/}).click();
  assert(!await holder.locator('.replay-consent').isChecked(),'Permission shared across tags');
  assert(errors.length===0,'Browser exception');
  const sources=Object.fromEntries(['scripts/verify-replay-export.cjs','extension/src/content/badge.js','extension/src/shared/contract.js'].map(p=>[p,crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex')]));
  return {captured_at:new Date().toISOString(),pass:true,synthetic_only:true,actual_service_record_used:true,separate_permission:true,keyboard_download:true,all_findings_preserved:true,downloaded_assertion_and_identity_digests_valid:true,permission_reset_per_open_and_tag:true,source_text_absent:true,reflow320:true,axe_serious:assess(axe).serious,axe_critical:assess(axe).critical,manual_screen_reader:false,independent_accuracy_evidence:false,sources,download_sha256:crypto.createHash('sha256').update(bytes).digest('hex'),synthetic_export:record};
 }finally{if(browser)await browser.close();await new Promise(r=>server.close(r))}
}
if(require.main===module)verify().then(r=>{writeReport(process.env.AITRUST_REPLAY_EXPORT_REPORT||'output/verification/replay-export.json',r);console.log(JSON.stringify({pass:r.pass,download_sha256:r.download_sha256}))}).catch(e=>{console.error(e.message);process.exitCode=1});
module.exports={verify};
