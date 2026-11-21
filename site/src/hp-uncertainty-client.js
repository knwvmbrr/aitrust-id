import manifest from './hp-uncertainty-manifest.json' with {type:'json'};
import {validUncertaintyInput,uncertaintyContext,validUncertaintyRecord} from './hp-uncertainty-result.js';
export {manifest,validUncertaintyInput};
export function hpUncertaintyClient({onStatus=()=>{},createWorker=()=>new Worker(new URL('./hp-uncertainty-worker.js',import.meta.url),{type:'module'}),loadTimeout=45000,checkTimeout=6000}={}){
 let active=null,sequence=0;
 return {stop(){active?.finish(Error('Uncertainty check cancelled'));},check(text,selection){
  try{validUncertaintyInput(text);if(selection!==true)throw Error();}catch{return Promise.reject(Error('Explicit supported context required'));}
  if(active)return Promise.reject(Error('Uncertainty check busy'));
  return new Promise((resolve,reject)=>{
   const id=++sequence;let worker,timer,finished=false,phase='loading';
   const finish=(error,value)=>{if(finished)return;finished=true;clearTimeout(timer);try{worker?.terminate();}catch{error=Error('Uncertainty worker cleanup unavailable');}if(active?.id===id)active=null;error?reject(error):resolve(value);};active={id,finish};
   try{
    const context=uncertaintyContext(text,selection);context.catch(()=>finish(Error('Context identity unavailable')));
    timer=setTimeout(()=>finish(Error('Uncertainty load deadline')),loadTimeout);onStatus('Loading the wording check on your device…');worker=createWorker();
    worker.onerror=()=>finish(Error('Uncertainty worker unavailable'));worker.onmessageerror=()=>finish(Error('Uncertainty worker unavailable'));
    worker.onmessage=async({data})=>{if(finished)return;try{
     if(data?.type==='ready'&&phase==='loading'){phase='checking';clearTimeout(timer);timer=setTimeout(()=>finish(Error('Uncertainty check deadline')),checkTimeout);onStatus('Looking for uncertainty words…');const c=await context;if(finished)return;worker.postMessage({id,text,annotation:c.annotation});return;}
     if(data?.type==='result'&&phase==='checking'&&data.id===id){phase='validating';const c=await context;if(finished)return;return finish(null,validUncertaintyRecord(data.record,c));}
     finish(Error('Uncertainty observation unavailable'));
    }catch{finish(Error('Uncertainty observation unavailable'));}};
   }catch{finish(Error('Uncertainty worker unavailable'));}
  });
 }};
}
