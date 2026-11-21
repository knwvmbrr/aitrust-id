import manifest from './mt-device-manifest.json' with {type:'json'};
// Fixed metadata only; candidate source is fetched only after explicit selection.
import mobile from './mt-mobile-device-manifest.json' with {type:'json'};
let inspect,runtime,mobileInitialization;
const digest=async bytes=>Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes)),x=>x.toString(16).padStart(2,'0')).join('');
async function bounded(response,limit){
 if(!response.ok||Number(response.headers.get('content-length'))>limit)throw Error('MT bundle unavailable');
 const reader=response.body?.getReader();if(!reader)throw Error('MT bundle unavailable');
 const chunks=[];let length=0;
 try{while(true){const {done,value}=await reader.read();if(done)break;length+=value.byteLength;if(length>limit)throw Error('MT bundle too large');chunks.push(value);}}
 catch(error){await reader.cancel();throw error;}
 finally{reader.releaseLock();}
 const bytes=new Uint8Array(length);let offset=0;for(const chunk of chunks){bytes.set(chunk,offset);offset+=chunk.byteLength;}return bytes;
}
async function installBundle(py,chosen,format){
 const bytes=await bounded(await fetch(chosen.path,{cache:'no-cache'}),1000000);
 if(bytes.length!==chosen.bundle_bytes||await digest(bytes)!==chosen.bundle_sha256)throw Error('MT bundle mismatch');
 const bundle=JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(bytes));
 if(bundle.format!==format||Object.keys(bundle).sort().join()!=='files,format'||Object.keys(bundle.files).sort().join()!==Object.keys(chosen.sources).sort().join())throw Error('MT source mismatch');
 for(const [name,text] of Object.entries(bundle.files)){
  if(typeof text!=='string'||new TextEncoder().encode(text).byteLength>200000||name.startsWith('/')||name.split('/').some(p=>!p||p==='.'||p==='..')||name.includes('\\'))throw Error('MT source unavailable');
  const raw=new TextEncoder().encode(text);if(await digest(raw)!==chosen.sources[name])throw Error('MT source mismatch');
  if(chosen!==manifest&&Object.hasOwn(manifest.sources,name)&&manifest.sources[name]!==chosen.sources[name])throw Error('MT shared source mismatch');
  const path='/mt-preview/'+name;py.FS.mkdirTree(path.slice(0,path.lastIndexOf('/')));py.FS.writeFile(path,raw);
 }
}
async function mobileInspector(){
 if(!mobileInitialization)mobileInitialization=(async()=>{
  if(!runtime||!inspect||mobile.format!=='mt-mobile-source-manifest/v1'||mobile.runtime!==manifest.runtime||mobile.normalization_id!==manifest.normalization_id)throw Error('MT optional method unavailable');
  await installBundle(runtime,mobile,'mt-mobile-source-bundle/v1');
  runtime.runPython('from tools.mt_mobile_device import inspect_mt_mobile_device');return runtime.globals.get('inspect_mt_mobile_device');
 })();
 return mobileInitialization;
}
async function initialize(){
 const {loadPyodide}=await import(/* @vite-ignore */ manifest.runtime_path+'pyodide.mjs');
 const py=await loadPyodide({indexURL:manifest.runtime_path,stdout:()=>{},stderr:()=>{}});
 await installBundle(py,manifest,'mt-device-source-bundle/v1');runtime=py;
 py.runPython("import sys\nsys.path.insert(0, '/mt-preview')\nfrom tools.mt_device import inspect_mt_device");
 inspect=py.globals.get('inspect_mt_device');self.postMessage({type:'ready'});
}
self.onmessage=async({data})=>{
 const {id,kind,text}=data||{};
 try{
  if(!inspect||!Number.isSafeInteger(id)||(!Object.hasOwn(manifest.methods,kind)&&kind!=='authority-curly')||typeof text!=='string')throw Error('MT input unavailable');
  const raw=kind==='authority-curly'?(await mobileInspector())(text):inspect(kind,text);if(typeof raw!=='string'||raw.length>1000000)throw Error('MT output unavailable');
  self.postMessage({type:'result',id,record:JSON.parse(raw)});
 }catch{self.postMessage({type:'unavailable',id});}
};
initialize().catch(()=>self.postMessage({type:'unavailable'}));
