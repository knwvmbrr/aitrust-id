import manifest from './device-manifest.json';
let check;
async function initialize(){
 const base='/device/runtime-'+manifest.runtime+'/';
 const {loadPyodide}=await import(/* @vite-ignore */ base+'pyodide.mjs');
 const py=await loadPyodide({indexURL:base,stdout:()=>{},stderr:()=>{}});
 const response=await fetch(manifest.path,{cache:'no-cache'});
 if(!response.ok)throw Error('Method unavailable');
 const bytes=await response.arrayBuffer();
 const hash=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes)),x=>x.toString(16).padStart(2,'0')).join('');
 if(hash!==manifest.bundle_sha256)throw Error('Method mismatch');
 // Only a shipped, hash-checked method is executed. Input is passed as data.
 py.runPython(new TextDecoder('utf-8',{fatal:true}).decode(bytes));
 check=py.globals.get('check_device');
 self.postMessage({type:'ready'});
}
self.onmessage=event=>{
 const {id,text}=event.data||{};
 try {
  if(!check||typeof text!=='string'||!Number.isSafeInteger(id))throw Error('Invalid check');
  const record=JSON.parse(check(text));
  if(record.models?.[0]?.sha256!==manifest.method_sha256)throw Error('Identity mismatch');
  self.postMessage({type:'result',id,record:{...record,device_runtime:manifest.runtime,bundle_sha256:manifest.bundle_sha256}});
 }catch{self.postMessage({type:'error',id});}
};
initialize().catch(()=>self.postMessage({type:'unavailable'}));
