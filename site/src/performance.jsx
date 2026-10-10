import React from 'react';
import data from './tag-performance.json';
import {percent} from './performance-model.js';
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
  {r.measured_at&&<p className="mt-2 text-muted">Measured {r.measured_at.slice(0,10)}</p>}
  <p className="mt-2"><strong>Next test:</strong> {r.next_test}</p>
  {r.sources.length>0&&<a className="mt-2 inline-block min-h-11 py-3 underline underline-offset-4" href={r.sources[0]} download>Download measured data</a>}
 </div>;
}
