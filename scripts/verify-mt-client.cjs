// Fixed entrypoint for the repository's source-bound revalidation runner.
const {spawnSync}=require('node:child_process');
const path=require('node:path');
const result=spawnSync(process.execPath,['--test','tests/mt-device-client.mjs','tests/mt-mobile-device-client.mjs'],{
 cwd:path.resolve(__dirname,'..'),stdio:'inherit',timeout:30000,
});
if(result.error||result.signal||result.status!==0)process.exitCode=1;
