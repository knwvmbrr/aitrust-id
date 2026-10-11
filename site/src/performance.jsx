import React from 'react';
import {redactionBrief,redactionLabel} from './redaction-performance-model.js';
import data from './tag-performance.json';
import {percent} from './performance-model.js';
import {milliseconds,timingNote} from './pipeline-timing-model.js';
export const performanceById=new Map(data.records.map(r=>[r.id,r]));
export function Performance({tag}) {
 const r=performanceById.get(tag.id);
 return <section data-tag-performance={tag.id} aria-label="Tag performance" className={r.metrics.length?"my-4 rounded-xl border border-line p-4":"my-4 py-1"}>
  <div className="flex flex-wrap justify-between gap-2"><h3 className="text-sm font-semibold">Performance</h3><span className="text-xs text-muted">{r.stage}</span></div>
  <p className="mt-1 text-xs leading-5 text-muted">{r.id==='PS'?'Development fixtures · not an independent study':r.summary}</p>
  <div className="performance-grid">{r.metrics.map(m=><div key={m.id} className="performance-row">
   <h4 className="text-xs font-semibold">{m.label}</h4><p className="text-sm font-semibold tabular-nums">{m.denominator?`${m.successes}/${m.denominator}`:'Not measured'}</p>
   {m.interval&&<><div className="performance-track" aria-hidden="true"><span className="performance-range" style={{left:percent(m.interval[0]),width:percent(m.interval[1]-m.interval[0])}}/><span className="performance-target" style={{left:percent(m.candidate_lower_bound)}}/></div><p className="text-xs text-muted tabular-nums">95% range {percent(m.interval[0])}–{percent(m.interval[1])}</p><p className="text-xs text-muted tabular-nums">Target lower bound {percent(m.candidate_lower_bound)}</p></>}
  </div>)}</div>
  {r.redaction&&<p className="mt-2 text-xs leading-5 tabular-nums">{redactionBrief(r.redaction)}</p>}
  {r.counts&&<p className="mt-3 text-xs leading-5 tabular-nums">{r.case_count} examples · {r.counts.fp} false alerts · {r.counts.fn} missed patterns</p>}
  <p className="mt-2 text-xs text-muted">Independent release validation: pending.</p>
  {!r.metrics.length&&<p className="mt-2 text-xs leading-5"><strong>Next test:</strong> {r.next_test}</p>}
 </section>;
}
export function PerformanceEvidence({tag}) {
 const r=performanceById.get(tag.id);
 return <div className="my-3 text-xs leading-5">
  {r.metrics.map(m=><p key={m.id}>{m.label}: {m.description} {m.denominator?`${m.successes}/${m.denominator} (${percent(m.point)}) in the development set.`:'Not measured.'}</p>)}
  {r.counts&&<p className="mt-2 tabular-nums">Correct alerts {r.counts.tp} · False alerts {r.counts.fp} · Missed patterns {r.counts.fn} · Correctly unflagged {r.counts.tn}. Wilson 95% ranges show sampling uncertainty, not a real-world accuracy certification. These examples were used during development.</p>}
  {r.device?.engines.length>0&&<div className="mt-3"><h4 className="font-semibold">Phone browser tests · emulated</h4><ul className="mt-1 space-y-1 tabular-nums">{r.device.engines.map(e=><li key={e.name}>{e.name}: {e.case_count}/{e.case_count} method-parity cases{e.timing&&` · warm p95 ${e.timing.p95_ms.toFixed(1)} ms`}</li>)}</ul><p className="mt-1 text-muted">Desktop-hosted emulation; warm checks exclude first runtime load. Physical-phone acceptance is pending.</p></div>}
  {r.categories?.length>0&&<details className="mt-3"><summary className="min-h-11 cursor-pointer py-3 font-semibold">Test breakdown</summary><p className="mb-2 text-muted">Development input groups, not a representative accuracy study.</p><dl className="space-y-2">{r.categories.map(c=><div key={c.id} className="border-b border-line pb-2"><dt className="font-semibold">{c.label}</dt><dd className="tabular-nums">{c.n} examples · {c.fp} false alerts · {c.fn} missed patterns</dd></div>)}</dl></details>}
  {r.redaction&&<RedactionTests data={r.redaction}/>}
  {r.pipeline&&<ServiceTiming data={r.pipeline}/>}
  {r.measured_at&&<p className="mt-2 text-muted">Measured {r.measured_at.slice(0,10)}</p>}
  <p className="mt-2"><strong>Next test:</strong> {r.next_test}</p>
  {r.sources.length>0&&<a className="mt-2 inline-block min-h-11 py-3 underline underline-offset-4" href={r.sources[0]} download>Download measured data</a>}
 </div>;
}
function ServiceTiming({data}) {
 const maximum=Math.max(...data.rows.map(r=>r.p95_ms),1);
 return <details data-service-timing className="mt-3"><summary className="min-h-11 cursor-pointer py-3 font-semibold">Local service speed</summary>
  <p className="mb-2 text-muted">Includes redaction and tagging. The phone preview uses a different route.</p>
  <dl className="space-y-2">{data.rows.map(r=><div key={r.input_length_codepoints}><dt className="text-muted">{r.input_length_codepoints.toLocaleString('en-US')} characters</dt><dd className="tabular-nums">{milliseconds(r.p95_ms)}<div className="h-1 rounded-full bg-line" aria-hidden="true"><div className="h-1 rounded-full bg-ink" style={{width:`${r.p95_ms/maximum*100}%`}}/></div></dd></div>)}</dl>
  <p className="mt-2 text-muted">{timingNote(data)}</p><p className="mt-1 text-muted">Measured {data.measured_at.slice(0,10)} · synthetic inputs</p>
  <a className="inline-block min-h-11 py-3 underline underline-offset-4" href={data.download} download>Download service timings</a>
 </details>;
}

