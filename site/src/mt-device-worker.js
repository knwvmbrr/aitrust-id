import manifest from './mt-device-manifest.json' with {type:'json'};
let inspect;
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
async function initialize(){
 const {loadPyodide}=await import(/* @vite-ignore */ manifest.runtime_path+'pyodide.mjs');
 const py=await loadPyodide({indexURL:manifest.runtime_path,stdout:()=>{},stderr:()=>{}});
 const bytes=await bounded(await fetch(manifest.path,{cache:'no-cache'}),1000000);
 if(bytes.length!==manifest.bundle_bytes||await digest(bytes)!==manifest.bundle_sha256)throw Error('MT bundle mismatch');
 const bundle=JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(bytes));
 if(bundle.format!=='mt-device-source-bundle/v1'||Object.keys(bundle).sort().join()!=='files,format'||Object.keys(bundle.files).sort().join()!==Object.keys(manifest.sources).sort().join())throw Error('MT source mismatch');
 for(const [name,text] of Object.entries(bundle.files)){
  if(typeof text!=='string'||new TextEncoder().encode(text).byteLength>200000||name.startsWith('/')||name.split('/').some(p=>!p||p==='.'||p==='..')||name.includes('\\'))throw Error('MT source unavailable');
  const raw=new TextEncoder().encode(text);if(await digest(raw)!==manifest.sources[name])throw Error('MT source mismatch');
  const path='/mt-preview/'+name;py.FS.mkdirTree(path.slice(0,path.lastIndexOf('/')));py.FS.writeFile(path,raw);
 }
 py.runPython("import sys\nsys.path.insert(0, '/mt-preview')\nfrom tools.mt_device import inspect_mt_device");
 inspect=py.globals.get('inspect_mt_device');self.postMessage({type:'ready'});
}
self.onmessage=({data})=>{
 const {id,kind,text}=data||{};
 try{
  if(!inspect||!Number.isSafeInteger(id)||!Object.hasOwn(manifest.methods,kind)||typeof text!=='string')throw Error('MT input unavailable');
  const raw=inspect(kind,text);if(typeof raw!=='string'||raw.length>1000000)throw Error('MT output unavailable');
  self.postMessage({type:'result',id,record:JSON.parse(raw)});
 }catch{self.postMessage({type:'unavailable',id});}
};
initialize().catch(()=>self.postMessage({type:'unavailable'}));
