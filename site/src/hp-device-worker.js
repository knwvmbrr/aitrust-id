import manifest from './hp-device-manifest.json' with {type:'json'};
let inspect;
const digest=async bytes=>Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes)),x=>x.toString(16).padStart(2,'0')).join('');
async function bounded(response,limit){
 if(!response.ok||Number(response.headers.get('content-length'))>limit)throw Error('HP bundle unavailable');
 const reader=response.body?.getReader();if(!reader)throw Error('HP bundle unavailable');
 const chunks=[];let length=0;
 try{while(true){const {done,value}=await reader.read();if(done)break;length+=value.byteLength;if(length>limit)throw Error('HP bundle too large');chunks.push(value);}}
 catch(error){await reader.cancel();throw error;}
 finally{reader.releaseLock();}
 const bytes=new Uint8Array(length);let offset=0;for(const chunk of chunks){bytes.set(chunk,offset);offset+=chunk.byteLength;}return bytes;
}
async function initialize(){
 const {loadPyodide}=await import(/* @vite-ignore */ manifest.runtime_path+'pyodide.mjs');
 const py=await loadPyodide({indexURL:manifest.runtime_path,stdout:()=>{},stderr:()=>{}});
 const bytes=await bounded(await fetch(manifest.path,{cache:'no-cache'}),1000000);
 if(bytes.length!==manifest.bundle_bytes||await digest(bytes)!==manifest.bundle_sha256)throw Error('HP bundle mismatch');
 const bundle=JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(bytes));
 if(bundle.format!=='hp-device-source-bundle/v1'||Object.keys(bundle).sort().join()!=='files,format'||Object.keys(bundle.files).sort().join()!==Object.keys(manifest.sources).sort().join())throw Error('HP source mismatch');
 for(const [name,text] of Object.entries(bundle.files)){
  if(typeof text!=='string'||new TextEncoder().encode(text).byteLength>200000||name.startsWith('/')||name.split('/').some(p=>!p||p==='.'||p==='..')||name.includes('\\'))throw Error('HP source unavailable');
  const raw=new TextEncoder().encode(text);if(await digest(raw)!==manifest.sources[name])throw Error('HP source mismatch');
  const path='/hp-preview/'+name;py.FS.mkdirTree(path.slice(0,path.lastIndexOf('/')));py.FS.writeFile(path,raw);
 }
 py.runPython("import sys\nsys.path.insert(0, '/hp-preview')\nfrom tools.hp_device import inspect_hp_device");
 inspect=py.globals.get('inspect_hp_device');self.postMessage({type:'ready'});
}
self.onmessage=({data})=>{
 const {id,text}=data||{};
 try{
  if(!inspect||!Number.isSafeInteger(id)||typeof text!=='string')throw Error('HP input unavailable');
  const raw=inspect(text);if(typeof raw!=='string'||raw.length>262144)throw Error('HP output unavailable');
  self.postMessage({type:'result',id,record:JSON.parse(raw)});
 }catch{self.postMessage({type:'unavailable',id});}
};
initialize().catch(()=>self.postMessage({type:'unavailable'}));
