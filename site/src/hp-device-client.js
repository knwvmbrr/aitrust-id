import manifest from './hp-device-manifest.json' with {type:'json'};
import {hpSubject,validHPRecord} from './hp-device-result.js';
export {manifest};
export function validHPInput(text){
 if(typeof text!=='string'||!text.trim()||Array.from(text).length>manifest.max_codepoints||new TextEncoder().encode(text).length>manifest.max_bytes||text.includes('\0')||Array.from(text).some(c=>{const n=c.codePointAt(0);return n>=0xd800&&n<=0xdfff;}))throw Error('Invalid literal-detail input');
}
export function hpDeviceClient({onStatus=()=>{},createWorker=()=>new Worker(new URL('./hp-device-worker.js',import.meta.url),{type:'module'}),loadTimeout=45000,checkTimeout=6000}={}){
 let active=null,sequence=0;
 function stop(){active?.finish(Error('Literal-detail check unavailable'));}
 return {stop,check(text){
  try{validHPInput(text);}catch(error){return Promise.reject(error);}
  if(active)return Promise.reject(Error('Literal-detail check busy'));
  return new Promise((resolve,reject)=>{
   let worker,timer,finished=false,phase='loading';const id=++sequence;
   const finish=(error,value)=>{if(finished)return;finished=true;clearTimeout(timer);try{worker?.terminate();}catch{error=Error('Literal-detail worker cleanup unavailable');}if(active?.id===id)active=null;error?reject(error):resolve(value);};active={id,finish};
   try{
    const subject=hpSubject(text);subject.catch(()=>finish(Error('Input identity unavailable')));
    onStatus('Loading the detail checker on your device…');worker=createWorker();timer=setTimeout(()=>finish(Error('Detail checker load deadline')),loadTimeout);
    worker.onerror=()=>finish(Error('Detail worker unavailable'));worker.onmessageerror=()=>finish(Error('Detail worker unavailable'));
    worker.onmessage=async({data})=>{
     if(finished)return;
     try{
      if(data?.type==='ready'&&phase==='loading'){phase='checking';clearTimeout(timer);timer=setTimeout(()=>finish(Error('Detail check deadline')),checkTimeout);onStatus('Looking for literal details on this device…');worker.postMessage({id,text});return;}
      if(data?.type==='result'&&phase==='checking'&&data.id===id){phase='validating';const context=await subject;if(finished)return;return finish(null,validHPRecord(data.record,context));}
      finish(Error('Literal-detail observation unavailable'));
     }catch{finish(Error('Literal-detail observation unavailable'));}
    };
   }catch{finish(Error('Literal-detail worker unavailable'));}
  });
 }};
}
