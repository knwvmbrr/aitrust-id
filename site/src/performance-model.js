// No content, identities or runtime heuristic scores enter public measurements.
export function validateEvidence(data, readHash) {
 if(data.format!=='ai-trust-id-performance-evidence/v1'||data.kind!=='development_regression'||data.independently_labeled!==false||data.release_validated!==false)throw Error('Invalid performance evidence classification');
 if(data.timing_source_sha256!==readHash('protocol/measurements.py'))throw Error('Stale timing implementation');
 if(data.measurement_source_sha256!==readHash('eval/harness.py')||data.category_source_sha256!==readHash('protocol/categories.py'))throw Error('Stale measurement implementation');
 if(data.normalization_sha256!==readHash('protocol/normalization.py')||data.normalization_data_sha256!==readHash('protocol/unicode15-data.json'))throw Error('Stale performance normalization: rerun measurements');
 if(data.method_sha256!==readHash('services/evaluator/app.py')||data.gates_sha256!==readHash('eval/gates.yaml'))throw Error('Stale performance method or gates: rerun measurements');
 for(const row of data.fixtures)if(row.sha256!==readHash(row.path))throw Error('Stale performance fixture');
 for(const [path,hash] of Object.entries(data.evidence_sha256))if(hash!==readHash(path))throw Error('Measured source report changed');
 const keys=['tp','fp','fn','tn'];if(keys.some(k=>!Number.isSafeInteger(data.counts[k])||data.counts[k]<0)||keys.reduce((n,k)=>n+data.counts[k],0)!==data.case_count)throw Error('Performance count mismatch');
 if(data.confidence!==0.95)throw Error('Unsupported confidence method');
 const grouped={tp:0,fp:0,fn:0,tn:0};const seen=new Set();
 if(!Array.isArray(data.category_metrics)||!data.category_metrics.length)throw Error('Missing category measurements');
 for(const row of data.category_metrics){
  const key=row.source_dataset+'/'+row.category;if(seen.has(key))throw Error('Duplicate category result');seen.add(key);
  for(const count of keys){if(!Number.isSafeInteger(row[count])||row[count]<0)throw Error('Invalid category count');grouped[count]+=row[count];}
  if(row.n!==keys.reduce((n,key)=>n+row[key],0))throw Error('Category count mismatch');
  for(const [metric,successes,denominator] of [['precision',row.tp,row.tp+row.fp],['recall',row.tp,row.tp+row.fn],['false_positive_rate',row.fp,row.fp+row.tn],['false_negative_rate',row.fn,row.fn+row.tp]])assertMetric(row[metric],successes,denominator);
  if(row.calibration?.ece!==null||row.calibration?.observations!==0)throw Error('Unmeasured category calibration claimed');
 }
 if(keys.some(k=>grouped[k]!==data.counts[k]))throw Error('Category totals differ from global counts');
 if(data.metrics.length!==2)throw Error('Missing PS metrics');
 for(const [id,denominator] of [['precision',data.counts.tp+data.counts.fp],['recall',data.counts.tp+data.counts.fn]]){
  const row=data.metrics.find(r=>r.id===id);
  assertMetric(row,data.counts.tp,denominator);
 }
 for(const engine of data.mobile.engines)validateTiming(engine.timing,engine.case_count);
 return data;
}
export function validateTiming(timing,total){
 if(!timing||!Array.isArray(timing.samples)||timing.samples.length!==total||total!==timing.sample_count||!total)throw Error('Missing timing samples');
 const ids=new Set();for(const row of timing.samples){if(typeof row.case_id!=='string'||ids.has(row.case_id)||!Number.isFinite(row.duration_ms)||row.duration_ms<0||!Number.isSafeInteger(row.input_length_codepoints)||row.input_length_codepoints<0)throw Error('Invalid timing observation');ids.add(row.case_id);}
 const quantiles=rows=>{const values=rows.map(r=>r.duration_ms).sort((a,b)=>a-b);return [values[Math.ceil(values.length*.5)-1],values[Math.ceil(values.length*.95)-1]];};
 const check=(rows,metrics)=>{const [p50,p95]=quantiles(rows);if(metrics?.sample_count!==rows.length||metrics?.p50_ms!==p50||metrics?.p95_ms!==p95)throw Error('Timing summary differs from observations');};
 check(timing.samples,timing);const categories=new Set(timing.samples.map(r=>r.category));
 if(Object.keys(timing.per_category||{}).length!==categories.size)throw Error('Missing category timing');
 for(const category of categories)check(timing.samples.filter(r=>r.category===category),timing.per_category[category]);
 const lengths=timing.samples.map(r=>r.input_length_codepoints);if(timing.input_lengths_codepoints?.min!==Math.min(...lengths)||timing.input_lengths_codepoints?.max!==Math.max(...lengths)||!Number.isFinite(timing.cold_load_ms)||timing.cold_load_ms<0)throw Error('Invalid declared timing environment');
 return timing;
}