function RedactionTests({data}) {
 return <details data-redaction-recognition className="mt-3"><summary className="min-h-11 cursor-pointer py-3 font-semibold">Redaction test breakdown</summary>
  <p className="mb-2 text-muted text-pretty">Synthetic examples on the English service, not the phone preview.</p><p className="mb-3 tabular-nums text-pretty">{redactionBrief(data)}</p>
  <dl className="space-y-2">{data.categories.map(c=><div key={c.entity} className="border-b border-line pb-2"><dt className="font-semibold">{redactionLabel(c.entity)}</dt><dd className="tabular-nums">{c.tp}/{c.expected} exact finds · {c.fn} missed · {c.fp} extra candidates<div className="h-1 rounded-full bg-line" aria-hidden="true"><div className="h-1 rounded-full bg-ink" style={{width:`${c.expected?c.tp/c.expected*100:0}%`}}/></div></dd></div>)}</dl>
  <p className="mt-2 tabular-nums">{data.other_extra_candidates} extra candidates from other recognizers.</p><p className="mt-3 text-muted text-pretty">Candidates can overlap. An extra candidate is not necessarily an extra redaction. Extra masking can remove ordinary text.</p>
  <p className="mt-2 tabular-nums text-pretty">Four out-of-coverage challenges: {data.challenges.fully_masked}/{data.challenges.expected} expected identifiers fully masked; {data.challenges.partial} partially masked and {data.challenges.untouched} untouched.</p>
  <p className="mt-3 tabular-nums text-pretty">Compact IP label checks: {data.compact.fully_masked}/{data.compact.expected} expected addresses masked in six additional synthetic examples; {data.compact.cases_with_extra_masking}/6 examples had extra masking ({data.compact.extra_masked_characters} characters).</p>
  <a className="inline-block min-h-11 py-3 underline underline-offset-4" href={data.compact.report} download>Download compact IP tests</a>
  <p className="mt-2 text-muted text-pretty">{data.limits} Other identifiers or sensitive context may be missed. Review before sharing.</p>
  <a className="inline-block min-h-11 py-3 underline underline-offset-4" href={data.sources.report} download>Download redaction observations</a>
 </details>;
}
