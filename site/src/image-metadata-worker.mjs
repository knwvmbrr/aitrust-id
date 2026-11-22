const PARSERS={"png":{"source_sha256":"addd35028617f2d5c2cd01dc19106cec9946686cfe35139beb923af3973d6994","projection_sha256":"59c5a09534b8ff7ff0e4598024a02a4a0e84447dfee408ce37b2b9c4df14c6f1","projection_bytes":12113,"profile":"png-metadata-preflight/1.0.0"},"jpeg":{"source_sha256":"c7e8fcb58acd2087a35c886a32b7df1fa390c74c52c023e9b137bdf1dd90872a","projection_sha256":"2670acac47e6cd567ed46643b905b202491d99bc12d4c490815044422597a7f2","projection_bytes":13607,"profile":"jpeg-metadata-observation/1.0.0"}},RUNTIME={"pyodide.mjs":{"bytes":17931,"sha256":"6f1d60f7bf529beb300f0f47983c921d3982363640ba20af0e38efdddbc66109"},"pyodide.asm.mjs":{"bytes":1250344,"sha256":"f7cdc8ece80678ceb712f8e65ebe6d3a83203a180c399865f49612a051693635"},"pyodide.asm.wasm":{"bytes":9598218,"sha256":"cc36e3cab04fdfc9a63ff13eb52eae2b911bf46c025cc7b281f394bd3de1d5e6"},"python_stdlib.zip":{"bytes":2545637,"sha256":"fa1957e5777068fc4f7437f96d860ae2fbe9c19732ba06c84e004ec16dd7dd7a"},"pyodide-lock.json":{"bytes":119077,"sha256":"5dc2fc119108bc148c7457dc86e7675b5c87e1cafd420b9c34c1eaef7b36c010"}};

let inspect,py;
const sha=async raw=>Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',raw)),v=>v.toString(16).padStart(2,'0')).join('');
const exact=(value,keys)=>value&&Object.getPrototypeOf(value)===Object.prototype&&Object.keys(value).sort().join()===keys.slice().sort().join();
async function bounded(url,limit){
 const response=await fetch(url,{cache:'no-cache'});if(!response.ok||Number(response.headers.get('content-length'))>limit)throw Error('Unavailable');
 const reader=response.body?.getReader();if(!reader)throw Error('Unavailable');const chunks=[];let length=0;
 try{while(true){const {done,value}=await reader.read();if(done)break;length+=value.length;if(length>limit)throw Error('Unavailable');chunks.push(value);}}
 catch(e){await reader.cancel();throw e;}finally{reader.releaseLock();}
 const result=new Uint8Array(length);let offset=0;for(const chunk of chunks){result.set(chunk,offset);offset+=chunk.length;}return result;
}
async function initialize(){
 const manifest=JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(await bounded('./manifest.json',65536)));
 if(manifest.format!=='image-metadata-device-manifest/v1'||manifest.source_commit!=='8e1b1a23a1bef0659bf1ec567ceef647b5cd76a5'||manifest.runtime!=='314.0.7'||manifest.runtime_path!=='/device/runtime-314.0.7/'||JSON.stringify(manifest.parsers)!==JSON.stringify(PARSERS)||JSON.stringify(manifest.runtime_files)!==JSON.stringify(RUNTIME)||!/^method-[a-f0-9]{64}\.json$/.test(manifest.bundle))throw Error('Unavailable');
 for(const [name,pin]of Object.entries(RUNTIME)){const bytes=await bounded(manifest.runtime_path+name,pin.bytes);if(bytes.length!==pin.bytes||await sha(bytes)!==pin.sha256)throw Error('Unavailable');}
 const bytes=await bounded(manifest.bundle,200000);if(bytes.length!==manifest.bundle_bytes||await sha(bytes)!==manifest.bundle_sha256)throw Error('Unavailable');
 const bundle=JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(bytes));if(!exact(bundle,['format','files'])||bundle.format!=='image-metadata-projected-python/v1'||!exact(bundle.files,['png','jpeg']))throw Error('Unavailable');
 for(const kind of ['png','jpeg']){const text=bundle.files[kind];if(typeof text!=='string')throw Error('Unavailable');const raw=new TextEncoder().encode(text);if(raw.length!==PARSERS[kind].projection_bytes||await sha(raw)!==PARSERS[kind].projection_sha256)throw Error('Unavailable');}
 const {loadPyodide}=await import('/device/runtime-314.0.7/pyodide.mjs');py=await loadPyodide({indexURL:new URL(manifest.runtime_path,import.meta.url).href,stdout:()=>{},stderr:()=>{}});
 py.FS.mkdirTree('/image-source');for(const kind of ['png','jpeg'])py.FS.writeFile('/image-source/image_'+kind+'.py',new TextEncoder().encode(bundle.files[kind]));
 py.runPython(`import sys,json\nsys.path.insert(0,'/image-source')\nimport image_png,image_jpeg\ndef _inspect_image(kind,buffer):\n raw=bytes(buffer)\n m=image_png if kind=='png' else image_jpeg\n try:r=m.inspect_bytes(raw)\n except m.ImageError as e:r=m.unavailable(e.reason,raw)\n m.validate_record(r,raw)\n return json.dumps(r,sort_keys=True,separators=(',',':'))\n`);
 inspect=py.globals.get('_inspect_image');self.postMessage({type:'ready'});
}
self.onmessage=({data})=>{
 const id=data?.id;let buffer;
 try{
  if(!inspect||!exact(data,['id','kind','bytes'])||!Number.isSafeInteger(id)||id<1||!['png','jpeg'].includes(data.kind)||!(data.bytes instanceof ArrayBuffer)||data.bytes.byteLength<1||data.bytes.byteLength>10485760)throw Error('Unavailable');
  buffer=py.toPy(new Uint8Array(data.bytes));const raw=inspect(data.kind,buffer);if(typeof raw!=='string'||new TextEncoder().encode(raw).length>8192)throw Error('Unavailable');
  self.postMessage({type:'result',id,record:{format:'image-metadata-device-record/v1',kind:data.kind,source_sha256:PARSERS[data.kind].source_sha256,projection_sha256:PARSERS[data.kind].projection_sha256,record:JSON.parse(raw)}});
 }catch{self.postMessage({type:'unavailable',id});}finally{buffer?.destroy();}
};
initialize().catch(()=>self.postMessage({type:'unavailable'}));