function assertMetric(row,successes,denominator){
 if(!row||row.successes!==successes||row.denominator!==denominator||row.point!==(denominator?successes/denominator:null))throw Error('Performance denominator mismatch');
 if(!denominator){if(row.interval!==null)throw Error('Unmeasured metric fabricated');return;}
 const z=1.959963984540054,p=successes/denominator,d=1+z*z/denominator,c=(p+z*z/(2*denominator))/d,r=z*Math.sqrt(p*(1-p)/denominator+z*z/(4*denominator*denominator))/d;
 const expected=[Math.max(0,c-r),Math.min(1,c+r)];
 if(!Array.isArray(row.interval)||row.interval.length!==2||row.interval.some((x,i)=>!Number.isFinite(x)||Math.abs(x-expected[i])>1e-10))throw Error('Confidence range differs from Wilson calculation');
}

const nextTests={
 PS:'A new frozen, independently labeled set, followed by release acceptance.',
 PII_REDACTED:'Measure missed and false redactions by entity category; independently review coverage.',
 NF:'Benchmark supported and unsupported claims against a declared reference corpus.',
 FI:'Test actual reference contradictions separately from missing evidence.',
 HP:'Validate specific indicators against independently labeled unsupported claims.',
 MT:'Compare helpful and pressuring messages, with independent reviewers checking the context.',
 IV:'Verify reviewer identity, independence, artifact binding and challenges.',
 FA:'Test positive generation evidence, binding and unknown-source behavior.',
 PA:'Test contribution/edit receipts, consent and assistive-input handling.',
 UNK:'Test insufficient evidence separately from unavailable and unsupported checks.',
 PII_OUTBOUND:'Test pre-send detection, explicit choice and fail-safe interception.',
 UC:'Agree the proposed code contract and independently validate command contexts.',
 SC:'Measure fraud-indicator false alarms, misses and legitimate look-alikes.',
 BT:'Test positive automation evidence against human and assistive-input counterexamples.',
 fleet:'Test deployment, version rollback and per-tag policy isolation.',
 host:'Test consented capture, permissions and artifact binding.',
 audit:'Test record retention, corrections, authorized access and deletion.',
 sso:'Test access roles, revocation and organization separation.',
 support:'Validate the actual support workflow before promising response times.',
 proprietary:'Test private-policy boundaries without weakening public tag standards.'
};
export function performanceFor(tag,evidence) {
 const working=['PS','PII_REDACTED'].includes(tag.id);
 const base={id:tag.id,stage:working?'Working preview':'Not running',independently_validated:false,
  accuracy_measured:false,metrics:[],next_test:nextTests[tag.id]||'Define and execute this capability’s acceptance tests.',
  summary:tag.id==='PII_REDACTED'?'Redaction procedure checked; recognition accuracy not measured.':tag.audience==='enterprise'?'Organization capability; performance not measured.':'No measured results for this tag yet.',
  sources:[],device:null};
 if(tag.id!=='PS')return base;
 return {...base,accuracy_measured:true,summary:'Development examples · not an independent accuracy study',
  categories:categoryGroups(evidence.category_metrics),measured_at:evidence.captured_at,metrics:evidence.metrics,counts:evidence.counts,case_count:evidence.case_count,
  confidence:evidence.confidence,device:evidence.mobile,sizing:evidence.sizing,
  sources:['/reference/tag-performance-evidence.json','/reference/performance-regressions.json','/reference/performance-device.json']};
}
const categoryLabels={encoded_content_forms:'Encoded content',file_download_forms:'Downloads saved to files',quoted_or_discussed_download_forms:'Quoted or discussed downloads',other_download_forms:'Other download commands',other_code_forms:'Other code forms',ordinary_text_forms:'Ordinary answers'};
export function categoryGroups(rows){
 const groups=new Map();for(const row of rows){if(!Object.hasOwn(categoryLabels,row.category))throw Error('Unknown category presentation');const group=groups.get(row.category)||{id:row.category,label:categoryLabels[row.category],n:0,fp:0,fn:0};group.n+=row.n;group.fp+=row.fp;group.fn+=row.fn;groups.set(row.category,group);}return [...groups.values()];
}

