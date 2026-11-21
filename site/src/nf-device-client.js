import manifest from './nf-device-manifest.json' with {type:'json'};
import {nfInputs,validNFInput,validLiteralRecord,explainNF} from './nf-device-result.js';
export {manifest,validNFInput,explainNF};
export function nfDeviceClient({onStatus=()=>{},createWorker=()=>new Worker(new URL('./nf-device-worker.js',import.meta.url),{type:'module'}),loadValidator=()=>import('./nf-cosine-result.js'),loadTimeout=45000,checkTimeout=6000}={}){
 let active=null,sequence=0;
 return {stop(){active?.finish(Error('Reference check cancelled'));},check(claim,passage,check){
  try{validNFInput(claim);validNFInput(passage);if(!['literal','cosine'].includes(check))throw Error();}catch{return Promise.reject(Error('Invalid reference inputs'));}
  if(active)return Promise.reject(Error('Reference check busy'));
  return new Promise((resolve,reject)=>{
   const id=++sequence;let worker,timer,finished=false,phase='loading';
   const finish=(error,value)=>{if(finished)return;finished=true;clearTimeout(timer);try{worker?.terminate();}catch{error=Error('Reference worker cleanup unavailable');}if(active?.id===id)active=null;error?reject(error):resolve(value);};active={id,finish};
   try{
    const context=nfInputs(claim,passage,check),validator=check==='literal'?Promise.resolve(validLiteralRecord):loadValidator().then(m=>m.validCosineRecord);
    context.catch(()=>finish(Error('Input identity unavailable')));validator.catch(()=>finish(Error('Selected method unavailable')));
    timer=setTimeout(()=>finish(Error('Reference load deadline')),loadTimeout);onStatus('Loading this check on your device…');worker=createWorker();
    worker.onerror=()=>finish(Error('Reference worker unavailable'));worker.onmessageerror=()=>finish(Error('Reference worker unavailable'));
    worker.onmessage=async({data})=>{if(finished)return;try{
     if(data?.type==='ready'&&phase==='loading'){phase='checking';clearTimeout(timer);timer=setTimeout(()=>finish(Error('Reference check deadline')),checkTimeout);onStatus('Comparing on your device…');worker.postMessage({id,claim,passage});return;}
     if(data?.type==='result'&&phase==='checking'&&data.id===id){phase='validating';const [c,validate]=await Promise.all([context,validator]);if(finished)return;return finish(null,validate(data.record,c));}
     finish(Error('Selected reference check unavailable'));
    }catch{finish(Error('Selected reference check unavailable'));}};
    worker.postMessage({type:'init',check});
   }catch{finish(Error('Reference worker unavailable'));}
  });
 }};
}
