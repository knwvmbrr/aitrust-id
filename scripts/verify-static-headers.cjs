'use strict';
const {spawnSync}=require('node:child_process'),path=require('node:path');
const root=path.resolve(__dirname,'..');
const result=spawnSync(process.execPath,['--test','tests/static-headers.cjs'],{cwd:root,stdio:'inherit',shell:false});
process.exitCode=typeof result.status==='number'?result.status:1;
