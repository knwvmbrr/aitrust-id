// Owned standalone build only. Shared site hooks/catalogue/main are untouched.
import {readFile,writeFile,mkdir,realpath,lstat,open,rename} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {constants} from 'node:fs';
import {createRequire} from 'node:module';
import {execFileSync} from 'node:child_process';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
const root=fileURLToPath(new URL('../',import.meta.url)),site=path.join(root,'site'),output=path.join(root,'output/verification/image-device-dist');
const same=(a,b)=>a.dev===b.dev&&a.ino===b.ino&&a.uid===b.uid&&a.mode===b.mode;
export async function prepareFixtureOutput(destination=output){
 const absolute=path.resolve(destination),parent=path.dirname(absolute);let current=path.parse(parent).root,handle=null;
 try{
  for(const part of parent.slice(current.length).split(path.sep).filter(Boolean)){
   current=path.join(current,part);let info;
   try{info=await lstat(current);}catch(error){if(error.code!=='ENOENT')throw error;await mkdir(current,{mode:0o700});info=await lstat(current);}
   if(!info.isDirectory()||info.isSymbolicLink())throw Error('Owned output unavailable');
  }
  const parentInfo=await lstat(parent);if(parentInfo.uid!==process.getuid()||parentInfo.mode&0o022)throw Error('Owned parent unavailable');
  // Exclusive creation: never empty an existing directory, even one with the
  // expected name. Preserve failed candidates for an explicit operator decision.
  await mkdir(absolute,{mode:0o700});handle=await open(absolute,constants.O_RDONLY|constants.O_DIRECTORY|constants.O_NOFOLLOW);const identity=await handle.stat();
  if(identity.uid!==process.getuid()||identity.mode&0o077)throw Error('Owned directory unavailable');
  return {directory:absolute,async check(){if(!handle||!same(await handle.stat(),identity)||!same(await lstat(absolute),identity))throw Error('Owned directory changed');},async close(){const owned=handle;handle=null;await owned?.close();}};
 }catch{const owned=handle;handle=null;await owned?.close();throw Error('Owned fixture output unavailable. Existing output was not cleared.');}
}
async function main(){
 const owned=await prepareFixtureOutput();
 try{
  const python=process.env.AITRUST_BUILD_PYTHON||'python3';
  execFileSync(python,['-B',path.join(root,'scripts/build-image-metadata-device.py')],{stdio:'inherit',timeout:15000});
  // Only the ordinary existing PS payload/ignored manifest is generated for the
  // unchanged real PS component used as a separate isolation control.
  execFileSync(python,['-B',path.join(root,'scripts/build-device-detector.py')],{stdio:'inherit',timeout:15000});
  const require=createRequire(path.join(site,'package.json')),{build}=await import(pathToFileURL(require.resolve('vite')));await owned.check();
  await build({root:site,configFile:path.join(site,'vite.config.js'),publicDir:path.join(site,'public'),build:{outDir:output,emptyOutDir:false,rollupOptions:{input:path.join(site,'image-metadata-fixture.html')}}});
  await owned.check();await rename(path.join(output,'image-metadata-fixture.html'),path.join(output,'index.html'));
  const policyPath=path.join(root,'sbom/nested-runtime/pyodide-wasm-release.json'),policyRaw=await readFile(policyPath),hash=b=>createHash('sha256').update(b).digest('hex');
  if(hash(policyRaw)!=='fda0196c527b3920744261e27ac93cb71637ad36cf127e450aeaf49f425dd86f')throw Error('Runtime policy changed');
  const policy=JSON.parse(policyRaw),runtime=await realpath(path.join(site,'node_modules/pyodide')),target=path.join(output,'device/runtime-314.0.7');await mkdir(target,{recursive:true});
  for(const [name,pin]of Object.entries(policy.runtime_members)){
   const file=await open(path.join(runtime,name),constants.O_RDONLY|constants.O_NOFOLLOW|constants.O_NONBLOCK);let bytes;
   try{
    const before=await file.stat();if(!before.isFile()||before.size!==pin.bytes||before.size>12000000)throw Error('Runtime unavailable');
    const parts=[];let size=0;while(true){const part=Buffer.alloc(Math.min(65536,pin.bytes+1-size));const {bytesRead}=await file.read(part,0,part.length,null);if(!bytesRead)break;size+=bytesRead;if(size>pin.bytes)throw Error('Runtime size changed');parts.push(part.subarray(0,bytesRead));}bytes=Buffer.concat(parts,size);
    const after=await file.stat();if(before.ino!==after.ino||before.size!==after.size||before.mtimeMs!==after.mtimeMs||bytes.length!==pin.bytes||hash(bytes)!==pin.sha256)throw Error('Runtime changed');
   }finally{await file.close();}
   await owned.check();await writeFile(path.join(target,name),bytes,{flag:'wx'});
  }
  await owned.check();await mkdir(path.join(output,'reference'),{recursive:true});await writeFile(path.join(output,'reference/image-device-guide.md'),await readFile(path.join(root,'docs/image-device-guide.md')),{flag:'wx'});
  await owned.check();console.log(JSON.stringify({state:'STANDALONE_IMAGE_FIXTURE_BUILT',shared_site_hooks_changed:false,runtime_files:5,runtime_execution:false}));
 }finally{await owned.close();}
}
if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url))main().catch(()=>{console.error('Standalone image fixture build unavailable; owned partial output may remain.');process.exitCode=1;});
