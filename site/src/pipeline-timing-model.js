// Synthetic staging speed is separate from tag accuracy and phone timing.
export const timingSources=['services/evaluator/app.py','services/gateway/app.py','services/anonymizer/app.py',
 'services/anonymizer/model_identity.py','protocol/normalization.py','protocol/unicode15-data.json',
 'spec/assertion.schema.json','protocol/assertions.py','protocol/evidence.py','protocol/reports.py',
 'scripts/measure-pipeline-performance.py'];
const sizes=[256,2000,8000,20000],forms=['ordinary','command','redaction_command'];
const finite=v=>typeof v==='number'&&Number.isFinite(v)&&v>=0;
const exact=(value,keys)=>value&&typeof value==='object'&&!Array.isArray(value)&&Object.keys(value).sort().join('|')===[...keys].sort().join('|');
function checkSummary(value){
 if(!exact(value,['sample_count','p50_ms','p95_ms','max_ms','quantile_method','durations_ms'])||value.sample_count!==20||value.quantile_method!=='nearest_rank'||!Array.isArray(value.durations_ms)||value.durations_ms.length!==20||!value.durations_ms.every(finite))throw Error('Invalid service timing samples');
 const ordered=[...value.durations_ms].sort((a,b)=>a-b);
 if(value.p50_ms!==ordered[9]||value.p95_ms!==ordered[18]||value.max_ms!==ordered[19])throw Error('Service timing summary differs from observations');
}
export function validatePipelineTiming(data,readHash){
 const keys=['captured_at','pass','kind','sources','source_unchanged','declared_hardware','declared_input_lengths',
  'repeats_per_profile','profile_count','rows','processing_scope','wire_latency_field',
  'command_profile_allows_configured_url_redaction','first_observed_is_not_service_cold_start','population_latency_inferred',
  'accepted_latency_budget_ms','user_content_used','submitted_payloads_executed','production_services_started_or_changed',
  'independent_accuracy_evidence','release_approved'];
 if(!exact(data,keys)||data.pass!==true||data.kind!=='synthetic_staging_pipeline_timing'||data.source_unchanged!==true||
  data.command_profile_allows_configured_url_redaction!==true||data.first_observed_is_not_service_cold_start!==true||
  data.population_latency_inferred!==false||data.accepted_latency_budget_ms!==null||data.user_content_used!==false||
  data.submitted_payloads_executed!==false||data.production_services_started_or_changed!==false||
  data.independent_accuracy_evidence!==false||data.release_approved!==false||data.repeats_per_profile!==20||data.profile_count!==12||
  JSON.stringify(data.declared_input_lengths)!==JSON.stringify(sizes)||!Number.isFinite(Date.parse(data.captured_at))||
  data.processing_scope!=='Authenticated loopback gateway, English redaction and evaluator; not remote network, browser or physical phone startup.'||
  data.wire_latency_field!=='evaluator.latency_ms — gateway pipeline duration, not detector-only time')throw Error('Invalid service timing classification');
 if(!exact(data.sources,timingSources)||timingSources.some(p=>!/^[a-f0-9]{64}$/.test(data.sources[p])||data.sources[p]!==readHash(p)))throw Error('Stale service timing source');
 const hardware=data.declared_hardware;
 if(!exact(hardware,['system','release','machine','logical_cpus','client_python'])||hardware.system!=='Linux'||
  !['x86_64','aarch64','arm64','AMD64'].includes(hardware.machine)||!Number.isSafeInteger(hardware.logical_cpus)||hardware.logical_cpus<1||hardware.logical_cpus>4096||
  !/^[0-9]+\.[0-9]+\.[0-9]+$/.test(hardware.client_python)||!/^[A-Za-z0-9+._-]{1,120}$/.test(hardware.release))throw Error('Missing declared staging hardware');
 if(!Array.isArray(data.rows)||data.rows.length!==12)throw Error('Missing service timing profiles');
 const seen=new Set();
 for(const row of data.rows){
  if(!exact(row,['form','input_length_codepoints','input_bytes_utf8','first_observed_round_trip_ms','first_observed_reported_pipeline_ms','warm_round_trip','warm_reported_pipeline'])||
   !forms.includes(row.form)||!sizes.includes(row.input_length_codepoints)||row.input_bytes_utf8!==row.input_length_codepoints||
   !finite(row.first_observed_round_trip_ms)||!finite(row.first_observed_reported_pipeline_ms))throw Error('Invalid service timing profile');
  const key=row.form+'/'+row.input_length_codepoints;if(seen.has(key))throw Error('Duplicate service timing profile');seen.add(key);
  checkSummary(row.warm_round_trip);checkSummary(row.warm_reported_pipeline);
 }
 return data;
}
export function pipelineTimingFor(tag,data){
 if(!['PS','PII_REDACTED'].includes(tag.id))return null;
 return {kind:'synthetic_staging_pipeline_timing',measured_at:data.captured_at,logical_cpus:data.declared_hardware.logical_cpus,
  sample_count_per_profile:20,profile_count:12,accuracy_evidence:false,budget_accepted:false,
  download:'/reference/pipeline-performance.json',
  rows:sizes.map(size=>({input_length_codepoints:size,p95_ms:Math.max(...data.rows.filter(r=>r.input_length_codepoints===size).map(r=>r.warm_round_trip.p95_ms))}))};
}
export const milliseconds=value=>value<1000?`${Math.ceil(value)} ms`:`${(value/1000).toFixed(2)} s`;
export const timingNote=data=>`20 repeats per profile on Linux (${data.logical_cpus} logical CPUs). Bars show the slowest profile’s warm p95, not a speed guarantee.`;
export function pipelineTimingHTML(data,esc){
 if(!data)return '';
 const maximum=Math.max(...data.rows.map(r=>r.p95_ms),1);
 return `<details data-service-timing class="mt-3"><summary class="min-h-11 cursor-pointer py-3 font-semibold">Local service speed</summary><p class="mb-2 text-muted">Includes redaction and tagging. The phone preview uses a different route.</p><dl class="space-y-2">${data.rows.map(r=>`<div><dt class="text-muted">${r.input_length_codepoints.toLocaleString('en-US')} characters</dt><dd class="tabular-nums">${esc(milliseconds(r.p95_ms))}<div class="h-1 rounded-full bg-line" aria-hidden="true"><div class="h-1 rounded-full bg-ink" style="width:${r.p95_ms/maximum*100}%"></div></div></dd></div>`).join('')}</dl><p class="mt-2 text-muted">${esc(timingNote(data))}</p><p class="mt-1 text-muted">Measured ${esc(data.measured_at.slice(0,10))} · synthetic inputs</p><a class="inline-block min-h-11 py-3 underline underline-offset-4" href="${esc(data.download)}" download>Download service timings</a></details>`;
}
