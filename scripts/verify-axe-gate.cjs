const {writeReport}=require('./execution-report.cjs');
// Exercise the same real badge gate twice: intact and deliberately inaccessible.
const {spawnSync}=require('node:child_process'),fs=require('node:fs'),assert=require('node:assert/strict');
const {assess}=require('./axe-gate.cjs');
assert.equal(assess({violations:[]}).pass,true);
for(const impact of ['serious','critical'])assert.equal(assess({violations:[{id:'control',impact,nodes:[{target:['button']}]}]}).pass,false);
assert.throws(()=>assess({}));
const positiveReport=process.env.AITRUST_AXE_POSITIVE_REPORT||'output/axe-positive.json';
const positive=spawnSync(process.execPath,['scripts/verify-browser.cjs'],{encoding:'utf8',timeout:60000,env:{...process.env,AITRUST_AXE_NEGATIVE:'0',AITRUST_BROWSER_REPORT:positiveReport}});
assert.equal(positive.status,0,positive.stderr);
const negative=spawnSync(process.execPath,['scripts/verify-browser.cjs'],{encoding:'utf8',timeout:60000,env:{...process.env,AITRUST_AXE_NEGATIVE:'1',AITRUST_BROWSER_REPORT:'output/axe-negative.json'}});
assert.notEqual(negative.status,0,'An inaccessible badge passed');assert(negative.stderr.includes('AXE_RELEASE_GATE_FAILED')&&negative.stderr.includes('button-name'),'Failure must come from the injected axe violation');
const report={captured_at:new Date().toISOString(),pass:true,intact_badge_exit:positive.status,inaccessible_badge_exit:negative.status,injected_violation:'button-name',gate_requires_zero_serious_and_critical:true,missing_results_refused:true,actual_browser_component:true,synthetic_fixture:true,live_vendor_compatibility:false,human_screen_reader:false,full_wcag_conformance:false};
if(process.env.AITRUST_AXE_GATE_REPORT)writeReport(process.env.AITRUST_AXE_GATE_REPORT,report);console.log(JSON.stringify(report));
