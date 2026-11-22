let inspect;
const hash=async bytes=>Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes)),v=>v.toString(16).padStart(2,'0')).join('');
async function bounded(url,limit){
 const response=await fetch(url,{cache:'no-cache'});if(!response.ok||Number(response.headers.get('content-length'))>limit)throw Error('Unavailable');
 const reader=response.body?.getReader();if(!reader)throw Error('Unavailable');const chunks=[];let length=0;
 try{while(true){const {done,value}=await reader.read();if(done)break;length+=value.length;if(length>limit)throw Error('Unavailable');chunks.push(value);}}
 catch(error){await reader.cancel();throw error;}finally{reader.releaseLock();}
 const bytes=new Uint8Array(length);let at=0;for(const chunk of chunks){bytes.set(chunk,at);at+=chunk.length;}return bytes;
}
async function initialize(){
 const manifest=JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(await bounded('./manifest.json',65536)));
 if(manifest.format!=='mt-choice-modal-manifest/v1'||manifest.runtime!=='314.0.7'||manifest.runtime_path!=='/device/runtime-314.0.7/'||!/^method-[a-f0-9]{64}\.json$/.test(manifest.bundle))throw Error('Unavailable');
 const runtime=['pyodide.mjs','pyodide.asm.mjs','pyodide.asm.wasm','python_stdlib.zip','pyodide-lock.json'];
 if(Object.keys(manifest.runtime_files).sort().join()!==runtime.sort().join())throw Error('Unavailable');
 for(const name of runtime){const entry=manifest.runtime_files[name];if(!Number.isSafeInteger(entry.bytes)||entry.bytes<1||entry.bytes>12000000)throw Error('Unavailable');const bytes=await bounded(manifest.runtime_path+name,entry.bytes);if(bytes.length!==entry.bytes||await hash(bytes)!==entry.sha256)throw Error('Unavailable');}
 const raw=await bounded(manifest.bundle,500000);if(raw.length!==manifest.bundle_bytes||await hash(raw)!==manifest.bundle_sha256)throw Error('Unavailable');
 const bundle=JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(raw));const expected=['tools/mt_choice_device.py','tools/choice_framing.py','tools/language_observations.py','protocol/corpus.py','protocol/normalization.py','protocol/unicode15-data.json'];
 if(bundle.format!=='mt-choice-python-sources/v1'||Object.keys(bundle).sort().join()!=='files,format'||Object.keys(bundle.files).sort().join()!==expected.sort().join()||Object.keys(manifest.sources).sort().join()!==expected.sort().join())throw Error('Unavailable');
 for(const name of expected){const value=bundle.files[name];if(typeof value!=='string')throw Error('Unavailable');const bytes=new TextEncoder().encode(value);if(bytes.length>200000||await hash(bytes)!==manifest.sources[name])throw Error('Unavailable');}
 const {loadPyodide}=await import('/device/runtime-314.0.7/pyodide.mjs');
 const py=await loadPyodide({indexURL:new URL(manifest.runtime_path,import.meta.url).href,stdout:()=>{},stderr:()=>{}});
 for(const name of expected){const file='/mt-choice-source/'+name;py.FS.mkdirTree(file.slice(0,file.lastIndexOf('/')));py.FS.writeFile(file,new TextEncoder().encode(bundle.files[name]));}
 py.runPython("import sys\nsys.path.insert(0, '/mt-choice-source')\nfrom tools.mt_choice_device import inspect_mt_choice");
 inspect=py.globals.get('inspect_mt_choice');self.postMessage({type:'ready'});
}
self.onmessage=({data})=>{
 const id=data?.id;
 try{
  if(!inspect||!data||Object.keys(data).sort().join()!=='id,request'||!Number.isSafeInteger(id)||typeof data.request!=='string'||new TextEncoder().encode(data.request).length>24000)throw Error('Unavailable');
  const raw=inspect(data.request);if(typeof raw!=='string'||raw.length>65536)throw Error('Unavailable');
  self.postMessage({type:'result',id,record:JSON.parse(raw)});
 }catch{self.postMessage({type:'unavailable',id});}
};
initialize().catch(()=>self.postMessage({type:'unavailable'}));
