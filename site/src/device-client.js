import manifest from './device-manifest.json';
export {manifest};
export function deviceChecker(onStatus){
 let worker,ready,resolveReady,rejectReady,timer,pending,sequence=0,closed=false;
 function stop(){closed=true;clearTimeout(timer);worker?.terminate();rejectReady?.(Error('Unavailable'));pending?.reject(Error('Unavailable'));pending=null;}
 function start(){
  if(closed)throw Error('Unavailable');
  if(ready)return ready;
  onStatus('Loading the on-device checker. The first use downloads its Python runtime.');
  worker=new Worker(new URL('./device-worker.js',import.meta.url),{type:'module'});
  ready=new Promise((resolve,reject)=>{resolveReady=resolve;rejectReady=reject;});
  timer=setTimeout(stop,45000);
  worker.onerror=stop;
  worker.onmessage=({data})=>{
   if(data.type==='ready'){clearTimeout(timer);resolveReady();}
   else if(data.type==='result'&&pending?.id===data.id){clearTimeout(timer);const p=pending;pending=null;p.resolve(data.record);}
   else if(data.type==='error'||data.type==='unavailable')stop();
  };
  return ready;
 }
 return {stop,async check(text){
  if(typeof text!=='string'||!text.trim()||Array.from(text).length>manifest.max_codepoints)throw Error('Invalid input');
  await start();if(closed||pending)throw Error('Unavailable');
  onStatus('Checking on this device…');
  return new Promise((resolve,reject)=>{const id=++sequence;pending={id,resolve,reject};timer=setTimeout(stop,5000);worker.postMessage({id,text});});
 }};
}
