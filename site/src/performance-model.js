// No content, identities or runtime heuristic scores enter public measurements.
export function validateEvidence(data, readHash) {
 if(data.format!=='ai-trust-id-performance-evidence/v1'||data.kind!=='development_regression'||data.independently_labeled!==false||data.release_validated!==false)throw Error('Invalid performance evidence classification');
 if(data.method_sha256!==readHash('services/evaluator/app.py')||data.gates_sha256!==readHash('eval/gates.yaml'))throw Error('Stale performance method or gates: rerun measurements');
 for(const row of data.fixtures)if(row.sha256!==readHash(row.path))throw Error('Stale performance fixture');
 for(const [path,hash] of Object.entries(data.evidence_sha256))if(hash!==readHash(path))throw Error('Measured source report changed');
 const keys=['tp','fp','fn','tn'];if(keys.some(k=>!Number.isSafeInteger(data.counts[k])||data.counts[k]<0)||keys.reduce((n,k)=>n+data.counts[k],0)!==data.case_count)throw Error('Performance count mismatch');
 if(data.metrics.length!==2)throw Error('Missing PS metrics');
 for(const [id,denominator] of [['precision',data.counts.tp+data.counts.fp],['recall',data.counts.tp+data.counts.fn]]){
  const row=data.metrics.find(r=>r.id===id);
  if(!row||row.denominator!==denominator||row.successes!==data.counts.tp||row.point!==(denominator?data.counts.tp/denominator:null))throw Error('Performance denominator mismatch');
  if(denominator){if(!Array.isArray(row.interval)||row.interval.length!==2||row.interval.some(v=>!Number.isFinite(v)||v<0||v>1)||row.interval[0]>row.point||row.interval[1]<row.point)throw Error('Invalid confidence range');}
  else if(row.interval!==null)throw Error('Unmeasured metric fabricated');
 }
 return data;
}
const nextTests={
 PS:'A new frozen, independently labeled set, followed by release acceptance.',
 PII_REDACTED:'Measure missed and false redactions by entity category; independently review coverage.',
 NF:'Benchmark supported and unsupported claims against a declared reference corpus.',
 FI:'Test actual reference contradictions separately from missing evidence.',
 HP:'Validate specific indicators against independently labeled unsupported claims.',
 MT:'Measure context-sensitive tactic errors and reviewer agreement.',
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
  measured_at:evidence.captured_at,metrics:evidence.metrics,counts:evidence.counts,case_count:evidence.case_count,
  confidence:evidence.confidence,device:evidence.mobile,sizing:evidence.sizing,
  sources:['/reference/tag-performance-evidence.json','/reference/performance-regressions.json','/reference/performance-device.json']};
}
export const percent=value=>`${(value*100).toFixed(1)}%`;
export function performanceHTML(record,esc) {
 const rows=record.metrics.map(m=>`<div class="performance-row"><div class="flex flex-wrap justify-between gap-2"><h3 class="text-sm font-semibold">${esc(m.label)}</h3><span class="tabular-nums text-sm">${m.denominator?esc(percent(m.point)):'Not measured'} · ${m.successes}/${m.denominator}</span></div>${m.interval?`<div class="performance-track" aria-hidden="true"><span class="performance-range" style="left:${m.interval[0]*100}%;width:${(m.interval[1]-m.interval[0])*100}%"></span><span class="performance-target" style="left:${m.candidate_lower_bound*100}%"></span></div><p class="text-xs text-muted">95% range ${esc(percent(m.interval[0]))}–${esc(percent(m.interval[1]))} · candidate lower bound ${esc(percent(m.candidate_lower_bound))}</p>`:''}<p class="text-xs text-muted">${esc(m.description)}</p></div>`).join('');
 const counts=record.counts?`<dl class="mt-3 grid grid-cols-2 gap-2 text-xs tabular-nums">${[['Correct alerts','tp'],['False alerts','fp'],['Missed patterns','fn'],['Correctly unflagged','tn']].map(([label,key])=>`<div><dt class="text-muted">${label}</dt><dd class="font-semibold">${record.counts[key]}</dd></div>`).join('')}</dl>`:'';
 return `<section data-tag-performance="${esc(record.id)}" aria-label="Tag performance" class="my-4 rounded-xl border border-line p-4"><div class="flex flex-wrap justify-between gap-2"><h2 class="text-sm font-semibold">Performance</h2><span class="text-xs text-muted">${esc(record.stage)}</span></div><p class="mt-1 text-sm">${esc(record.summary)}</p>${rows}${counts}<p class="mt-2 text-xs text-muted">${record.case_count?`${record.case_count} development examples. Range shows sampling uncertainty; tuned examples do not establish real-world accuracy. `:''}Independent release validation: pending.</p>${record.measured_at?`<p class="mt-1 text-xs text-muted">Measured ${esc(record.measured_at.slice(0,10))}</p>`:''}<p class="mt-2 text-xs"><strong>Next test:</strong> ${esc(record.next_test)}</p></section>`;
}
