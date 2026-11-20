import manifest from './credential-device-manifest.json' with {type:'json'};
import {credentialSubject,validCredentialRecord} from './credential-device-result.js';
export {manifest};
export function validCredentialInput(text){
 if(typeof text!=='string'||!text.trim()||Array.from(text).length>manifest.max_codepoints||new TextEncoder().encode(text).length>manifest.max_bytes||text.includes('\0')||Array.from(text).some(c=>{const n=c.codePointAt(0);return n>=0xd800&&n<=0xdfff;}))throw Error('Invalid Python-flow input');
}
export function credentialDeviceClient({onStatus=()=>{},createWorker=()=>new Worker(new URL('./credential-device-worker.js',import.meta.url),{type:'module'}),loadTimeout=45000,checkTimeout=6000}={}){
 let active=null,sequence=0;
 function stop(){active?.finish(Error('Python-flow check unavailable'));}
 return {stop,check(text){
  try{validCredentialInput(text);}catch(error){return Promise.reject(error);}
  if(active)return Promise.reject(Error('Python-flow check busy'));
  return new Promise((resolve,reject)=>{
   let worker,timer,finished=false,phase='loading';const id=++sequence;
   const finish=(error,value)=>{if(finished)return;finished=true;clearTimeout(timer);try{worker?.terminate();}catch{error=Error('Python-flow worker cleanup unavailable');}if(active?.id===id)active=null;error?reject(error):resolve(value);};active={id,finish};
   try{
    const subject=credentialSubject(text);subject.catch(()=>finish(Error('Input identity unavailable')));
    onStatus('Loading the Python checker on your device…');worker=createWorker();timer=setTimeout(()=>finish(Error('Python checker load deadline')),loadTimeout);
    worker.onerror=()=>finish(Error('Python-flow worker unavailable'));worker.onmessageerror=()=>finish(Error('Python-flow worker unavailable'));
    worker.onmessage=async({data})=>{
     if(finished)return;
     try{
      if(data?.type==='ready'&&phase==='loading'){phase='checking';clearTimeout(timer);timer=setTimeout(()=>finish(Error('Python check deadline')),checkTimeout);onStatus('Inspecting Python flow on this device…');worker.postMessage({id,text});return;}
      if(data?.type==='result'&&phase==='checking'&&data.id===id){phase='validating';const context=await subject;if(finished)return;return finish(null,validCredentialRecord(data.record,context));}
      finish(Error('Python-flow observation unavailable'));
     }catch{finish(Error('Python-flow observation unavailable'));}
    };
   }catch{finish(Error('Python-flow worker unavailable'));}
  });
 }};
}
