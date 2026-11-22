import {PARSERS,MAX_INPUT,imageContext,validateImageRecord} from './image-metadata-result.mjs';
const RUNTIME={"pyodide.mjs":{"bytes":17931,"sha256":"6f1d60f7bf529beb300f0f47983c921d3982363640ba20af0e38efdddbc66109"},"pyodide.asm.mjs":{"bytes":1250344,"sha256":"f7cdc8ece80678ceb712f8e65ebe6d3a83203a180c399865f49612a051693635"},"pyodide.asm.wasm":{"bytes":9598218,"sha256":"cc36e3cab04fdfc9a63ff13eb52eae2b911bf46c025cc7b281f394bd3de1d5e6"},"python_stdlib.zip":{"bytes":2545637,"sha256":"fa1957e5777068fc4f7437f96d860ae2fbe9c19732ba06c84e004ec16dd7dd7a"},"pyodide-lock.json":{"bytes":119077,"sha256":"5dc2fc119108bc148c7457dc86e7675b5c87e1cafd420b9c34c1eaef7b36c010"}};
export const IMAGE_MANIFEST='/device/image-metadata/manifest.json';
const hex=/^[a-f0-9]{64}$/;
const need=ok=>{if(!ok)throw Error('Image preview unavailable.');};
const closed=(v,expected)=>v&&Object.getPrototypeOf(v)===Object.prototype&&Object.keys(v).sort().join()===expected.slice().sort().join();
const same=(v,p)=>closed(v,Object.keys(p))&&Object.keys(p).every(k=>typeof p[k]==='object'?same(v[k],p[k]):v[k]===p[k]);
export function validateImageManifest(value){
 need(closed(value,['format','source_commit','runtime','python_version','runtime_path','runtime_files','bundle','bundle_sha256','bundle_bytes','parsers','max_input_bytes','build_inputs','experimental']));
 need(value.format==='image-metadata-device-manifest/v1'&&value.source_commit==='8e1b1a23a1bef0659bf1ec567ceef647b5cd76a5'&&value.runtime==='314.0.7'&&value.python_version==='3.14.2'&&value.runtime_path==='/device/runtime-314.0.7/'&&same(value.runtime_files,RUNTIME)&&same(value.parsers,PARSERS)&&value.max_input_bytes===MAX_INPUT&&value.experimental===true);
 need(typeof value.bundle==='string'&&/^method-[a-f0-9]{64}\.json$/.test(value.bundle)&&hex.test(value.bundle_sha256)&&value.bundle==='method-'+value.bundle_sha256+'.json'&&Number.isSafeInteger(value.bundle_bytes)&&value.bundle_bytes>0&&value.bundle_bytes<=200000);
 need(value.build_inputs&&Object.getPrototypeOf(value.build_inputs)===Object.prototype&&Object.keys(value.build_inputs).length>0&&Object.keys(value.build_inputs).length<=32&&Object.entries(value.build_inputs).every(([k,v])=>typeof k==='string'&&k.length<200&&/^[A-Za-z0-9._/-]+$/.test(k)&&typeof v==='string'&&hex.test(v)));
 return value;
}
export async function loadImageManifest({signal}={}){
 const controller=new AbortController();let reader,timer,abort;
 const unavailable=()=>Error('Image preview unavailable.');const check=()=>{if(controller.signal.aborted)throw unavailable();};
 const deadline=new Promise((_,reject)=>{timer=setTimeout(()=>{controller.abort();reject(unavailable());},10000);});
 const cancelled=new Promise((_,reject)=>{abort=()=>{controller.abort();reject(unavailable());};if(signal){if(signal.aborted)abort();else signal.addEventListener('abort',abort,{once:true});}});
 const read=async()=>{
  check();const response=await fetch(IMAGE_MANIFEST,{cache:'no-cache',signal:controller.signal});check();need(response.ok&&Number(response.headers.get('content-length'))<=65536);reader=response.body?.getReader();need(reader);
  let size=0;const chunks=[];while(true){const {done,value}=await reader.read();check();if(done)break;size+=value.length;need(size<=65536);chunks.push(value);}
  const bytes=new Uint8Array(size);let at=0;for(const part of chunks){bytes.set(part,at);at+=part.length;}
  check();return validateImageManifest(JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(bytes)));
 };
 try{return await Promise.race([read(),deadline,cancelled]);}
 catch{throw unavailable();}
 finally{clearTimeout(timer);controller.abort();signal?.removeEventListener('abort',abort);if(reader){try{Promise.resolve(reader.cancel()).catch(()=>{});}catch{}try{reader.releaseLock();}catch{}}}
}
export function imageClient({onStatus=()=>{},createWorker=()=>new Worker('/device/image-metadata/image-metadata-worker.mjs',{type:'module'}),createReader=()=>new FileReader(),loadTimeout=45000,checkTimeout=6000}={}){
 let active=null,serial=0;
 function stop(){active?.cancel();}
 function check(file){
  stop();let size;
  try{size=Object.getOwnPropertyDescriptor(Blob.prototype,'size').get.call(file);need(Number.isSafeInteger(size)&&size>0&&size<=MAX_INPUT);}
  catch{const error=Error('Choose a PNG or JPEG up to 10 MiB.');error.code='input_limit';return Promise.reject(error);}
  const id=++serial;return new Promise((resolve,reject)=>{
   let done=false,worker=null,timer=null,reader=null,rejectCapture=null,context;
   const finish=(error,value)=>{if(done)return;done=true;clearTimeout(timer);if(active?.id===id)active=null;const owned=worker,reading=reader,cancelRead=rejectCapture;worker=null;reader=null;rejectCapture=null;try{if(reading?.readyState===1)reading.abort();}catch{error=Error('Image read cleanup unavailable.');}cancelRead?.(Error('Image capture cancelled.'));if(reading)reading.onload=reading.onerror=reading.onabort=null;try{owned?.terminate();}catch{error=Error('Image worker cleanup unavailable.');}error?reject(error):resolve(value);};
   active={id,cancel:()=>{const error=Error('Image check cancelled.');error.code='cancelled';finish(error);}};
   timer=setTimeout(()=>finish(Error('Image startup unavailable.')),loadTimeout);
   (async()=>{
    try{
     onStatus('Reading your selected file on this device…');const bytes=await new Promise((resolveRead,rejectRead)=>{
      rejectCapture=rejectRead;const own=createReader();reader=own;
      const release=()=>{if(reader===own)reader=null;rejectCapture=null;own.onload=own.onerror=own.onabort=null;};
      own.onload=()=>{const result=own.result;release();result instanceof ArrayBuffer?resolveRead(result):rejectRead(Error('Image read unavailable.'));};
      own.onerror=own.onabort=()=>{release();rejectRead(Error('Image read unavailable.'));};
      own.readAsArrayBuffer(file);
     });if(done)return;need(bytes.byteLength===size);context=await imageContext(bytes);if(done)return;
     onStatus('Loading the private image reader…');worker=createWorker();
     worker.onerror=worker.onmessageerror=()=>finish(Error('Image worker unavailable.'));
     let sent=false;
     worker.onmessage=({data})=>{
      if(done)return;
      try{
       if(!data||typeof data!=='object')throw Error('Image worker unavailable.');
       if(!sent&&closed(data,['type'])&&data.type==='ready'){
        sent=true;clearTimeout(timer);timer=setTimeout(()=>finish(Error('Image evaluation unavailable.')),checkTimeout);onStatus('Inspecting bounded container details…');worker.postMessage({id,kind:context.kind,bytes},[bytes]);return;
       }
       if(!sent||!closed(data,['type','id','record'])||data.type!=='result'||data.id!==id)throw Error('Image worker unavailable.');
       finish(null,validateImageRecord(data.record,context));
      }catch{finish(Error('Image result unavailable.'));}
     };
    }catch(error){if(error?.code==='unsupported_format')finish(error);else finish(Error('Image preview unavailable.'));}
   })();
  });
 }
 return {check,stop};
}
