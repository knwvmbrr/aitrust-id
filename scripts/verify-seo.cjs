// Fixed SEO checks shared by npm, CI and source-bound revalidation.
const {spawnSync}=require('node:child_process');
const path=require('node:path');
const root=path.resolve(__dirname,'..');
for(const args of [['--test','tests/seo-metadata.mjs'],['scripts/verify-seo.mjs']]){
 const run=spawnSync(process.execPath,args,{cwd:root,stdio:'inherit',timeout:60000});
 if(run.error||run.signal||run.status!==0){process.exitCode=run.status||1;break;}
}
