import {choiceContext,validateChoice} from './mt-choice-result.mjs';
export async function loadManifest(){
 const response=await fetch('./manifest.json',{cache:'no-cache'});
 if(!response.ok||Number(response.headers.get('content-length'))>65536)throw Error('Practice files unavailable.');
 const reader=response.body?.getReader();if(!reader)throw Error('Practice files unavailable.');
 const chunks=[];let length=0;
 try{while(true){const {done,value}=await reader.read();if(done)break;length+=value.byteLength;if(length>65536)throw Error('Practice files unavailable.');chunks.push(value);}}
 catch(error){try{await reader.cancel();}catch{}throw error;}finally{reader.releaseLock();}
 const bytes=new Uint8Array(length);let at=0;for(const chunk of chunks){bytes.set(chunk,at);at+=chunk.byteLength;}
 const m=JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(bytes));
 if(m.format!=='mt-choice-practice-manifest/v1'||m.runtime!=='314.0.7'||m.method!=='caller-bound-choice-framing-observation/1.3.0'||m.runtime_path!=='./runtime/'||!/^method-[a-f0-9]{64}\.json$/.test(m.bundle)||!Number.isSafeInteger(m.bundle_bytes)||m.bundle_bytes>500000||m.bundle_bytes<1)throw Error('Practice files unavailable.');
 return m;
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
