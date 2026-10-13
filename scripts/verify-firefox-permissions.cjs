// Execute the Firefox-only consent tests with this Node runtime; no owner browser.
const {spawnSync}=require('node:child_process'),path=require('node:path');
const result=spawnSync(process.execPath,['--test','tests/firefox-permissions.cjs'],{
  cwd:path.resolve(__dirname,'..'),stdio:'inherit',shell:false});
if(result.error){console.error('Firefox permission checks unavailable.');process.exitCode=1;}
else process.exitCode=result.status===0?0:1;
