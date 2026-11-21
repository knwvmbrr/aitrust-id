import React,{useEffect,useId,useRef,useState} from 'react';
import {clsx} from 'clsx';import {twMerge} from 'tailwind-merge';
const cn=(...values)=>twMerge(clsx(values));
import {hpUncertaintyClient,validUncertaintyInput,manifest} from './hp-uncertainty-client.js';
import {explainUncertainty} from './hp-uncertainty-result.js';
const button='min-h-11 rounded-lg border border-line bg-surface px-4 py-3 text-sm font-medium disabled:opacity-50';
export function HPUncertaintyExplorer(){
 const id=useId(),generation=useRef(0),client=useRef(null),input=useRef(null),confirmation=useRef(null),result=useRef(null);
 const [text,setText]=useState(''),[selected,setSelected]=useState(false),[record,setRecord]=useState(null),[details,setDetails]=useState(false),[busy,setBusy]=useState(false),[status,setStatus]=useState(''),[error,setError]=useState(''),[invalid,setInvalid]=useState('');
 function reset(){generation.current++;client.current?.stop();client.current=null;setRecord(null);setDetails(false);setBusy(false);setStatus('');setError('');setInvalid('');}
 useEffect(()=>()=>{generation.current++;client.current?.stop();},[]);
 useEffect(()=>{if(record)result.current?.focus({preventScroll:true});},[record]);
 async function run(event){
  event.preventDefault();reset();const own=generation.current;
  try{validUncertaintyInput(text);}catch{setInvalid('text');setError('Use an English passage up to 8,000 characters. Some Unicode word-boundary forms are unavailable; your full text is unchanged.');input.current?.focus();return;}
  if(!selected){setInvalid('selection');setError('Choose the whole-passage context before checking. This tool does not decide where uncertainty is needed.');confirmation.current?.focus();return;}
  setBusy(true);client.current=hpUncertaintyClient({onStatus:value=>{if(own===generation.current)setStatus(value);}});
  try{const value=await client.current.check(text,selected);if(own!==generation.current)return;setRecord(value);setStatus('Wording check complete.');}
  catch{if(own===generation.current){setStatus('');setError('Unavailable: this wording check could not finish. No result was issued. Other checks remain separate.');}}
  finally{if(own===generation.current){setBusy(false);client.current=null;}}
 }
 const explanation=record?explainUncertainty(record):null;
 return <section data-hp-uncertainty aria-labelledby={id+'-heading'} className="mt-4 min-w-0 rounded-xl border border-line bg-surface p-4 text-sm leading-6">
  <h3 id={id+'-heading'} className="text-base font-semibold text-balance">Look for uncertainty words</h3>
  <p className="mt-1 text-pretty">Choose a passage where you expect uncertainty to be expressed. Look for words such as “may,” “might” or “likely.”</p>
  <p className="mt-2 text-xs text-muted text-pretty">Optional HP method preview · No HP tag is issued. Text stays on this page, without upload or saving. The first run downloads the on-device Python runtime.</p>
  <form onSubmit={run} aria-busy={busy} className="mt-4 min-w-0">
   <label htmlFor={id+'-text'} className="block font-semibold">English passage</label>
   <textarea ref={input} id={id+'-text'} rows={4} value={text} spellCheck={false} autoComplete="off" autoCorrect="off" autoCapitalize="off" onChange={e=>{reset();setText(e.target.value);setSelected(false);}} aria-invalid={invalid==='text'?true:undefined} aria-describedby={id+'-limit'+(invalid==='text'?' '+id+'-error':'')} className="mt-1 block w-full min-w-0 resize-y rounded-lg border border-input bg-surface p-3 text-base"/>
   <p id={id+'-limit'} className="mt-1 text-xs text-muted tabular-nums">{Array.from(text).length.toLocaleString()} / {manifest.max_codepoints.toLocaleString()} characters · No text is clipped.</p>
   <label className="mt-3 flex min-h-11 items-start gap-3 text-pretty"><input ref={confirmation} type="checkbox" checked={selected} onChange={e=>{reset();setSelected(e.target.checked);}} aria-invalid={invalid==='selection'?true:undefined} aria-describedby={invalid==='selection'?id+'-error':id+'-context-limit'} className="mt-1.5"/><span>I expect uncertainty to be expressed in this whole passage.</span></label>
   <p id={id+'-context-limit'} className="mt-1 text-xs text-muted text-pretty">That context is your choice, not an independent judgment by the checker.</p>
   {error&&<p id={id+'-error'} role="alert" className="mt-2 text-pretty">{error}</p>}
   <div className="mt-3 flex flex-wrap gap-2"><button type="submit" disabled={busy} className={cn(button)}>{busy?'Checking wording…':'Check uncertainty words'}</button>{busy&&<button type="button" className={cn(button)} onClick={()=>{reset();setStatus('Cancelled. No result was issued.');}}>Cancel wording check</button>}<button type="button" className={cn(button)} onClick={()=>{reset();setText('');setSelected(false);}}>Clear passage</button></div>
  </form><p role="status" className="mt-2">{status}</p>
  {record&&<section ref={result} tabIndex={-1} aria-label="Uncertainty wording result" className="mt-4 rounded-lg border border-line bg-canvas p-3">
   <h4 className="font-semibold text-balance">{explanation.title}</h4><p className="mt-1 text-pretty">{explanation.body}</p>
   <dl className="mt-3 grid grid-cols-2 gap-2 tabular-nums"><div><dt className="text-xs text-muted">Listed words</dt><dd className="font-semibold">{record.counts.hedge_words}</dd></div><div><dt className="text-xs text-muted">Calendar exclusions</dt><dd className="font-semibold">{record.counts.calendar_candidates}</dd></div></dl>
   <p className="mt-2 text-xs text-muted text-pretty">“May 12” is a calendar candidate, not a verified date. “Not likely” still contains a listed word; negation, word sense and confidence are not interpreted.</p>
   <details open={details} onToggle={e=>setDetails(e.currentTarget.open)} className="mt-3 border-t border-line pt-2"><summary className="flex min-h-11 cursor-pointer items-center font-semibold">Method and exact positions</summary>{details&&<><p className="mt-1 text-xs text-muted text-pretty">Private fingerprints, your context selection and NFC positions can link text. Your pasted text is not included. Share deliberately.</p><pre aria-label="Private uncertainty evidence" tabIndex={0} className="mt-2 max-h-72 overflow-auto whitespace-pre-wrap break-all rounded-lg border border-line bg-surface p-3 text-xs">{JSON.stringify(record,null,2)}</pre></>}</details>
  </section>}
  <p className="mt-3 text-xs text-muted"><a href="/hp-uncertainty-device/notices.txt" className="inline-flex min-h-11 items-center underline underline-offset-4">Source notices</a><span aria-hidden="true"> · </span><a href="/device-licenses/source.txt" className="inline-flex min-h-11 items-center underline underline-offset-4">Runtime source notices</a></p>
 </section>;
}
