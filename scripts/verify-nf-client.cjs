// Fixed source-bound entrypoint: prepare owned fixture, then strict client,
// canonical browser and native input-path controls. No outside service or input.
const {spawnSync}=require('node:child_process');
const path=require('node:path');
const commands=[['scripts/build-nf-device-fixture.mjs',90000],['--test','tests/nf-device-client.mjs',30000],['scripts/verify-nf-device.cjs',180000],['scripts/verify-nf-input.cjs',120000]];
for(const command of commands){
 const timeout=command.at(-1),args=command.slice(0,-1);
 const result=spawnSync(process.execPath,args,{cwd:path.resolve(__dirname,'..'),stdio:'inherit',timeout});
 if(result.error||result.signal||result.status!==0){process.exitCode=1;break;}
}
