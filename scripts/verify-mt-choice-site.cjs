// Actual built-route controls. Public callers reuse verifyMTChoiceSite(browser,base).
'use strict';
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),assert=require('node:assert/strict');
const {chromium,webkit}=require('playwright');
const {startSiteFixture}=require('./site-fixture-server.cjs');
const {writeReport}=require('./execution-report.cjs');
const {verifyMTChoiceSite}=require('./mt-choice-site-controls.cjs');
const directory=path.resolve(process.env.AITRUST_MT_CHOICE_BUILD||'site/dist');
const output=process.env.AITRUST_MT_CHOICE_SITE_REPORT||'output/verification/mt-choice-site.json';
const hash=p=>crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
function list(dir,prefix=''){return fs.readdirSync(dir,{withFileTypes:true}).flatMap(e=>e.isDirectory()?list(path.join(dir,e.name),prefix+e.name+'/'):[prefix+e.name]);}
const sources=[...list('integrations/mt-choice-reference/1.3.0').map(p=>'integrations/mt-choice-reference/1.3.0/'+p),
 'scripts/build-mt-choice-device.py','scripts/mt-choice-device-cases.py','scripts/mt-choice-site-controls.cjs','scripts/verify-mt-choice-site.cjs',
 'site/src/MTChoiceExplorer.jsx','site/src/MTChoiceExplorerSlot.jsx','site/src/mt-choice-client.mjs','site/src/mt-choice-result.mjs','site/src/mt-choice-worker.mjs',
 'site/src/main.jsx','site/scripts/prepare.mjs','scripts/verify-site-accessibility.cjs','scripts/verify-site.cjs','site/scripts/prepare-offline.mjs',
 'tests/test_mt_choice_integration.py','tests/mt-choice-modal-client.mjs','protocol/normalization.mjs','protocol/normalization-core.js',
 'sbom/nested-runtime/pyodide-wasm-release.json','docs/mt-choice-device.md','docs/mt-choice-modal-integration-plan.md',
 'tools/choice_framing.py','tools/mt_workflow.py','site/src/MTExplorer.jsx','site/src/mt-device-client.js','site/src/mt-device-result.js','site/src/mt-device-worker.js'];
const assets=['index.html','_headers','offline-worker.js','offline-release.json','reference/mt-choice-device.md',
 ...list(path.join(directory,'device/mt-choice')).map(p=>'device/mt-choice/'+p),
 ...list(path.join(directory,'assets')).filter(p=>/\.(js|css)$/.test(p)).map(p=>'assets/'+p),
 ...['pyodide.mjs','pyodide.asm.mjs','pyodide.asm.wasm','python_stdlib.zip','pyodide-lock.json'].map(p=>'device/runtime-314.0.7/'+p)];
const snapshot=()=>({sources:Object.fromEntries(sources.map(p=>[p,hash(p)])),served:Object.fromEntries(assets.map(p=>[p,hash(path.join(directory,p))]))});
(async()=>{
 const before=snapshot(),report={captured_at:new Date().toISOString(),author:'Codex / web_camo',profile:'mt-selected-wording-production-route/v1',pass:false,before,engines:[],errors:[],
  artifact_mode:'isolated_normal_build',production_publication_claimed:false,full_MT_acceptance_claimed:false,independent_accuracy_evidence:false,physical_phone_tested:false};
 let fixture;
 try{
  fixture=await startSiteFixture({directory});
  const headers=await fetch(fixture.url+'/',{signal:AbortSignal.timeout(5000)});assert(headers.headers.get('content-security-policy'),'Reviewed actual response CSP missing');report.actual_CSP=true;
  for(const [name,engine]of [['Chromium',chromium],['WebKit',webkit]]){
   let browser,offlineServer;
   try{offlineServer=await startSiteFixture({directory});browser=await engine.launch();report.engines.push({engine:name,...await verifyMTChoiceSite(browser,fixture.url,{screenshots:path.join('output/verification/mt-choice-screenshots',name.toLowerCase()),offlineServer})});}
   catch(error){const raw=String(error.stack||error);fs.mkdirSync('output/verification',{recursive:true});fs.writeFileSync('output/verification/mt-choice-private-'+name.toLowerCase()+'.log',raw,{mode:0o600});report.errors.push({engine:name,error_sha256:crypto.createHash('sha256').update(raw).digest('hex')});throw error;}
   finally{await browser?.close();await offlineServer?.close();}
  }
  report.after=snapshot();assert.deepEqual(report.after,before,'Source or served bytes changed');report.source_and_served_bytes_stable=true;report.pass=true;
 }catch{process.exitCode=1;}
 finally{await fixture?.close();report.fixture_closed=true;report.finalized_at=new Date().toISOString();writeReport(output,report);console.log(JSON.stringify({pass:report.pass,engines:report.engines.map(e=>({engine:e.engine,worker_records:e.full_canonical_worker_records,UI_records:e.full_actual_UI_records,offline:e.offline})),errors:report.errors}));}
})().catch(()=>{console.error('Selected-wording production verification unavailable');process.exitCode=1;});
