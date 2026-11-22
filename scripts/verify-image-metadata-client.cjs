// Fixed bounded entrypoint for source-bound image privacy/lifecycle controls.
'use strict';
const {spawnSync}=require('node:child_process');
const path=require('node:path');
const result=spawnSync(process.execPath,['--test','tests/image-metadata-client.mjs','tests/image-fixture-output.mjs','tests/fa-image-main-integration.cjs'],{
 cwd:path.resolve(__dirname,'..'),stdio:'inherit',timeout:30000,
});
if(result.error||result.signal||result.status!==0)process.exitCode=1;
