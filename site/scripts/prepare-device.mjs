import {execFileSync} from 'node:child_process';
import {readFile,copyFile,mkdir} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
const root=fileURLToPath(new URL('../../',import.meta.url));
execFileSync(process.env.AITRUST_BUILD_PYTHON||'python3',[root+'scripts/build-device-detector.py'],{stdio:'inherit'});
const pkg=JSON.parse(await readFile(new URL('../node_modules/pyodide/package.json',import.meta.url)));
if(pkg.version!=='314.0.7')throw Error('Unexpected runtime version');
const directory=new URL('../public/device/runtime-314.0.7/',import.meta.url);
await mkdir(directory,{recursive:true});
for(const file of ['pyodide.mjs','pyodide.asm.mjs','pyodide.asm.wasm','python_stdlib.zip','pyodide-lock.json'])
 await copyFile(new URL('../node_modules/pyodide/'+file,import.meta.url),new URL(file,directory));
