/* Build an unpublished MT-only test surface; never alter the shared catalogue. */
import {readFile,writeFile,mkdir,copyFile,cp} from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {execFileSync} from 'node:child_process';
import {build} from '../site/node_modules/vite/dist/node/index.js';
import tailwind from '../site/node_modules/@tailwindcss/vite/dist/index.mjs';
const root=fileURLToPath(new URL('../',import.meta.url));
execFileSync(process.env.AITRUST_VERIFY_PYTHON||'python3',[root+'scripts/build-mt-device.py'],{stdio:'ignore'});
const source=path.join(root,'output/mt-device-fixture-source'),destination=path.join(root,'output/mt-device-fixture');
await mkdir(source,{recursive:true});
await writeFile(path.join(source,'index.html'),'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>MT preview engineering fixture</title></head><body><div id="root"></div><script type="module" src="./main.jsx"></script></body></html>');
await writeFile(path.join(source,'main.jsx'),`import React,{useState} from 'react';import {createRoot} from 'react-dom/client';import {MTExplorerSlot,createMTExplorerSlot} from '../../site/src/MTExplorerSlot.jsx';import './styles.css';
const FailedImport=createMTExplorerSlot(()=>Promise.reject(Error('Synthetic MT import failure')));const FailedRender=createMTExplorerSlot(()=>Promise.resolve({MTExplorer:()=>{throw Error('Synthetic MT render failure');}}));
function Fixture(){const [open,setOpen]=useState(true),[mode,setMode]=useState('normal');const Slot=mode==='import'?FailedImport:mode==='render'?FailedRender:MTExplorerSlot;return <main className="mx-auto max-w-2xl p-4"><h1 className="text-xl font-semibold">MT preview engineering fixture</h1>{open&&<Slot/>}<button className="mt-4 min-h-11 rounded-lg border border-line p-3" onClick={()=>setOpen(!open)}>{open?'Unmount preview':'Mount preview'}</button><button className="mt-4 min-h-11 rounded-lg border border-line p-3" onClick={e=>e.currentTarget.textContent='Other tool remains available'}>Other tool probe</button><button className="mt-4 min-h-11 rounded-lg border border-line p-3" onClick={()=>setMode('import')}>Import failure probe</button><button className="mt-4 min-h-11 rounded-lg border border-line p-3" onClick={()=>setMode('render')}>Render failure probe</button><button className="mt-4 min-h-11 rounded-lg border border-line p-3" onClick={()=>setMode('normal')}>Restore preview</button></main>;}createRoot(document.getElementById('root')).render(<Fixture/>);`);
await writeFile(path.join(source,'styles.css'),'@import "../../site/src/styles.css";\n@source "../../site/src/MTExplorer.jsx";\n@source "../../site/src/MTExplorerSlot.jsx";\n');
await build({configFile:false,root:source,publicDir:path.join(root,'site/public'),plugins:[tailwind()],
 resolve:{alias:{react:path.join(root,'site/node_modules/react'),'react-dom':path.join(root,'site/node_modules/react-dom')}},
 build:{outDir:destination,emptyOutDir:true}});
const pkg=JSON.parse(await readFile(path.join(root,'site/node_modules/pyodide/package.json')));
if(pkg.version!=='314.0.7')throw Error('Unreviewed MT runtime');
const runtime=path.join(destination,'device/runtime-314.0.7');await mkdir(runtime,{recursive:true});
for(const name of ['pyodide.mjs','pyodide.asm.mjs','pyodide.asm.wasm','python_stdlib.zip','pyodide-lock.json'])await copyFile(path.join(root,'site/node_modules/pyodide',name),path.join(runtime,name));
console.log(JSON.stringify({fixture:destination,published_route:false,runtime:pkg.version}));
