import React,{useEffect,useId,useRef,useState} from 'react';
import {nfDeviceClient,validNFInput,explainNF,manifest} from './nf-device-client.js';
const button='min-h-11 rounded-lg border border-line bg-surface px-4 py-3 text-sm font-medium disabled:opacity-50';
export function NFExplorer(){
 const uid=useId(),generation=useRef(0),client=useRef(null),first=useRef(null),second=useRef(null),resultRef=useRef(null);
 const [claim,setClaim]=useState(''),[passage,setPassage]=useState(''),[check,setCheck]=useState('literal'),[busy,setBusy]=useState(false),[status,setStatus]=useState(''),[error,setError]=useState(''),[invalid,setInvalid]=useState({claim:false,passage:false}),[record,setRecord]=useState(null),[details,setDetails]=useState(false);
 function reset(){generation.current++;client.current?.stop();client.current=null;setBusy(false);setStatus('');setError('');setInvalid({claim:false,passage:false});setRecord(null);setDetails(false);}
 useEffect(()=>()=>{generation.current++;client.current?.stop();},[]);
 useEffect(()=>{if(record)resultRef.current?.focus({preventScroll:true});},[record]);
 async function run(event){
  event.preventDefault();reset();const own=generation.current;
  const bad={claim:false,passage:false};try{validNFInput(claim);}catch{bad.claim=true;}try{validNFInput(passage);}catch{bad.passage=true;}
  if(bad.claim||bad.passage){setInvalid(bad);setError('Check the highlighted passage. Add text up to 2,000 characters; no result was issued.');(bad.claim?first:second).current?.focus();return;}
  setBusy(true);client.current=nfDeviceClient({onStatus:value=>{if(own===generation.current)setStatus(value);}});
  try{const value=await client.current.check(claim,passage,check);if(own!==generation.current)return;setRecord(value);setStatus('Comparison complete.');}
  catch{if(own===generation.current){setStatus('');setError(check==='cosine'?'Word overlap is unavailable for these inputs or this device. Try Exact words; it is a separate check. No overlap result was issued.':'This exact-word check could not finish. No result was issued. Try again or use a shorter passage.');}}
  finally{if(own===generation.current){client.current=null;setBusy(false);}}
 }
 const explanation=record?explainNF(record):null;
 return <section data-nf-explorer aria-labelledby={uid+'-heading'} className="mt-4 min-w-0 rounded-xl border border-line bg-surface p-4 text-sm leading-6">
  <h3 id={uid+'-heading'} className="text-base font-semibold">Compare with your reference</h3>
  <p className="mt-1">Choose a claim and the passage you want to compare it with.</p>
  <p className="mt-2 text-xs text-muted">NF method preview · No NF tag is issued. Both passages stay on this page, with no upload or saving. The first run downloads the on-device Python runtime.</p>
  <form className="mt-4 min-w-0" onSubmit={run} aria-busy={busy}>
   {[['claim','Claim',claim,setClaim],['passage','Reference passage',passage,setPassage]].map(([key,label,value,setter],i)=><div key={key} className={i?'mt-3':undefined}>
    <label htmlFor={uid+'-'+key} className="block font-semibold">{label}</label>
    <textarea ref={i?second:first} id={uid+'-'+key} value={value} rows={3} spellCheck={false} autoComplete="off" autoCorrect="off" autoCapitalize="off" onChange={e=>{reset();setter(e.target.value);}} aria-invalid={invalid[key]?true:undefined} aria-describedby={uid+'-'+key+'-limit'+(invalid[key]?' '+uid+'-error':'')} className="mt-1 block w-full min-w-0 resize-y rounded-lg border border-input bg-surface p-3 text-base"/>
    <p id={uid+'-'+key+'-limit'} className="mt-1 text-xs tabular-nums text-muted">{Array.from(value).length.toLocaleString()} / {manifest.max_codepoints.toLocaleString()} characters</p>
   </div>)}
   <fieldset className="mt-3"><legend className="font-semibold">Choose one check</legend><div className="flex flex-wrap gap-3">
    {[['literal','Exact words'],['cosine','Word overlap']].map(([value,label])=><label key={value} className="inline-flex min-h-11 items-center gap-2"><input type="radio" name={uid+'-check'} value={value} checked={check===value} onChange={()=>{reset();setCheck(value);}}/>{label}</label>)}
   </div><p className="text-xs text-muted">Exact words is case-sensitive and supports Unicode. Word overlap uses ASCII letters and numbers, with one claim per line.</p></fieldset>
   {error&&<p id={uid+'-error'} role="alert" className="mt-2">{error}</p>}
   <div className="mt-3 flex flex-wrap gap-2"><button type="submit" disabled={busy} className={button}>{busy?'Comparing…':'Compare passages'}</button>{busy&&<button type="button" className={button} onClick={()=>{reset();setStatus('Cancelled. No result was issued.');}}>Cancel comparison</button>}<button type="button" className={button} onClick={()=>{reset();setClaim('');setPassage('');}}>Clear passages</button></div>
  </form><p role="status" className="mt-2">{status}</p>
  {record&&<section ref={resultRef} tabIndex={-1} aria-label="Reference comparison result" className="mt-4 rounded-lg border border-line bg-canvas p-3">
   <h4 className="font-semibold">{explanation.title}</h4><p className="mt-1">{explanation.body}</p>
   <p className="mt-2 text-xs text-muted">Only the passages you selected were compared. References can be wrong or outdated. Other sources and claims were not checked.{explanation.count===10&&' The first 10 matches are shown; more may exist.'}</p>
   <details className="mt-3 border-t border-line pt-2" open={details} onToggle={e=>setDetails(e.currentTarget.open)}><summary className="flex min-h-11 cursor-pointer items-center font-semibold">Method and exact positions</summary>{details&&<><p className="mt-1 text-xs text-muted">These private details include matching words, fingerprints and character positions. Share deliberately.</p><pre aria-label="Private reference evidence" tabIndex={0} className="mt-2 max-h-72 overflow-auto whitespace-pre-wrap break-all rounded-lg border border-line bg-surface p-3 text-xs">{JSON.stringify(record,null,2)}</pre></>}</details>
  </section>}
  <p className="mt-3 text-xs text-muted"><a href="/nf-device/notices.txt" className="inline-flex min-h-11 items-center underline underline-offset-4">Source notices</a><span aria-hidden="true"> · </span><a href="/device-licenses/source.txt" className="inline-flex min-h-11 items-center underline underline-offset-4">Runtime source notices</a><span aria-hidden="true"> · </span><a href="https://github.com/knwvmbrr/aitrust-id/blob/main/docs/nf-device-reference.md" className="inline-flex min-h-11 items-center underline underline-offset-4">Comparison guide</a></p>
 </section>;
}
