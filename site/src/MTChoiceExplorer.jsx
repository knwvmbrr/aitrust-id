import React,{useEffect,useId,useRef,useState} from 'react';
import {clsx} from 'clsx';
import {twMerge} from 'tailwind-merge';
const cn=(...values)=>twMerge(clsx(values));
import {loadManifest,choiceClient} from './mt-choice-client.mjs';
import {explainChoice} from './mt-choice-result.mjs';

const blank={subject:'',first:'',second:'',reference:'',whole_frame:false};
const examples={additive:'Not only tea but also coffee.',either:'Either tea or coffee.',only:'Only tea or coffee.',neither:'Neither tea nor coffee.',between:'Between tea and coffee.'};
const labels={subject:'English passage',first:'First exact item',second:'Second exact item',reference:'Additional passage you nominate'};
function issue(request){
 for(const name of ['subject','first','second','reference']){
  const text=request[name],small=name==='first'||name==='second',characters=small?256:2000,bytes=small?1024:8000;
  if(!text.trim())return {name,message:'Fill in this field before checking.'};
  if(Array.from(text).length>characters||new TextEncoder().encode(text).length>bytes)return {name,message:`Keep this field within ${characters.toLocaleString('en-US')} characters and ${bytes.toLocaleString('en-US')} UTF-8 bytes. Your whole input is still here.`};
 }
 if(!request.whole_frame)return {name:'whole_frame',message:'Confirm the passage and context you are choosing.'};
 return null;
}
export function MTChoiceExplorer(){
 const prefix=useId(),client=useRef(null),sequence=useRef(0),refs=useRef({});
 const [form,setForm]=useState({...blank}),[example,setExample]=useState(''),[ready,setReady]=useState(false),[busy,setBusy]=useState(false),[record,setRecord]=useState(null),[details,setDetails]=useState(false),[invalid,setInvalid]=useState(null),[error,setError]=useState(false),[manifestError,setManifestError]=useState(false),[status,setStatus]=useState('Opening this optional preview…');
 const reset=(message=ready?'Ready. Check is always your choice.':manifestError?'Unavailable: close and reopen this preview to retry.':'Opening this optional preview…')=>{sequence.current++;client.current?.stop();setBusy(false);setRecord(null);setDetails(false);setInvalid(null);setError(false);setStatus(message);};
 useEffect(()=>{
  let alive=true;const controller=new AbortController();
  loadManifest({signal:controller.signal}).then(manifest=>{
   if(!alive)return;
   client.current=choiceClient(manifest,{onStatus:message=>{if(alive)setStatus(message);}});
   setReady(true);setStatus('Ready. Nothing runs until you choose Check.');
  }).catch(()=>{if(alive){setManifestError(true);setStatus('Unavailable: this optional preview could not load. Close and reopen it to retry; other wording checks remain separate.');}});
  const leave=()=>{sequence.current++;client.current?.stop();if(alive){setForm({...blank});setRecord(null);setDetails(false);setBusy(false);setStatus('Stopped. Clear or check again when ready.');}};
  window.addEventListener('pagehide',leave);
  return()=>{alive=false;sequence.current++;controller.abort();client.current?.stop();client.current=null;window.removeEventListener('pagehide',leave);};
 },[]);
 function edit(name,value){reset();setForm(old=>({...old,[name]:value}));setExample('');}
 function choose(value){reset();setExample(value);if(examples[value])setForm({subject:examples[value],first:'tea',second:'coffee',reference:'Water is also listed.',whole_frame:false});}
 async function check(event){
  event.preventDefault();if(!ready||busy||!client.current)return;
  reset();const request={...form},bad=issue(request);
  if(bad){setInvalid(bad);setStatus('Input needs attention. No worker started.');refs.current[bad.name]?.focus();return;}
  const token=++sequence.current;setBusy(true);
  try{
   const value=await client.current.check(request);if(token!==sequence.current)return;
   // explainChoice accepts only the closed, request-bound validated record.
   explainChoice(value);setRecord(value);setStatus('Finished on this device. Exact evidence stays closed until you choose to view it.');
  }catch{
   if(token!==sequence.current)return;
   setRecord(null);setDetails(false);setError(true);setStatus('Unavailable: no valid observation completed. Check the declaration, unique ordered items and limits, or clear and try again.');
  }finally{if(token===sequence.current)setBusy(false);}
 }
 const brief=record?explainChoice(record):null;
 const field=(name,small=false)=><div className={cn(small&&'min-w-0')} key={name}>
  <label className="mb-1 block text-sm font-semibold" htmlFor={prefix+'-'+name}>{labels[name]}</label>
  {small?<input ref={e=>{refs.current[name]=e;}} id={prefix+'-'+name} className="min-h-11 w-full rounded-lg border border-input bg-surface px-3 py-2 text-sm" type="text" autoComplete="off" spellCheck={false} value={form[name]} onChange={e=>edit(name,e.target.value)} aria-invalid={invalid?.name===name} aria-describedby={prefix+'-limits'+(invalid?.name===name?' '+prefix+'-error':'')}/>:<textarea ref={e=>{refs.current[name]=e;}} id={prefix+'-'+name} className="w-full resize-y rounded-lg border border-input bg-surface px-3 py-2 text-sm leading-6" rows={name==='subject'?4:3} spellCheck={false} value={form[name]} onChange={e=>edit(name,e.target.value)} aria-invalid={invalid?.name===name} aria-describedby={prefix+'-limits'+(invalid?.name===name?' '+prefix+'-error':'')}/>}
 </div>;
 return <section data-mt-choice-explorer className="mt-3 rounded-xl border border-line bg-surface p-4 text-sm leading-6" aria-labelledby={prefix+'-title'}>
  <h3 id={prefix+'-title'} className="text-balance font-semibold">Look at a pair of items</h3>
  <p className="text-pretty mt-1">Choose the wording and context you want to inspect. This literal preview does not decide intent or issue an MT tag.</p>
  <form className="mt-3 space-y-3" onSubmit={check} noValidate>
   <label className="block font-semibold" htmlFor={prefix+'-example'}>Start with an invented example</label>
   <select id={prefix+'-example'} className="min-h-11 w-full rounded-lg border border-input bg-surface px-3 py-2" value={example} onChange={e=>choose(e.target.value)}><option value="">Choose an example</option><option value="additive">Not only … but also …</option><option value="either">Either … or …</option><option value="only">Only … or …</option><option value="neither">Neither … nor …</option><option value="between">Between … and …</option></select>
   {field('subject')}
   <div className="grid min-w-0 gap-3 sm:grid-cols-2">{field('first',true)}{field('second',true)}</div>
   {field('reference')}
   <p id={prefix+'-limits'} className="text-xs text-muted">Passage and context: up to 2,000 characters/8,000 UTF-8 bytes each. Items: 256 characters/1,024 bytes each, appearing once and in order. Oversized input stays visible and is refused. Context is nominated by you; it is not a verified alternative.</p>
   <label className="flex min-h-11 items-start gap-3 py-2" htmlFor={prefix+'-whole'}><input ref={e=>{refs.current.whole_frame=e;}} className="mt-1 size-5 shrink-0" id={prefix+'-whole'} type="checkbox" checked={form.whole_frame} onChange={e=>edit('whole_frame',e.target.checked)} aria-invalid={invalid?.name==='whole_frame'} aria-describedby={invalid?.name==='whole_frame'?prefix+'-error':undefined}/><span>I choose this whole passage as the frame and this extra passage as context.</span></label>
   {invalid&&<p id={prefix+'-error'} className="text-sm" role="alert">{invalid.message}</p>}
   <div className="flex flex-wrap gap-2"><button type="submit" disabled={!ready||busy} className="min-h-11 rounded-lg bg-ink px-3 py-2 font-semibold text-surface disabled:opacity-50">Check selected wording</button>{busy&&<button type="button" className="min-h-11 rounded-lg border border-input px-3 py-2" onClick={()=>reset('Cancelled. No valid observation completed.')}>Cancel selected check</button>}<button type="button" className="min-h-11 rounded-lg border border-input px-3 py-2" onClick={()=>{reset('Cleared. No previous result is retained.');setForm({...blank});setExample('');refs.current.subject?.focus();}}>Clear selected wording</button></div>
  </form>
  <p className="text-pretty mt-3 text-sm" role="status" aria-live="polite">{status}</p>
  {(error||manifestError)&&<p data-mt-choice-unavailable className="mt-2 text-sm">This check is Unavailable, not safe or zero findings. Other methods remain separate.</p>}
  {record&&<div data-mt-choice-result className="mt-3 rounded-lg border border-line bg-surface p-3"><h4 className="text-balance font-semibold">{brief.title}</h4><p className="text-pretty mt-1">{brief.message}</p><p className="text-pretty mt-1 text-xs tabular-nums text-muted">Additive frames: {record.counts.additive_frames}. Other paired frames: {record.counts.other_paired_frames}. This is wording evidence, not a verdict or safety clearance.</p><p className="text-pretty mt-2 text-xs text-muted" id={prefix+'-details-warning'}>Exact records contain linkable hashes and positions. Open them only when you choose; they contain no full input words.</p><button type="button" className="mt-1 min-h-11 rounded-lg border border-input px-3 py-2" aria-describedby={prefix+'-details-warning'} aria-expanded={details} onClick={()=>setDetails(v=>!v)}>{details?'Hide exact selected record':'Show exact selected record'}</button>{details&&<pre data-mt-choice-details aria-label="Private selected wording evidence" tabIndex={0} className="mt-2 max-h-80 overflow-auto whitespace-pre-wrap break-words rounded-lg border border-line bg-surface p-3 text-xs">{JSON.stringify(record,null,2)}</pre>}</div>}
  <p className="text-pretty mt-3 text-xs text-muted">Inputs stay on this device. Public method/runtime files must be available; initial use can need a download. No account or input storage. <a className="underline underline-offset-4" href="/reference/mt-choice-device.md">Method and privacy guide</a> · <a className="underline underline-offset-4" href="/device/mt-choice/project-notices.txt">Source notices</a></p>
 </section>;
}
