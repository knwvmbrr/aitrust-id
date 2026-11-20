#!/usr/bin/env node
// Real bundled Pyodide and Android loader; this is not an Android device test.
import {readFileSync,writeFileSync} from 'node:fs';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {resolve} from 'node:path';
import {execFileSync} from 'node:child_process';
import vm from 'node:vm';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
const root=fileURLToPath(new URL('../',import.meta.url));
const assets=resolve(root,'output/android-share/assets');
const source=readFileSync(resolve(assets,'bridge.mjs'),'utf8');
const cases=JSON.parse(execFileSync(process.env.AITRUST_BUILD_PYTHON||'python3',['-B',resolve(root,'scripts/native-probe-cases.py')],{maxBuffer:4194304}));
const requests=[],originalFetch=globalThis.fetch;
let networkAttempts=0;
globalThis.fetch=async()=>{networkAttempts++;throw Error('Network forbidden in Android parity control');};
try{
 const context=vm.createContext({window:{},location:{href:pathToFileURL(resolve(assets,'index.html')).href},TextDecoder,URL,console:{log(){},warn(){},error(){}},fetch:async name=>{
  assert(['./device-manifest.json','./method.py'].includes(name));requests.push(name);
  const raw=readFileSync(resolve(assets,name));
  return {ok:true,json:async()=>JSON.parse(raw.toString()),arrayBuffer:async()=>raw.buffer.slice(raw.byteOffset,raw.byteOffset+raw.byteLength)};
 }});
 const module=new vm.SourceTextModule(source,{context,identifier:'verified-android-loader',importModuleDynamically:async name=>{
  assert.equal(name,'./runtime/pyodide.mjs');
  const actual=await import(pathToFileURL(resolve(assets,name)).href);
  // Node's runtime expects a filesystem indexURL; Android uses the same local
  // files through its intercepted HTTPS origin. Adapt only that harness path.
  const local=new vm.SyntheticModule(['loadPyodide'],function(){this.setExport('loadPyodide',options=>actual.loadPyodide({...options,indexURL:resolve(assets,'runtime')+'/'}));},{context});
  await local.link(()=>{throw Error('Unexpected import');});await local.evaluate();return local;
 }});
 await module.link(()=>{throw Error('Unexpected static import');});await module.evaluate({timeout:30000});
 assert.equal(context.window.AndroidPS.state,'ready');
 for(const row of cases){
  const expected={...row.expected,format:'ai-trust-id-android-summary/v1'};
  assert.deepEqual(JSON.parse(JSON.stringify(context.window.AndroidPS.check(row.text))),expected);
 }
 for(const text of ['', ' ', 'a'.repeat(20001)])assert.throws(()=>context.window.AndroidPS.check(text));
 assert.equal(networkAttempts,0);
 const manifest=JSON.parse(readFileSync(resolve(assets,'device-manifest.json')));
 const result={format:'ai-trust-id-android-engine-parity/v1',recorded_at:new Date().toISOString(),pass:true,actual_runtime:'Pyodide314.0.7',actual_android_loader:true,node_filesystem_indexURL_adapter:true,case_count:cases.length,invalid_input_controls:3,network_attempts:networkAttempts,method_sha256:manifest.method_sha256,bundle_sha256:manifest.bundle_sha256,loader_sha256:createHash('sha256').update(source).digest('hex'),native_android_execution:false,physical_device_evidence:false,independent_accuracy_evidence:false};
 writeFileSync(resolve(root,'output/android-share/engine-parity.json'),JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify(result,null,2));
}finally{globalThis.fetch=originalFetch;}
