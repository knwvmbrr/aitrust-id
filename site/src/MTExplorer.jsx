import React,{useEffect,useId,useRef,useState} from 'react';
import {clsx} from 'clsx';
import {twMerge} from 'tailwind-merge';
import {mtDeviceClient,manifest,validMTInput,explainMTSelection} from './mt-device-client.js';
const cn=(...values)=>twMerge(clsx(values));
const button='min-h-11 rounded-lg border border-line bg-surface px-4 py-3 text-sm font-medium disabled:opacity-50';
export function MTExplorer(){
 const uid=useId(),generation=useRef(0),client=useRef(null),input=useRef(null),selection=useRef(null),resultRef=useRef(null);
 const [kind,setKind]=useState(''),[text,setText]=useState(''),[busy,setBusy]=useState(false),[status,setStatus]=useState(''),[error,setError]=useState(''),[errorTarget,setErrorTarget]=useState(''),[record,setRecord]=useState(null),[details,setDetails]=useState(false),[explanation,setExplanation]=useState(null);
 function reset(){generation.current++;client.current?.stop();client.current=null;setRecord(null);setExplanation(null);setBusy(false);setStatus('');setError('');setErrorTarget('');setDetails(false);}
 useEffect(()=>()=>{generation.current++;client.current?.stop();},[]);
 useEffect(()=>{if(record)resultRef.current?.focus({preventScroll:true});},[record]);
 async function run(event){
  event.preventDefault();reset();const own=generation.current;
  try{validMTInput(kind,text);}catch{setErrorTarget(kind?'input':'kind');setError(kind?'Paste English text, up to 8,000 characters, without invalid control characters.':'Choose a wording check first.');if(kind)input.current?.focus();else selection.current?.focus();return;}
  setBusy(true);client.current=mtDeviceClient({onStatus:message=>{if(own===generation.current)setStatus(message);}});
  try{const value=await client.current.check(kind,text);if(own!==generation.current)return;const brief=await explainMTSelection(value,kind);if(own!==generation.current)return;setExplanation(brief);setRecord(value);setStatus('Wording check complete.');}
  catch{if(own===generation.current){setStatus('');setErrorTarget('result');setError('This check couldn’t finish. Your text has not been rated. Try the other check, or try again.');}}
  finally{if(own===generation.current){client.current=null;setBusy(false);}}
 }
 return <section data-mt-explorer aria-labelledby={uid+'-heading'} className="mt-4 min-w-0 rounded-xl border border-line bg-surface p-4 text-sm leading-6">
  <h3 id={uid+'-heading'} className="text-base font-semibold text-balance">Explore the wording</h3>
  <p className="mt-1 text-pretty">Spot supported English phrases. You decide what they mean.</p>
  <p className="mt-2 text-xs text-muted">MT method preview · No MT tag is issued. Text stays on this page; no upload or saving. The first run downloads the on-device Python runtime.</p>
  <form noValidate className="mt-4 min-w-0" onSubmit={run} aria-busy={busy}>
   <label className="block font-semibold" htmlFor={uid+'-kind'}>Look for</label>
   <div className="relative mt-1"><select required ref={selection} id={uid+'-kind'} aria-invalid={errorTarget==='kind'?true:undefined} value={kind} className="block min-h-11 w-full min-w-0 appearance-none rounded-lg border border-input bg-surface py-2 pl-3 pr-10 text-base" onChange={e=>{reset();setKind(e.target.value);}} aria-describedby={uid+'-method'+(errorTarget==='kind'?' '+uid+'-error':'')}>
    <option value="">Choose a check</option><option value="urgency">Instructions + time words</option><option value="authority">Authority wording</option><option value="authority-curly">Include curly quotes · preview</option>
   </select><svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="pointer-events-none absolute right-3 top-1/2 size-4 -translate-y-1/2"><path d="m6 9 6 6 6-6"/></svg></div>
   <p id={uid+'-method'} className="mt-2 text-xs text-muted">{kind==='authority-curly'?'Includes straight or curly double quotes, one style per passage. Quote placement is not endorsement. Single quotes are ordinary text.':kind==='authority'?'Looks for expertise or consensus phrases. Uses straight double quotes only; other quote styles are not supported yet. Sources are not verified.':kind==='urgency'?'Looks for a supported instruction and time phrase in the same sentence unit. Quotations and intent are not interpreted.':'These are separate phrase checks, not votes about a person or message.'}</p>
   <label htmlFor={uid+'-text'} className="mt-3 block font-semibold">English text</label>
   <textarea required ref={input} id={uid+'-text'} value={text} rows={4} maxLength={16000} spellCheck={false} autoComplete="off" autoCorrect="off" autoCapitalize="off" onChange={e=>{reset();setText(e.target.value);}} aria-invalid={errorTarget==='input'?true:undefined} aria-describedby={uid+'-limit'+(errorTarget==='input'?' '+uid+'-error':'')} className="mt-1 block w-full min-w-0 resize-y rounded-lg border border-input bg-surface p-3 text-base"/>
   <p id={uid+'-limit'} className="mt-1 text-xs tabular-nums text-muted">{Array.from(text).length.toLocaleString()} / {manifest.max_codepoints.toLocaleString()} characters · English only</p>
   {error&&<p id={uid+'-error'} role="alert" className="mt-2 text-pretty">{error}</p>}
   <div className="mt-3 flex flex-wrap gap-2"><button type="submit" disabled={busy} className={cn(button)}>{busy?'Checking wording…':'Explore wording'}</button><button type="button" className={cn(button)} onClick={()=>{reset();setText('');}}>Clear wording</button></div>
  </form>
  <p role="status" className="mt-2 text-sm">{status}</p>
  {record&&explanation&&<section ref={resultRef} tabIndex={-1} aria-label="Wording result" className="mt-4 rounded-lg border border-line bg-canvas p-3">
   <h4 className="font-semibold text-balance">{explanation.title}</h4><p className="mt-1 text-pretty">{explanation.body}</p>
   <p className="mt-2 text-xs text-muted">A phrase observation, not a manipulation or intent verdict. No confidence score or independent accuracy claim.</p>
   <details className="mt-3 border-t border-line pt-2" open={details} onToggle={e=>setDetails(e.currentTarget.open)}><summary className="flex min-h-11 cursor-pointer items-center font-semibold">Method and exact positions</summary>
    {details&&<><p className="mt-1 text-xs text-muted">Private fingerprints and NFC character positions can link text. Keep them on your device. Your pasted text is not included.</p><pre aria-label="Private wording evidence" tabIndex={0} className="mt-2 max-h-72 overflow-auto whitespace-pre-wrap break-all rounded-lg border border-line bg-surface p-3 text-xs">{JSON.stringify(record,null,2)}</pre></>}
   </details>
  </section>}
  <p className="mt-3 text-xs text-muted">{kind==='authority-curly'&&<><a href="/mt-mobile-device/notices.txt" className="inline-flex min-h-11 items-center underline underline-offset-4">Curly quote source notices</a><span aria-hidden="true"> · </span><a href="/reference/mt-mobile-quotation.md" className="inline-flex min-h-11 items-center underline underline-offset-4">Quote preview guide</a><span aria-hidden="true"> · </span></>}<a href="/mt-device/notices.txt" className="inline-flex min-h-11 items-center underline underline-offset-4">Source notices</a><span aria-hidden="true"> · </span><a href="/device-licenses/source.txt" className="inline-flex min-h-11 items-center underline underline-offset-4">Runtime source notices</a></p>
 </section>;
}
