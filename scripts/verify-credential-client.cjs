// Source-bound entry point for credential preview lifecycle/refusal controls.
const {spawnSync}=require('node:child_process');
const path=require('node:path');
const r=spawnSync(process.execPath,['--test','tests/credential-device-client.mjs'],{cwd:path.resolve(__dirname,'..'),stdio:'inherit',timeout:30000});
if(r.error||r.signal||r.status!==0)process.exitCode=1;
