// Affected-only replay after candidate2. Never run this against a public origin.
'use strict';
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),assert=require('node:assert/strict');
const {chromium,webkit}=require('playwright');
const {startSiteFixture}=require('./site-fixture-server.cjs');
const {verifyMTChoiceOutage}=require('./mt-choice-site-controls.cjs');
const {writeReport}=require('./execution-report.cjs');
const priorPath='runs/2026-11-22-mt-choice-site-candidate-2.json',prior=JSON.parse(fs.readFileSync(priorPath));
const hash=p=>crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
const sourcePaths=[...Object.keys(prior.before.sources),'scripts/verify-mt-choice-outage.cjs'];
const snapshot=()=>({sources:Object.fromEntries(sourcePaths.map(p=>[p,hash(p)])),served:Object.fromEntries(Object.keys(prior.before.served).map(p=>[p,hash(path.join('site/dist',p))]))});
(async()=>{
 const before=snapshot(),report={captured_at:new Date().toISOString(),author:'Codex / web_camo',profile:'mt-selected-wording-owned-outage-observation/v1',pass:false,before,prior_full_matrix:{path:priorPath,sha256:hash(priorPath),not_reexecuted:true},engines:[],errors:[]};
 try{
  assert(prior.pass&&prior.source_and_served_bytes_stable);assert.deepEqual(before.served,prior.before.served,'Actual served bytes changed');
  const allowed=new Set(['scripts/mt-choice-site-controls.cjs','docs/mt-choice-modal-integration-plan.md']);
  report.changed_from_prior=Object.keys(prior.before.sources).filter(p=>before.sources[p]!==prior.before.sources[p]);assert(report.changed_from_prior.every(p=>allowed.has(p)),'Unexpected runtime/source change');
  for(const [name,engine]of [['Chromium',chromium],['WebKit',webkit]]){
   let fixture,browser;
   try{fixture=await startSiteFixture({directory:path.resolve('site/dist')});browser=await engine.launch();report.engines.push({engine:name,...await verifyMTChoiceOutage(browser,fixture)});}
   catch(error){const raw=String(error.stack||error);fs.writeFileSync('output/verification/mt-choice-outage-private-'+name.toLowerCase()+'.log',raw,{mode:0o600});report.errors.push({engine:name,error_sha256:crypto.createHash('sha256').update(raw).digest('hex')});throw error;}
   finally{await browser?.close();await fixture?.close();}
  }
  report.after=snapshot();assert.deepEqual(report.after,before);report.source_and_served_bytes_stable=true;report.pass=true;
 }catch{process.exitCode=1;}
 finally{report.finalized_at=new Date().toISOString();writeReport('runs/2026-11-22-mt-choice-owned-outage-observation.json',report);console.log(JSON.stringify({pass:report.pass,engines:report.engines,errors:report.errors}));}
})().catch(()=>{console.error('Owned outage verification unavailable');process.exitCode=1;});
