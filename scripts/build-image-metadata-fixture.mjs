// Owned standalone build only. Shared site hooks/catalogue/main are untouched.
import {readFile,writeFile,mkdir,realpath,stat,open,rename} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {constants} from 'node:fs';
import {createRequire} from 'node:module';
import {execFileSync} from 'node:child_process';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
const root=fileURLToPath(new URL('../',import.meta.url)),site=path.join(root,'site'),output=path.join(root,'output/verification/image-device-dist');
const python=process.env.AITRUST_BUILD_PYTHON||'python3';
execFileSync(python,['-B',path.join(root,'scripts/build-image-metadata-device.py')],{stdio:'inherit',timeout:15000});
// Generate only the ordinary existing PS payload/ignored manifest required by
// the unchanged real PS component used as an isolation control.
execFileSync(python,['-B',path.join(root,'scripts/build-device-detector.py')],{stdio:'inherit',timeout:15000});
const require=createRequire(path.join(site,'package.json')),{build}=await import(pathToFileURL(require.resolve('vite')));
await build({root:site,configFile:path.join(site,'vite.config.js'),publicDir:path.join(site,'public'),build:{outDir:output,emptyOutDir:true,rollupOptions:{input:path.join(site,'image-metadata-fixture.html')}}});
await rename(path.join(output,'image-metadata-fixture.html'),path.join(output,'index.html'));
const policyPath=path.join(root,'sbom/nested-runtime/pyodide-wasm-release.json'),policyRaw=await readFile(policyPath),hash=b=>createHash('sha256').update(b).digest('hex');
if(hash(policyRaw)!=='fda0196c527b3920744261e27ac93cb71637ad36cf127e450aeaf49f425dd86f')throw Error('Runtime policy changed');
const policy=JSON.parse(policyRaw),runtime=await realpath(path.join(site,'node_modules/pyodide')),target=path.join(output,'device/runtime-314.0.7');await mkdir(target,{recursive:true});
for(const [name,pin]of Object.entries(policy.runtime_members)){
 const file=await open(path.join(runtime,name),constants.O_RDONLY|constants.O_NOFOLLOW|constants.O_NONBLOCK);let bytes;
 try{const before=await file.stat();if(!before.isFile()||before.size!==pin.bytes||before.size>12000000)throw Error('Runtime unavailable');const parts=[];let size=0;while(true){const part=Buffer.alloc(Math.min(65536,pin.bytes+1-size));const {bytesRead}=await file.read(part,0,part.length,null);if(!bytesRead)break;size+=bytesRead;if(size>pin.bytes)throw Error('Runtime size changed');parts.push(part.subarray(0,bytesRead));}bytes=Buffer.concat(parts,size);const after=await file.stat();if(before.ino!==after.ino||before.size!==after.size||before.mtimeMs!==after.mtimeMs||bytes.length!==pin.bytes||hash(bytes)!==pin.sha256)throw Error('Runtime changed');}finally{await file.close();}
 await writeFile(path.join(target,name),bytes,{flag:'wx'});
}
await mkdir(path.join(output,'reference'),{recursive:true});await writeFile(path.join(output,'reference/image-device-guide.md'),await readFile(path.join(root,'docs/image-device-guide.md')),{flag:'wx'});
console.log(JSON.stringify({state:'STANDALONE_IMAGE_FIXTURE_BUILT',shared_site_hooks_changed:false,runtime_files:5,runtime_execution:false}));
