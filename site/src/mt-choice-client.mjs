import {choiceContext,validateChoice} from './mt-choice-result.mjs';
export const MANIFEST_TIMEOUT_MS=10000;
export const CHOICE_MANIFEST_PATH='/device/mt-choice/manifest.json';
const runtimeNames=['pyodide.mjs','pyodide.asm.mjs','pyodide.asm.wasm','python_stdlib.zip','pyodide-lock.json'];
const sourceNames=['tools/mt_choice_device.py','tools/choice_framing.py','tools/language_observations.py','protocol/corpus.py','protocol/normalization.py','protocol/unicode15-data.json'];
export async function loadManifest({signal}={}){
 const controller=new AbortController();let reader,timer,abort;
 const unavailable=()=>Error('Practice files unavailable.');
 const check=()=>{if(controller.signal.aborted)throw unavailable();};
 const deadline=new Promise((_,reject)=>{timer=setTimeout(()=>{controller.abort();reject(unavailable());},MANIFEST_TIMEOUT_MS);});
 const cancelled=new Promise((_,reject)=>{abort=()=>{controller.abort();reject(unavailable());};if(signal){if(signal.aborted)abort();else signal.addEventListener('abort',abort,{once:true});}});
 const read=async()=>{
  check();const response=await fetch(CHOICE_MANIFEST_PATH,{cache:'no-cache',signal:controller.signal});check();
  if(!response.ok||Number(response.headers.get('content-length'))>65536)throw unavailable();
  reader=response.body?.getReader();if(!reader)throw unavailable();
  const chunks=[];let length=0;
  while(true){const {done,value}=await reader.read();check();if(done)break;length+=value.byteLength;if(length>65536)throw unavailable();chunks.push(value);}
  check();const bytes=new Uint8Array(length);let at=0;for(const chunk of chunks){bytes.set(chunk,at);at+=chunk.byteLength;}
  check();const m=JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(bytes));
  const keys=['format','runtime','python_version','runtime_path','runtime_files','method','normalization_id','bundle','bundle_sha256','bundle_bytes','sources','source_commit','build_inputs','experimental'];
  if(!m||typeof m!=='object'||Array.isArray(m)||Object.keys(m).sort().join()!==keys.sort().join()
   ||m.format!=='mt-choice-modal-manifest/v1'||m.runtime!=='314.0.7'||m.python_version!=='3.14.2'
   ||m.method!=='caller-bound-choice-framing-observation/1.3.0'||m.normalization_id!=='NFC-Unicode-15.0.0/v1'
   ||m.runtime_path!=='/device/runtime-314.0.7/'||m.source_commit!=='b896cb4f1c303cb2a2bcd8a5ef5e5ba5a9b7acf8'
   ||m.experimental!==true||!/^method-[a-f0-9]{64}\.json$/.test(m.bundle)||!Number.isSafeInteger(m.bundle_bytes)||m.bundle_bytes>500000||m.bundle_bytes<1
   ||!/^([a-f0-9]{64})$/.test(m.bundle_sha256)||m.bundle!=='method-'+m.bundle_sha256+'.json')throw unavailable();
  const hashes=(value,names)=>value&&typeof value==='object'&&!Array.isArray(value)&&Object.keys(value).sort().join()===names.toSorted().join()&&Object.values(value).every(h=>typeof h==='string'&&/^[a-f0-9]{64}$/.test(h));
  if(!hashes(m.sources,sourceNames)||!m.runtime_files||Object.keys(m.runtime_files).sort().join()!==runtimeNames.toSorted().join())throw unavailable();
  let runtimeBytes=0;for(const name of runtimeNames){const v=m.runtime_files[name];if(!v||Object.keys(v).sort().join()!=='bytes,sha256'||!Number.isSafeInteger(v.bytes)||v.bytes<1||v.bytes>12000000||typeof v.sha256!=='string'||!/^[a-f0-9]{64}$/.test(v.sha256))throw unavailable();runtimeBytes+=v.bytes;}
  if(runtimeBytes>32000000||!m.build_inputs||typeof m.build_inputs!=='object'||Array.isArray(m.build_inputs)||Object.keys(m.build_inputs).length>32||!hashes(m.build_inputs,Object.keys(m.build_inputs)))throw unavailable();
  check();return m;
 };
 try{return await Promise.race([read(),deadline,cancelled]);}
 catch{throw unavailable();}
 finally{
  clearTimeout(timer);controller.abort();if(signal)signal.removeEventListener('abort',abort);
  if(reader){try{Promise.resolve(reader.cancel()).catch(()=>{});}catch{}try{reader.releaseLock();}catch{}}
 }
}
export function choiceClient(manifest,{onStatus=()=>{},createWorker=()=>new Worker('/device/mt-choice/mt-choice-worker.mjs',{type:'module'}),loadTimeout=45000,checkTimeout=6000}={}){
 let active=null,sequence=0;
 return {stop(){active?.finish(Error('Check cancelled.'));},check(request){
  if(active)return Promise.reject(Error('Check busy.'));
  return new Promise((resolve,reject)=>{
   const id=++sequence;let worker,timer,done=false,phase='binding';
   const finish=(error,value)=>{if(done)return;done=true;clearTimeout(timer);if(active?.id===id)active=null;try{worker?.terminate();}catch{error=Error('Worker cleanup unavailable.');}error?reject(error):resolve(value);};
   active={id,finish};
   // The existing startup budget includes asynchronous request binding.
   timer=setTimeout(()=>finish(Error('Runtime unavailable.')),loadTimeout);
   (async()=>{
    try{
     const {context,wire}=await choiceContext(request,manifest);if(done)return;
     phase='loading';onStatus('Loading the check on this device…');
     worker=createWorker();worker.onerror=worker.onmessageerror=()=>finish(Error('Worker unavailable.'));
     worker.onmessage=({data})=>{
      if(done)return;
      try{
       if(data?.type==='ready'&&phase==='loading'){
        phase='checking';clearTimeout(timer);timer=setTimeout(()=>finish(Error('Check unavailable.')),checkTimeout);
        onStatus('Inspecting your declared items…');worker.postMessage({id,request:wire});return;
       }
       if(data?.type==='result'&&phase==='checking'&&data.id===id){return finish(null,validateChoice(data.record,context,manifest));}
       finish(Error('No valid observation completed.'));
      }catch{finish(Error('No valid observation completed.'));}
     };
    }catch{finish(Error('Check unavailable.'));}
   })();
  });
 }};
}
