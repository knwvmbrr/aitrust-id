import assert from 'node:assert/strict';
import {mkdtemp,mkdir,writeFile,readFile,symlink,realpath,rename,rm,stat} from 'node:fs/promises';
import {tmpdir} from 'node:os';import path from 'node:path';
import {prepareFixtureOutput} from '../scripts/build-image-metadata-fixture.mjs';
const root=await realpath(await mkdtemp(path.join(tmpdir(),'aitrust-owned-image-fixture-')));
try{
 const existing=path.join(root,'existing');await mkdir(existing);await writeFile(path.join(existing,'marker'),'KEEP');await assert.rejects(prepareFixtureOutput(existing));assert.equal(await readFile(path.join(existing,'marker'),'utf8'),'KEEP');
 const target=path.join(root,'target');await mkdir(target);await writeFile(path.join(target,'marker'),'PRESERVE');await symlink(target,path.join(root,'linked'));await assert.rejects(prepareFixtureOutput(path.join(root,'linked','output')));assert.equal(await readFile(path.join(target,'marker'),'utf8'),'PRESERVE');
 const selected=path.join(root,'owned'),owned=await prepareFixtureOutput(selected);assert.equal((await stat(selected)).mode&0o777,0o700);await owned.check();await rename(selected,path.join(root,'retained'));await mkdir(selected);await assert.rejects(owned.check());await owned.close();await owned.close();
 console.log(JSON.stringify({pass:true,groups:3,preexisting_output_preserved:true,linked_parent_refused:true,owned_identity_drift_refused:true,no_Vite_or_browser_executed:true}));
}finally{await rm(root,{recursive:true,force:true});}
