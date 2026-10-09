// Same contract for npm callers, local builds and full-history CI.
const {spawnSync}=require('node:child_process');
const path=require('node:path');
const result=spawnSync(process.env.AITRUST_CHANGELOG_PYTHON||'python3',[path.join(__dirname,'verify-changelog.py'),...process.argv.slice(2)],{stdio:'inherit'});
if(result.error){console.error(result.error.message);process.exit(1);}
process.exit(result.status??1);
