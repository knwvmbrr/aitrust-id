import React,{useState,useEffect,useRef,useId} from 'react';
import * as Dialog from '@radix-ui/react-dialog';
import {deviceChecker,manifest} from './device-client.js';
const button='min-h-11 rounded-lg border border-line px-4 py-3 text-sm font-medium disabled:opacity-50';
function download(name,data){const url=URL.createObjectURL(new Blob([JSON.stringify(data,null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}

function Checker(){
 const uid=useId(),client=useRef(null),generation=useRef(0);
 const [text,setText]=useState(''),[busy,setBusy]=useState(false),[status,setStatus]=useState(''),[record,setRecord]=useState(null);
 useEffect(()=>()=>{generation.current++;client.current?.stop();},[]);
 function clear(value=''){generation.current++;client.current?.stop();client.current=null;setText(value);setRecord(null);setBusy(false);setStatus('');}
 async function check(event){
  event.preventDefault();const own=++generation.current;setRecord(null);
  if(!text.trim()||Array.from(text).length>manifest.max_codepoints){setStatus('Paste an answer, up to 20,000 characters.');return;}
  setBusy(true);
  try{client.current??=deviceChecker(message=>{if(own===generation.current)setStatus(message);});const value=await client.current.check(text);if(own!==generation.current)return;setRecord({...value,record_id:crypto.randomUUID()});setStatus('Check complete.');}
  catch{if(own===generation.current){client.current?.stop();client.current=null;setStatus('UNAVAILABLE — the check could not finish. Try again with a shorter answer or a supported browser.');}}
  finally{if(own===generation.current)setBusy(false);}
 }
 return <><p className="text-sm leading-6">Copy an answer from any AI app. Paste. Check.</p>
 <p className="mt-2 text-sm leading-6 text-muted">Checks run on your device. No text is uploaded or saved. Commands are never executed; personal information is not redacted.</p>
 <form className="mt-4" onSubmit={check}><label className="block text-sm font-semibold" htmlFor={uid}>AI answer</label><textarea id={uid} className="mt-2 block w-full resize-y rounded-lg border border-input bg-surface p-3 text-base" rows={5} value={text} maxLength={40000} spellCheck={false} autoComplete="off" autoCorrect="off" autoCapitalize="off" onChange={e=>clear(e.target.value)} aria-describedby={uid+'-limit'}/><p id={uid+'-limit'} className="mt-1 text-xs text-muted">{Array.from(text).length.toLocaleString()} / 20,000 characters · Development preview</p>
 <div className="mt-3 flex flex-wrap gap-2"><button className={button} type="submit" disabled={busy}>{busy?'Checking…':'Check answer'}</button><button className={button} type="button" onClick={()=>clear()}>Clear</button></div></form>
 <p role="status" className="mt-3 text-sm leading-6">{status}</p>
 {record&&<section aria-label="Check result" className="mt-3 rounded-xl border border-line p-4"><p className="text-base font-semibold">{record.state==='FINDING'?'PS · Command-risk pattern found':'No supported pattern found'}</p><p className="mt-1 text-sm leading-6">{record.state==='FINDING'?'Read and understand the command before acting. This does not establish a scam or malicious intent.':'This is not a safety clearance. PS recognizes a bounded set of command patterns.'}</p><p className="mt-2 text-xs text-muted">Development preview · Method {record.models[0].revision} · {record.candidates.reduce((n,c)=>n+c.signals.length,0)} supported signals</p><button className={button+' mt-3'} onClick={()=>download('ai-trust-id-ps-record.json',record)}>Download record</button><p className="mt-2 text-xs text-muted">Metadata only, not a training label. The subject hash can link matching text; share carefully.</p></section>}
 <Offline/>
 </>;
}

function Offline(){
 const [status,setStatus]=useState(''),[busy,setBusy]=useState(false);
 async function remove(){setBusy(true);try{
  if('serviceWorker' in navigator)for(const registration of await navigator.serviceWorker.getRegistrations()){
   const worker=registration.active||registration.waiting||registration.installing;
   if(worker&&new URL(worker.scriptURL).pathname==='/offline-worker.js')await registration.unregister();
  }
  if('caches' in window)for(const name of await caches.keys())if(name.startsWith('aitrust-id-offline-'))await caches.delete(name);
  setStatus('Offline files removed. Close and reopen the app to finish removing offline mode.');
 }catch{setStatus('Removal did not finish. Use your browser’s site-data controls.');}finally{setBusy(false);}}
 async function save(){setBusy(true);setStatus('Saving public checker files. Keep this page open.');try{
  if(!('serviceWorker' in navigator))throw Error('Unsupported');
  const registration=await navigator.serviceWorker.register('/offline-worker.js',{scope:'/'});
  const target=registration.installing||registration.waiting||registration.active;
  if(target&&target.state!=='activated')await new Promise((resolve,reject)=>{const timeout=setTimeout(()=>{target.removeEventListener('statechange',change);reject(Error('Timeout'));},45000);function finish(error){clearTimeout(timeout);target.removeEventListener('statechange',change);error?reject(error):resolve();}function change(){if(target.state==='activated'||(target.state==='installed'&&registration.active))finish();else if(target.state==='redundant')finish(Error('Cache failed'));}target.addEventListener('statechange',change);change();});
  if(registration.waiting||(target?.state==='installed'&&registration.active)){setStatus('Updated offline files are ready. Close all AI Trust ID tabs and reopen the app to use them.');return;}
  await navigator.serviceWorker.ready;setStatus('Saved for offline use. Your browser may remove cached files when storage is low. Save again online to check for updates, then close all AI Trust ID tabs and reopen.');
 }catch{setStatus('Offline saving did not finish. Stay online and try again.');}finally{setBusy(false);}}
 return <section className="mt-5 border-t border-line pt-4"><h3 className="text-sm font-semibold">Keep it on your phone</h3><p className="mt-1 text-sm leading-6">iPhone: Safari → Share → Add to Home Screen. Android: browser menu → Install app or Add to Home screen.</p><div className="mt-3 flex flex-wrap gap-2"><button className={button} disabled={busy} onClick={save}>{busy?'Saving…':'Save for offline use'}</button><button className={button} disabled={busy} onClick={remove}>Remove offline files</button></div><p className="mt-2 text-xs text-muted">About 15 MB of public app files. Pasted answers and review files are never cached. Requires a browser with WebAssembly, such as Safari 16.4+ or Chrome 112+.</p><p role="status" className="mt-2 text-sm leading-6">{status}</p></section>;
}

const headerKeys=['format','reviewer_slot','dataset_sha256','method_sha256','gates_sha256','protocol_sha256','items'];
export function validateReview(value){
 if(!value||Object.keys(value).sort().join()!=headerKeys.sort().join()||value.format!=='ai-trust-id-blind-ps-labels/v1'||![1,2].includes(value.reviewer_slot))throw Error('Invalid packet');
 for(const key of headerKeys.filter(k=>k.endsWith('sha256')))if(!/^[a-f0-9]{64}$/.test(value[key]))throw Error('Invalid hash');
 if(!Array.isArray(value.items)||!value.items.length||value.items.length>1000)throw Error('Invalid items');
 const ids=new Set();for(const row of value.items){
  if(!row||Object.keys(row).sort().join()!==['id','text','category','source','label','reason'].sort().join())throw Error('Unexpected fields');
  for(const key of ['id','text','category','source'])if(typeof row[key]!=='string'||!row[key].trim())throw Error('Invalid text');
  if(row.id.length>100||Array.from(row.text).length>200000||ids.has(row.id)||![null,'positive','negative','ambiguous'].includes(row.label)||typeof row.reason!=='string'||row.reason.length>2000)throw Error('Invalid review');
  ids.add(row.id);
 }return value;
}
function Review(){
 const uid=useId(),[packet,setPacket]=useState(null),[index,setIndex]=useState(0),[status,setStatus]=useState(''),loadId=useRef(0);
 useEffect(()=>()=>{loadId.current++;},[]);
 async function load(event){const own=++loadId.current;const file=event.target.files?.[0];event.target.value='';setPacket(null);setIndex(0);if(!file)return;try{if(file.size>10000000)throw Error('Too large');const value=validateReview(JSON.parse(await file.text()));if(own===loadId.current){setPacket(value);setStatus('Review file opened on this device. No upload.');}}catch{if(own===loadId.current)setStatus('Choose a valid reviewer JSON file generated by AI Trust ID, up to 10 MB.');}}
 const row=packet?.items[index];function update(key,value){setPacket(p=>({...p,items:p.items.map((r,i)=>i===index?{...r,[key]:value}:r)}));}
 const completed=packet?.items.filter(r=>r.label&&r.reason.trim()).length||0;
 return <><p className="text-sm leading-6">Open the reviewer JSON file your coordinator sends you. Review each example yourself, without running PS or discussing answers with the other reviewer. This form shows no predictions.</p><p className="mt-2 text-sm leading-6">Positive: the text recommends or presents a supported risky command for use. Negative: no such supported pattern, or a clear warning/literal description. Ambiguous: you cannot decide. <a className="underline" href="/reference/independent-review.md" target="_blank" rel="noreferrer">Read the full labeling rules</a>.</p>
 <label className="mt-4 block text-sm font-semibold" htmlFor={uid+'-file'}>Reviewer file<input id={uid+'-file'} type="file" accept=".json,application/json" onChange={load} className="mt-2 block w-full min-h-11 text-sm"/></label>
 {row&&<><p className="mt-4 text-sm">Example {index+1} of {packet.items.length} · {completed} complete</p><pre className="my-3 max-h-72 overflow-auto whitespace-pre-wrap break-words rounded-lg border border-line bg-canvas p-3 text-sm font-sans" aria-label="Example text">{row.text}</pre><p className="text-xs text-muted">{row.category} · {row.source}</p>
 <label className="mt-3 block text-sm" htmlFor={uid+'-label'}>Your judgment</label><select id={uid+'-label'} className="mt-1 block w-full min-h-11 rounded-lg border border-input bg-surface px-3" value={row.label||''} onChange={e=>update('label',e.target.value||null)}><option value="">Choose a label</option><option value="positive">Positive</option><option value="negative">Negative</option><option value="ambiguous">Ambiguous</option></select>
 <label className="mt-3 block text-sm" htmlFor={uid+'-reason'}>Why?<textarea id={uid+'-reason'} rows={3} maxLength={2000} className="mt-1 block w-full rounded-lg border border-input bg-surface p-3 text-base" value={row.reason} onChange={e=>update('reason',e.target.value)} /></label>
 <div className="mt-3 flex flex-wrap gap-2"><button className={button} disabled={index===0} onClick={()=>setIndex(i=>i-1)}>Previous</button><button className={button} disabled={index===packet.items.length-1} onClick={()=>setIndex(i=>i+1)}>Next</button><button className={button} onClick={()=>{download('reviewer-'+packet.reviewer_slot+'.json',packet);setStatus(completed===packet.items.length?'Labels downloaded. Return this file privately to your coordinator.':'Progress downloaded. Reopen this file to resume. Incomplete labels cannot pass comparison.');}}>Download labels</button></div><button className={button+' mt-3'} onClick={()=>{loadId.current++;setPacket(null);setStatus('Review cleared from this page. Downloaded files remain on your device.');}}>Clear review</button></>}
 <p role="status" className="mt-3 text-sm leading-6">{status}</p><p className="mt-3 text-xs text-muted">This page does not save, submit or certify labels. Download to preserve progress. The coordinator verifies the frozen file, completeness and disagreements before any accuracy evaluation.</p></>;
}

export function HandheldDialogs({Shell}){return <div className="my-3 flex flex-wrap gap-2"><Dialog.Root><Dialog.Trigger className={button}>Check on this device</Dialog.Trigger><Shell title="Check with PS" description="Free · On-device development preview"><Checker/></Shell></Dialog.Root><Dialog.Root><Dialog.Trigger className={button}>Review test examples</Dialog.Trigger><Shell title="Review PS examples" description="Independent review · No predictions shown"><Review/></Shell></Dialog.Root></div>;}
