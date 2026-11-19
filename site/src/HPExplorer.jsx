import React,{useEffect,useId,useRef,useState} from 'react';
import {clsx} from 'clsx';import {twMerge} from 'tailwind-merge';
import {hpDeviceClient,validHPInput,manifest} from './hp-device-client.js';
import {explainHP} from './hp-device-result.js';
const cn=(...values)=>twMerge(clsx(values));const button='min-h-11 rounded-lg border border-line bg-surface px-4 py-3 text-sm font-medium disabled:opacity-50';
export function HPExplorer(){
 const uid=useId(),generation=useRef(0),client=useRef(null),input=useRef(null),resultRef=useRef(null);
 const [text,setText]=useState(''),[busy,setBusy]=useState(false),[status,setStatus]=useState(''),[error,setError]=useState(''),[inputError,setInputError]=useState(false),[record,setRecord]=useState(null),[details,setDetails]=useState(false);
 function reset(){generation.current++;client.current?.stop();client.current=null;setRecord(null);setBusy(false);setStatus('');setError('');setInputError(false);setDetails(false);}
 useEffect(()=>()=>{generation.current++;client.current?.stop();},[]);
 useEffect(()=>{if(record)resultRef.current?.focus({preventScroll:true});},[record]);
 async function run(event){
  event.preventDefault();reset();const own=generation.current;
  try{validHPInput(text);}catch{setError('Paste English text, up to 8,000 characters, without invalid control characters.');setInputError(true);input.current?.focus();return;}
  setBusy(true);client.current=hpDeviceClient({onStatus:message=>{if(own===generation.current)setStatus(message);}});
  try{const value=await client.current.check(text);if(own!==generation.current)return;setRecord(value);setStatus('Detail check complete.');}
  catch{if(own===generation.current){setStatus('');setError('This check couldn’t finish. No result was issued. Try a shorter passage or try again.');}}
  finally{if(own===generation.current){client.current=null;setBusy(false);}}
 }
 const explanation=record?explainHP(record):null;
 return <section data-hp-explorer aria-labelledby={uid+'-heading'} className="mt-4 min-w-0 rounded-xl border border-line bg-surface p-4 text-sm leading-6">
  <h3 id={uid+'-heading'} className="text-base font-semibold text-balance">Explore the details</h3>
  <p className="mt-1 text-pretty">Find numbers and date-shaped text, then see whether a source marker appears in the same sentence unit.</p>
  <p className="mt-2 text-xs text-muted">HP method preview · No HP tag is issued. Text stays on this page; no upload or saving. The first run downloads the on-device Python runtime.</p>
  <form className="mt-4 min-w-0" onSubmit={run} aria-busy={busy}>
   <label htmlFor={uid+'-text'} className="block font-semibold">English text</label>
   <textarea ref={input} id={uid+'-text'} value={text} rows={4} maxLength={16000} spellCheck={false} autoComplete="off" autoCorrect="off" autoCapitalize="off" onChange={e=>{reset();setText(e.target.value);}} aria-invalid={inputError?true:undefined} aria-describedby={uid+'-limit'+(inputError?' '+uid+'-error':'')} className="mt-1 block w-full min-w-0 resize-y rounded-lg border border-input bg-surface p-3 text-base"/>
   <p id={uid+'-limit'} className="mt-1 text-xs tabular-nums text-muted">{Array.from(text).length.toLocaleString()} / {manifest.max_codepoints.toLocaleString()} characters · English only</p>
   {error&&<p id={uid+'-error'} role="alert" className="mt-2 text-pretty">{error}</p>}
   <div className="mt-3 flex flex-wrap gap-2"><button type="submit" disabled={busy} className={cn(button)}>{busy?'Finding details…':'Find details'}</button><button type="button" className={cn(button)} onClick={()=>{reset();setText('');}}>Clear details</button></div>
  </form><p role="status" className="mt-2 text-sm">{status}</p>
  {record&&<section ref={resultRef} tabIndex={-1} aria-label="Detail result" className="mt-4 rounded-lg border border-line bg-canvas p-3">
   <h4 className="font-semibold text-balance">{explanation.title}</h4><p className="mt-1 text-pretty">{explanation.body}</p>
   <dl className="mt-3 grid grid-cols-2 gap-2 tabular-nums"><div><dt className="text-xs text-muted">With a marker</dt><dd className="font-semibold">{explanation.marked}</dd></div><div><dt className="text-xs text-muted">Without a marker</dt><dd className="font-semibold">{explanation.unmarked}</dd></div></dl>
   <p className="mt-2 text-xs text-muted">A marker is a URL or numbered reference, not a checked source. Calendar dates and claims are not verified. Other formats may not be covered.{explanation.skipped>0&&` Skipped candidates: ${explanation.skipped}.`}</p>
   <details className="mt-3 border-t border-line pt-2" open={details} onToggle={e=>setDetails(e.currentTarget.open)}><summary className="flex min-h-11 cursor-pointer items-center font-semibold">Method and exact positions</summary>
    {details&&<><p className="mt-1 text-xs text-muted">Private fingerprints and NFC character positions can link text. Keep them on your device. Your pasted text is not included.</p><pre aria-label="Private detail evidence" tabIndex={0} className="mt-2 max-h-72 overflow-auto whitespace-pre-wrap break-all rounded-lg border border-line bg-surface p-3 text-xs">{JSON.stringify(record,null,2)}</pre></>}
   </details>
  </section>}
  <p className="mt-3 text-xs text-muted"><a href="/hp-device/notices.txt" className="inline-flex min-h-11 items-center underline underline-offset-4">Source notices</a><span aria-hidden="true"> · </span><a href="/device-licenses/source.txt" className="inline-flex min-h-11 items-center underline underline-offset-4">Runtime source notices</a></p>
 </section>;
}
