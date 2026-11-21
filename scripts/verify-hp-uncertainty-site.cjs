// Actual integrated-route runner, separate from standalone source/fixture proof.
'use strict';
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),assert=require('node:assert/strict');
const {chromium,webkit}=require('playwright'),{startSiteFixture}=require('./site-fixture-server.cjs'),{writeReport}=require('./execution-report.cjs'),{verifyHPUncertaintySite}=require('./hp-uncertainty-site-controls.cjs');
const sourceRoot=path.resolve(process.env.AITRUST_HP_UNCERTAINTY_SOURCE_ROOT||process.cwd());
const directory=path.resolve(process.env.AITRUST_HP_UNCERTAINTY_BUILD||path.join(sourceRoot,'site/dist'));
const manifest=JSON.parse(fs.readFileSync(path.join(sourceRoot,'site/src/hp-uncertainty-manifest.json')));
const sources=[...new Set([...Object.keys(manifest.checks.hedge.sources),'site/src/main.jsx','site/src/HPUncertaintyExplorer.jsx','site/src/HPUncertaintyExplorerSlot.jsx','site/src/hp-uncertainty-client.js','site/src/hp-uncertainty-worker.js','site/src/hp-uncertainty-result.js','site/src/hp-uncertainty-manifest.json','scripts/build-hp-uncertainty-device.py','scripts/hp-uncertainty-cases.py','scripts/hp-uncertainty-site-controls.cjs','scripts/verify-hp-uncertainty-site.cjs','docs/hp-uncertainty-device.md','site/public'+manifest.checks.hedge.path,'site/public/hp-uncertainty-device/notices.txt'])];
const artifacts=['index.html','_headers','reference/hp-uncertainty-device.md',manifest.checks.hedge.path.slice(1),'hp-uncertainty-device/notices.txt',...fs.readdirSync(path.join(directory,'assets')).filter(v=>/\.(js|css)$/.test(v)).map(v=>'assets/'+v),...['pyodide.mjs','pyodide.asm.mjs','pyodide.asm.wasm','python_stdlib.zip','pyodide-lock.json'].map(v=>'device/runtime-314.0.7/'+v)];
const hash=p=>crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
const sourcePath=p=>p==='scripts/hp-uncertainty-site-controls.cjs'||p==='scripts/verify-hp-uncertainty-site.cjs'?path.join(__dirname,path.basename(p)):path.join(sourceRoot,p);
const snapshot=()=>({sources:Object.fromEntries(sources.map(p=>[p,hash(sourcePath(p))])),served:Object.fromEntries(artifacts.map(p=>[p,hash(path.join(directory,p))]))});
(async()=>{let fixture;const before=snapshot(),report={profile:'hp-uncertainty-integrated-site/v1',captured_at:new Date().toISOString(),pass:false,before,engines:[],production_publication_claimed:false,physical_phone:false,independent_accuracy_evidence:false};
 try{fixture=await startSiteFixture({directory});for(const [name,engine] of [['Chromium',chromium],['WebKit',webkit]]){const browser=await engine.launch();try{report.engines.push({engine:name,...await verifyHPUncertaintySite(browser,fixture.url)});}catch(error){report.failure={engine:name,stage:error.hpUncertaintySiteStage||'unknown',error_sha256:crypto.createHash('sha256').update(String(error.message)).digest('hex')};throw error;}finally{await browser.close();}}
  report.after=snapshot();assert.deepEqual(report.after,before);report.source_and_served_stable=true;report.pass=true;
 }catch{process.exitCode=1;}finally{await fixture?.close();writeReport(process.env.AITRUST_HP_UNCERTAINTY_SITE_REPORT||'output/verification/hp-uncertainty-site.json',report);console.log(JSON.stringify({pass:report.pass,engines:report.engines,failure:report.failure}));}
})().catch(()=>{console.error('HP uncertainty integrated-site verification unavailable');process.exitCode=1;});
