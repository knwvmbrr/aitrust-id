// Owned disposable paths: no private evidence or real browser needed.
const fs=require('node:fs'),os=require('node:os'),path=require('node:path'),assert=require('node:assert/strict');
const {receiptPath}=require('./verify-replay-export.cjs');
const root=fs.mkdtempSync(path.join(os.tmpdir(),'aitrust-replay-input-'));
try {
 fs.mkdirSync(path.join(root,'runs'));
 const file=path.join(root,'runs','fixture.json');fs.writeFileSync(file,'{}');
 assert.equal(receiptPath('runs/fixture.json',root),file);
 let refused=0;
 for(const value of [null,'/private/credential.json','../credential.json','runs/../credential.json','runs/fixture.json/other','runs/not-there.json']){
  assert.throws(()=>receiptPath(value,root));refused++;
 }
 fs.symlinkSync(file,path.join(root,'runs','linked.json'));
 assert.throws(()=>receiptPath('runs/linked.json',root));refused++;
 fs.writeFileSync(file,Buffer.alloc(2000001));
 assert.throws(()=>receiptPath('runs/fixture.json',root));refused++;
 console.log(JSON.stringify({pass:true,public_receipt_accepted:true,unsafe_receipts_refused:refused}));
} finally {fs.rmSync(root,{recursive:true,force:true});}
