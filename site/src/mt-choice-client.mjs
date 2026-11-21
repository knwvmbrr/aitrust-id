import {choiceContext,validateChoice} from './mt-choice-result.mjs';
export const MANIFEST_TIMEOUT_MS=10000;
export async function loadManifest(){
 const controller=new AbortController();let reader,timer;
 const unavailable=()=>Error('Practice files unavailable.');
 const check=()=>{if(controller.signal.aborted)throw unavailable();};
 const deadline=new Promise((_,reject)=>{timer=setTimeout(()=>{controller.abort();reject(unavailable());},MANIFEST_TIMEOUT_MS);});
 const read=async()=>{
  const response=await fetch('./manifest.json',{cache:'no-cache',signal:controller.signal});check();
  if(!response.ok||Number(response.headers.get('content-length'))>65536)throw unavailable();
  reader=response.body?.getReader();if(!reader)throw unavailable();
  const chunks=[];let length=0;
  while(true){const {done,value}=await reader.read();check();if(done)break;length+=value.byteLength;if(length>65536)throw unavailable();chunks.push(value);}
  check();const bytes=new Uint8Array(length);let at=0;for(const chunk of chunks){bytes.set(chunk,at);at+=chunk.byteLength;}
  check();const m=JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(bytes));
  if(m.format!=='mt-choice-practice-manifest/v1'||m.runtime!=='314.0.7'||m.method!=='caller-bound-choice-framing-observation/1.3.0'||m.runtime_path!=='./runtime/'||!/^method-[a-f0-9]{64}\.json$/.test(m.bundle)||!Number.isSafeInteger(m.bundle_bytes)||m.bundle_bytes>500000||m.bundle_bytes<1)throw unavailable();
  check();return m;
 };
 try{return await Promise.race([read(),deadline]);}
 catch{throw unavailable();}
 finally{
  clearTimeout(timer);controller.abort();
  if(reader){try{Promise.resolve(reader.cancel()).catch(()=>{});}catch{}try{reader.releaseLock();}catch{}}
 }
}
export function choiceClient(manifest,{onStatus=()=>{},createWorker=()=>new Worker(new URL('./mt-choice-worker.mjs',import.meta.url),{type:'module'}),loadTimeout=45000,checkTimeout=6000}={}){
 let active=null,sequence=0;
 return {stop(){active?.finish(Error('Check cancelled.'));},check(request){
  if(active)return Promise.reject(Error('Check busy.'));
  return new Promise((resolve,reject)=>{
   const id=++sequence;let worker,timer,done=false,phase='binding';
   const finish=(error,value)=>{if(done)return;done=true;clearTimeout(timer);if(active?.id===id)active=null;try{worker?.terminate();}catch{error=Error('Worker cleanup unavailable.');}error?reject(error):resolve(value);};
   active={id,finish};
   (async()=>{
    try{
     const {context,wire}=await choiceContext(request,manifest);if(done)return;
     phase='loading';onStatus('Loading the check on this device…');
     timer=setTimeout(()=>finish(Error('Runtime unavailable.')),loadTimeout);
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
