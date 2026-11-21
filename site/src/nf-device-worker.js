import manifest from './nf-device-manifest.json' with {type:'json'};
let inspect,selection,started=false,called=false;
const digest=async bytes=>Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes)),x=>x.toString(16).padStart(2,'0')).join('');
async function bounded(response,limit){
 if(!response.ok||Number(response.headers.get('content-length'))>limit)throw Error();const reader=response.body?.getReader();if(!reader)throw Error();const chunks=[];let length=0;
 try{while(true){const {done,value}=await reader.read();if(done)break;length+=value.byteLength;if(length>limit)throw Error();chunks.push(value);}}catch(error){await reader.cancel();throw error;}finally{reader.releaseLock();}
 const bytes=new Uint8Array(length);let at=0;for(const chunk of chunks){bytes.set(chunk,at);at+=chunk.byteLength;}return bytes;
}
async function initialize(check){
 const m=manifest.checks[check];if(!m)throw Error();selection=check;
 const {loadPyodide}=await import(/* @vite-ignore */ manifest.runtime_path+'pyodide.mjs');
 const py=await loadPyodide({indexURL:manifest.runtime_path,stdout:()=>{},stderr:()=>{}});
 const bytes=await bounded(await fetch(m.path,{cache:'no-cache'}),1000000);if(bytes.length!==m.bundle_bytes||await digest(bytes)!==m.bundle_sha256)throw Error();
 const bundle=JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(bytes));
 if(bundle.format!=='nf-device-source-bundle/v1'||Object.keys(bundle).sort().join()!=='files,format'||!bundle.files||Object.keys(bundle.files).sort().join()!==Object.keys(m.sources).sort().join())throw Error();
 for(const [name,text] of Object.entries(bundle.files)){
  if(typeof text!=='string'||new TextEncoder().encode(text).length>200000||name.startsWith('/')||name.includes('\\')||name.split('/').some(p=>!p||p==='.'||p==='..'))throw Error();
  const raw=new TextEncoder().encode(text);if(await digest(raw)!==m.sources[name])throw Error();
  const path='/nf-preview/'+name;py.FS.mkdirTree(path.slice(0,path.lastIndexOf('/')));py.FS.writeFile(path,raw);
 }
 py.runPython("import sys\nsys.path.insert(0, '/nf-preview')\nfrom tools.nf_device import inspect_nf_device");inspect=py.globals.get('inspect_nf_device');self.postMessage({type:'ready'});
}
self.onmessage=({data})=>{
 if(!started){started=true;if(!data||Object.keys(data).sort().join()!=='check,type'||data.type!=='init'||!['literal','cosine'].includes(data.check))return self.postMessage({type:'unavailable'});initialize(data.check).catch(()=>self.postMessage({type:'unavailable'}));return;}
 const {id,claim,passage}=data||{};
 try{if(!inspect||called||Object.keys(data).sort().join()!=='claim,id,passage'||!Number.isSafeInteger(id)||typeof claim!=='string'||typeof passage!=='string')throw Error();called=true;const raw=inspect(claim,passage,selection);if(typeof raw!=='string'||raw.length>262144)throw Error();self.postMessage({type:'result',id,record:JSON.parse(raw)});}catch{self.postMessage({type:'unavailable',id});}
};
