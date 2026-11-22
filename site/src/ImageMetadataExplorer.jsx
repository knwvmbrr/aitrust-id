import React,{useEffect,useId,useRef,useState} from 'react';
import {clsx} from 'clsx';
import {twMerge} from 'tailwind-merge';
import {imageClient,loadImageManifest} from './image-metadata-client.mjs';
import {explainImage} from './image-metadata-result.mjs';
const cn=(...parts)=>twMerge(clsx(parts));
const labels={plain_text:'Plain text sections',compressed_text:'Compressed text sections',international_text:'International text sections',EXIF_section:'Exif-shaped sections',ICC_section:'Color-profile sections',C2PA_section:'Content Credential-shaped sections',time_section:'Time sections',other_ancillary_sections:'Other ancillary sections',Exif_labelled:'Exif-labelled sections',XMP_labelled:'XMP-labelled sections',ICC_labelled:'ICC-labelled sections',JFIF_labelled:'JFIF-labelled sections',APP11_opaque:'Opaque APP11 sections',comment:'Comment sections',other_APP:'Other application sections'};
export function ImageMetadataExplorer(){
 const id=useId(),file=useRef(null),input=useRef(null),client=useRef(null),generation=useRef(0);
 const [selected,setSelected]=useState(false),[ready,setReady]=useState(false),[busy,setBusy]=useState(false),[record,setRecord]=useState(null),[details,setDetails]=useState(false),[error,setError]=useState(''),[inputBad,setInputBad]=useState(false),[status,setStatus]=useState('Opening the optional reader…');
 function reset(message='Choose a file, then inspect when ready.'){
  generation.current++;client.current?.stop();setBusy(false);setRecord(null);setDetails(false);setError('');setInputBad(false);setStatus(message);
 }
 function clear(){reset('Cleared. No previous result is retained.');file.current=null;setSelected(false);if(input.current)input.current.value='';input.current?.focus();}
 useEffect(()=>{
  let alive=true;const controller=new AbortController();
  loadImageManifest({signal:controller.signal}).then(()=>{if(alive){client.current=imageClient({onStatus:message=>{if(alive)setStatus(message);}});setReady(true);setStatus('Ready. Nothing runs until you choose Inspect.');}}).catch(()=>{if(alive){setError('The optional reader is unavailable. Close and reopen it to retry.');setStatus('No image check completed.');}});
  const leave=()=>{generation.current++;client.current?.stop();file.current=null;if(input.current)input.current.value='';if(alive){setSelected(false);setRecord(null);setDetails(false);setBusy(false);setStatus('Stopped. Choose the file again when ready.');}};
  window.addEventListener('pagehide',leave);
  return()=>{alive=false;generation.current++;controller.abort();client.current?.stop();client.current=null;file.current=null;window.removeEventListener('pagehide',leave);};
 },[]);
 async function inspect(event){
  event.preventDefault();if(!ready||busy||!client.current)return;reset();
  if(!file.current){setInputBad(true);setError('Choose a local PNG or JPEG first.');input.current?.focus();return;}
  const token=++generation.current;setBusy(true);
  try{const value=await client.current.check(file.current);if(token!==generation.current)return;explainImage(value);setRecord(value);setStatus('Finished on this device. Exact evidence stays closed until you choose it.');}
  catch(failure){if(token!==generation.current)return;setRecord(null);setDetails(false);setInputBad(['input_limit','unsupported_format'].includes(failure.code));setError(failure.code==='input_limit'?'Choose a nonempty PNG or JPEG up to 10 MiB. Your selected file is unchanged.':failure.code==='unsupported_format'?'Unsupported format. Choose a PNG or JPEG; the file extension is not used as proof.':'Unavailable: no valid image observation completed. Other checks remain separate.');input.current?.focus();setStatus('No successful result is being reported.');}
  finally{if(token===generation.current)setBusy(false);}
 }
 const brief=record?explainImage(record):null;
 return <section data-image-metadata-explorer className="rounded-xl border border-line bg-surface p-4 text-sm leading-6" aria-labelledby={id+'-title'}>
  <h3 id={id+'-title'} className="text-balance font-semibold">Read image details privately</h3>
  <p className="text-pretty mt-1">Choose a PNG or JPEG to inspect its supported container details. Your image stays on this device. This does not detect AI origin.</p>
  <form onSubmit={inspect} className="mt-3 space-y-3" noValidate>
   <label className="block font-semibold" htmlFor={id+'-file'}>Choose a local image</label>
   <input ref={input} id={id+'-file'} className={cn('min-h-11 w-full min-w-0 rounded-lg border border-input bg-surface px-3 py-2 text-sm')} type="file" accept="image/png,image/jpeg" aria-describedby={id+'-limits'+(inputBad?' '+id+'-error':'')} aria-invalid={inputBad} onChange={event=>{reset();file.current=event.target.files?.[0]||null;setSelected(Boolean(file.current));}}/>
   <p id={id+'-limits'} className="text-pretty text-xs text-muted">Up to 10 MiB and 4 million header pixels. Selected noninterlaced 8-bit PNG and baseline single-scan JPEG profiles only. Other variants may be Unsupported. No image or metadata value is uploaded, stored or scrubbed.</p>
   <div className="flex flex-wrap gap-2"><button type="submit" className="min-h-11 rounded-lg bg-ink px-3 py-2 font-semibold text-surface disabled:opacity-50" disabled={!ready||busy}>Inspect image</button>{busy&&<button type="button" className="min-h-11 rounded-lg border border-input px-3 py-2" onClick={()=>reset('Cancelled. No successful result is retained.')}>Cancel image check</button>}<button type="button" className="min-h-11 rounded-lg border border-input px-3 py-2" onClick={clear}>Clear image</button></div>
  </form>
  {!selected&&<p className="mt-2 text-xs text-muted">Selecting a file does not start analysis.</p>}
  <p role="status" aria-live="polite" className="text-pretty mt-3">{status}</p>
  {error&&<p id={id+'-error'} role="status" aria-live="polite" data-image-metadata-unavailable className="text-pretty mt-2">{error}</p>}
  {record&&<div data-image-metadata-result className="mt-3 rounded-lg border border-line bg-surface p-3">
   <h4 className="text-balance font-semibold">{brief.title}</h4><p className="text-pretty mt-1">{brief.message}</p>
   {brief.observed&&<><dl className="mt-2 space-y-1 tabular-nums">{Object.entries(record.record.metadata_sections).map(([key,count])=><div className="flex flex-wrap justify-between gap-2" key={key}><dt>{labels[key]}</dt><dd>{count}</dd></div>)}</dl><p className="text-pretty mt-2 text-xs text-muted">Labels and counts are untrusted observations. Stored names, GPS, comments and URLs are hidden; identifying information may still remain in the unchanged file.</p></>}
   <p className="text-pretty mt-2 text-xs text-muted">No watermark or Content Credential is verified. JPEG entropy and pixels are not decoded; PNG checks cover only the declared preflight subset. An observation does not establish image validity, authorship or truth. No tag is issued.</p>
   <p id={id+'-warning'} className="text-pretty mt-2 text-xs text-muted">Exact records include the encoded-file hash, which can identify other copies. Open only when you choose; no automatic sharing.</p>
   <button type="button" className="mt-1 min-h-11 rounded-lg border border-input px-3 py-2" aria-describedby={id+'-warning'} aria-expanded={details} onClick={()=>setDetails(v=>!v)}>{details?'Hide exact image record':'Show exact image record'}</button>
   {details&&<pre data-image-metadata-details aria-label="Private image evidence" tabIndex={0} className="mt-2 max-h-80 overflow-auto whitespace-pre-wrap break-words rounded-lg border border-line bg-surface p-3 text-xs">{JSON.stringify(record,null,2)}</pre>}
  </div>}
  <p className="text-pretty mt-3 text-xs text-muted">Initial use needs public method/runtime files. On-device computation does not guarantee offline availability. <a className="underline underline-offset-4" href="/reference/image-device-guide.md">Method and privacy guide</a> · <a className="underline underline-offset-4" href="/device/image-metadata/project-notices.txt">Source notices</a></p>
 </section>;
}
