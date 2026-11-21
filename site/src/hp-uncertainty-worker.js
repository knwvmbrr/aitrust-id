import manifest from './hp-uncertainty-manifest.json' with {type:'json'};
let inspect,called=false;
const digest=async bytes=>Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes)),x=>x.toString(16).padStart(2,'0')).join('');
async function bounded(response,limit){
 if(!response.ok||Number(response.headers.get('content-length'))>limit)throw Error();const reader=response.body?.getReader();if(!reader)throw Error();const chunks=[];let length=0;
 try{while(true){const {done,value}=await reader.read();if(done)break;length+=value.byteLength;if(length>limit)throw Error();chunks.push(value);}}catch(error){await reader.cancel();throw error;}finally{reader.releaseLock();}
 const bytes=new Uint8Array(length);let offset=0;for(const chunk of chunks){bytes.set(chunk,offset);offset+=chunk.byteLength;}return bytes;
}
async function initialize(){
 const selected=manifest.checks.hedge;
 const {loadPyodide}=await import(/* @vite-ignore */ manifest.runtime_path+'pyodide.mjs');
 const py=await loadPyodide({indexURL:manifest.runtime_path,stdout:()=>{},stderr:()=>{}});
 const raw=await bounded(await fetch(selected.path,{cache:'no-cache'}),1000000);
 if(raw.length!==selected.bundle_bytes||await digest(raw)!==selected.bundle_sha256)throw Error();
 const bundle=JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(raw));
 if(bundle.format!=='hp-uncertainty-source-bundle/v1'||Object.keys(bundle).sort().join()!=='files,format'||!bundle.files||Object.keys(bundle.files).sort().join()!==Object.keys(selected.sources).sort().join())throw Error();
 for(const [name,text] of Object.entries(bundle.files)){
  if(typeof text!=='string'||new TextEncoder().encode(text).length>200000||name.startsWith('/')||name.includes('\\')||name.split('/').some(p=>!p||p==='.'||p==='..'))throw Error();
  const bytes=new TextEncoder().encode(text);if(await digest(bytes)!==selected.sources[name])throw Error();
  const file='/hp-uncertainty/'+name;py.FS.mkdirTree(file.slice(0,file.lastIndexOf('/')));py.FS.writeFile(file,bytes);
 }
 py.runPython("import sys\nsys.path.insert(0, '/hp-uncertainty')\nfrom tools.hp_uncertainty_device import inspect_hp_uncertainty_device");inspect=py.globals.get('inspect_hp_uncertainty_device');self.postMessage({type:'ready'});
}
self.onmessage=({data})=>{const {id,text,annotation}=data||{};try{
 if(!inspect||called||Object.keys(data).sort().join()!=='annotation,id,text'||!Number.isSafeInteger(id)||typeof text!=='string'||!annotation||typeof annotation!=='object')throw Error();
 called=true;const raw=inspect(text,JSON.stringify(annotation));if(typeof raw!=='string'||raw.length>262144)throw Error();self.postMessage({type:'result',id,record:JSON.parse(raw)});
}catch{self.postMessage({type:'unavailable',id});}};
initialize().catch(()=>self.postMessage({type:'unavailable'}));
