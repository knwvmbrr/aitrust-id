import manifest from './mt-device-manifest.json' with {type:'json'};
import {validMTRecord,mtSubject,explainMT} from './mt-device-result.js';
export {manifest};
export function validMTInput(kind,text){
 if(typeof kind!=='string'||(!Object.hasOwn(manifest.methods,kind)&&kind!=='authority-curly')||typeof text!=='string'||!text.trim()||Array.from(text).length>manifest.max_codepoints||new TextEncoder().encode(text).byteLength>manifest.max_bytes||text.includes('\0')||Array.from(text).some(c=>{const n=c.codePointAt(0);return n>=0xd800&&n<=0xdfff;}))throw Error('Invalid MT input');
}
export function mtDeviceClient({onStatus=()=>{},createWorker=()=>new Worker(new URL('./mt-device-worker.js',import.meta.url),{type:'module'}),loadTimeout=45000,checkTimeout=6000}={}){
 let active=null,sequence=0;
 function stop(){active?.finish(Error('MT check unavailable'));}
 return {stop,check(kind,text){
  try{validMTInput(kind,text);}catch(error){return Promise.reject(error);}
  if(active)return Promise.reject(Error('MT check busy'));
  return new Promise((resolve,reject)=>{
   let worker,timer,finished=false,phase='loading';const id=++sequence;
   const finish=(error,value)=>{if(finished)return;finished=true;clearTimeout(timer);if(active?.id===id)active=null;try{worker?.terminate();}catch{error=Error('MT worker cleanup unavailable');}error?reject(error):resolve(value);};
   active={id,finish};
   try{
    const selected=kind==='authority-curly'?import('./mt-mobile-device-result.js'):null;
    const subject=selected?selected.then(module=>module.mtMobileSubject(text)):mtSubject(text);subject.catch(()=>finish(Error('MT input identity unavailable')));
    onStatus('Loading the wording check on your device…');worker=createWorker();
    timer=setTimeout(()=>finish(Error('MT load timed out')),loadTimeout);
    worker.onerror=()=>finish(Error('MT worker unavailable'));
    worker.onmessageerror=()=>finish(Error('MT worker unavailable'));
    worker.onmessage=async({data})=>{
     if(finished)return;
     try{
      if(data?.type==='ready'&&phase==='loading'){
       phase='checking';clearTimeout(timer);timer=setTimeout(()=>finish(Error('MT check timed out')),checkTimeout);
       onStatus('Looking at wording on this device…');worker.postMessage({id,kind,text});return;
      }
      if(data?.type==='result'&&phase==='checking'&&data.id===id){
       if(kind!=='authority-curly'&&JSON.stringify(data.record).length>1000000)throw Error('MT output too large');
       phase='validating';const context=await subject;if(finished)return;
       return finish(null,selected?(await selected).validMTMobileRecord(data.record,context):validMTRecord(data.record,kind,context));
      }
      finish(Error('MT observation unavailable'));
     }catch{finish(Error('MT observation unavailable'));}
    };
   }catch{finish(Error('MT worker unavailable'));}
  });
 }};
}

export async function explainMTSelection(record,kind){
 return kind==='authority-curly'?(await import('./mt-mobile-device-result.js')).explainMTMobile(record):explainMT(record);
}
