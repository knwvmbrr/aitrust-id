// The deploy guard uses the explicitly selected verification environment.
const {spawnSync}=require('node:child_process'),path=require('node:path');
const root=path.resolve(__dirname,'..');
const result=spawnSync(process.env.AITRUST_VERIFY_PYTHON||'python3',
  ['scripts/verify-route-boundaries.py'],{cwd:root,stdio:'inherit',shell:false});
if(result.error){console.error('Boundary verifier unavailable; deployment refused.');process.exitCode=1;}
else process.exitCode=result.status===0?0:1;
