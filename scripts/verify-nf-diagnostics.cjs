// Fixed inert controls for the real NF process/engine controller; no browser launch.
const {spawnSync}=require('node:child_process'),path=require('node:path');
const result=spawnSync(process.execPath,['--test','tests/nf-browser-diagnostics.cjs'],{cwd:path.resolve(__dirname,'..'),stdio:'inherit',timeout:30000});
if(result.error||result.signal||result.status!==0)process.exitCode=1;