export const percent=value=>`${(value*100).toFixed(1)}%`;
export function performanceHTML(record,esc) {
 const rows=record.metrics.map(m=>`<div class="performance-row"><div class="flex flex-wrap justify-between gap-2"><h3 class="text-sm font-semibold">${esc(m.label)}</h3><span class="tabular-nums text-sm">${m.denominator?esc(percent(m.point)):'Not measured'} · ${m.successes}/${m.denominator}</span></div>${m.interval?`<div class="performance-track" aria-hidden="true"><span class="performance-range" style="left:${m.interval[0]*100}%;width:${(m.interval[1]-m.interval[0])*100}%"></span><span class="performance-target" style="left:${m.candidate_lower_bound*100}%"></span></div><p class="text-xs text-muted">95% range ${esc(percent(m.interval[0]))}–${esc(percent(m.interval[1]))} · candidate lower bound ${esc(percent(m.candidate_lower_bound))}</p>`:''}<p class="text-xs text-muted">${esc(m.description)}</p></div>`).join('');
 const counts=record.counts?`<dl class="mt-3 grid grid-cols-2 gap-2 text-xs tabular-nums">${[['Correct alerts','tp'],['False alerts','fp'],['Missed patterns','fn'],['Correctly unflagged','tn']].map(([label,key])=>`<div><dt class="text-muted">${label}</dt><dd class="font-semibold">${record.counts[key]}</dd></div>`).join('')}</dl>`:'';
 const categories=record.categories?.length?`<details class="mt-3"><summary class="min-h-11 cursor-pointer py-3 font-semibold">Test breakdown</summary><p class="mb-2 text-muted">Development input groups, not a representative accuracy study.</p><dl class="space-y-2">${record.categories.map(c=>`<div class="border-b border-line pb-2"><dt class="font-semibold">${esc(c.label)}</dt><dd class="tabular-nums">${c.n} examples · ${c.fp} false alerts · ${c.fn} missed patterns</dd></div>`).join('')}</dl></details>`:'';
 return `<section data-tag-performance="${esc(record.id)}" aria-label="Tag performance" class="my-4 rounded-xl border border-line p-4"><div class="flex flex-wrap justify-between gap-2"><h2 class="text-sm font-semibold">Performance</h2><span class="text-xs text-muted">${esc(record.stage)}</span></div><p class="mt-1 text-sm">${esc(record.summary)}</p>${rows}${counts}${categories}<p class="mt-2 text-xs text-muted">${record.case_count?`${record.case_count} development examples. Range shows sampling uncertainty; tuned examples do not establish real-world accuracy. `:''}Independent release validation: pending.</p>${record.measured_at?`<p class="mt-1 text-xs text-muted">Measured ${esc(record.measured_at.slice(0,10))}</p>`:''}<p class="mt-2 text-xs"><strong>Next test:</strong> ${esc(record.next_test)}</p></section>`;
}
