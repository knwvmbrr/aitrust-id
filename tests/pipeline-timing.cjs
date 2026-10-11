const {test,before}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const crypto=require('node:crypto');
const path=require('node:path');
const root=path.resolve(__dirname,'..');
const data=JSON.parse(fs.readFileSync(path.join(root,'runs/2026-10-11-staging-pipeline-performance.json'),'utf8'));
const hash=p=>crypto.createHash('sha256').update(fs.readFileSync(path.join(root,p))).digest('hex');
let model;
before(async()=>{model=await import('../site/src/pipeline-timing-model.js');});
test('admit the actual source-bound synthetic staging measurements',()=>{
 assert.equal(model.validatePipelineTiming(data,hash),data);
 assert.equal(data.profile_count,12);assert.equal(data.repeats_per_profile,20);
});
const corruptions={
 'failed execution':d=>d.pass=false,'real content':d=>d.user_content_used=true,
 'release claim':d=>d.release_approved=true,'independent accuracy':d=>d.independent_accuracy_evidence=true,
 'invented budget':d=>d.accepted_latency_budget_ms=100,'missing profile':d=>d.rows.pop(),
 'fabricated percentile':d=>d.rows[0].warm_round_trip.p95_ms=0,
 'missing sample':d=>d.rows[0].warm_round_trip.durations_ms.pop(),
 'negative service duration':d=>d.rows[0].warm_reported_pipeline.durations_ms[0]=-1,
 'nonfinite client duration':d=>d.rows[0].warm_round_trip.durations_ms[0]=NaN,
 'unknown profile':d=>d.rows[0].form='unknown','unknown length':d=>d.rows[0].input_length_codepoints=999,
 'duplicate profile':d=>d.rows[11]=structuredClone(d.rows[0]),
 'stale source':d=>d.sources['services/evaluator/app.py']='0'.repeat(64),
 'hidden text':d=>d.private='canary must not be published',
 'missing hardware':d=>d.declared_hardware.logical_cpus=0
};
for(const [name,corrupt] of Object.entries(corruptions))test('reject '+name,()=>{
 const bad=structuredClone(data);corrupt(bad);assert.throws(()=>model.validatePipelineTiming(bad,hash));
});
test('never read an attacker-selected source filename',()=>{
 const bad=structuredClone(data);bad.sources['../../private.env']='a'.repeat(64);
 assert.throws(()=>model.validatePipelineTiming(bad,()=>assert.fail('Unexpected source read')));
});
test('bind displayed values to the maximum measured p95 for each input size',()=>{
 for(const id of ['PS','PII_REDACTED']){
  const summary=model.pipelineTimingFor({id},data);assert.equal(summary.rows.length,4);
  for(const row of summary.rows)assert.equal(row.p95_ms,Math.max(...data.rows.filter(r=>r.input_length_codepoints===row.input_length_codepoints).map(r=>r.warm_round_trip.p95_ms)));
  assert.equal(summary.accuracy_evidence,false);assert.equal(summary.budget_accepted,false);
 }
 for(const id of ['HP','MT','NF','FI','IV','FA','PA','UNK','SC','BT','fleet'])assert.equal(model.pipelineTimingFor({id},data),null);
});
test('static HTML keeps visible values, decorative bars and downloadable conditions',()=>{
 const esc=s=>String(s).replaceAll('&','&amp;').replaceAll('<','&lt;');
 const html=model.pipelineTimingHTML(model.pipelineTimingFor({id:'PS'},data),esc);
 assert.equal((html.match(/<dt /g)||[]).length,4);
 assert.ok(html.includes('Local service speed')&&html.includes('not a speed guarantee')&&html.includes('aria-hidden="true"'));
 assert.ok(html.includes('download>Download service timings'));
 assert.equal(model.pipelineTimingHTML(null,esc),'');
});
