#!/usr/bin/env node
'use strict';
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),{execFileSync}=require('node:child_process');
const receipts=require('../protocol/receipts.cjs');
const choice=require('../protocol/author-choice.cjs');
const atomic=require('./atomic-output.cjs');
const root=path.resolve(__dirname,'..');
function read(name,privateKey=false,limit=262144){
 const file=path.resolve(name),fd=fs.openSync(file,fs.constants.O_RDONLY|fs.constants.O_NOFOLLOW|fs.constants.O_NONBLOCK);
 try{const stat=fs.fstatSync(fd);if(!stat.isFile()||stat.size>limit||(privateKey&&(stat.uid!==process.getuid()||(stat.mode&0o077)!==0)))throw Error('File permissions or size unsupported');
  const raw=Buffer.alloc(limit+1);let size=0;
  while(size<raw.length){const n=fs.readSync(fd,raw,size,raw.length-size,null);if(!n)break;size+=n;}
  if(size>limit)throw Error('File grew past its read limit');return raw.subarray(0,size);
 }finally{fs.closeSync(fd);}
}
function write(name,raw,privateFile=false){
 const file=path.resolve(name),parent=path.dirname(file);
 if(privateFile&&(file===root||file.startsWith(root+path.sep)))throw Error('Private keys must stay outside the repository');
 if(fs.realpathSync(parent)!==parent)throw Error('Symlink output directory refused');
 const stat=fs.statSync(parent);if(privateFile&&(stat.uid!==process.getuid()||(stat.mode&0o077)!==0))throw Error('Use an owner-only directory for keys');
 atomic.publish(file,raw);
}
function schema(value){
 const python=process.env.AITRUST_VERIFY_PYTHON||'python3';
 execFileSync(python,['-c','import json,sys;from protocol.assertions import validator;validator().validate(json.load(sys.stdin))'],{cwd:root,input:JSON.stringify(value),stdio:['pipe','ignore','pipe']});
}
function main(args){
 const [command,...a]=args;
 if(!command||command==='help'){
  console.log('AI Trust ID · optional offline receipts\n\nkeygen <Ed25519|ECDSA-P256-SHA256> <new-private.pem> <new-public.pem>\nissue <artifact.txt> <observation.json> <private.pem> <new-receipt.json>\nverify <receipt.json> <pinned-public.pem> <artifact.txt>\nsign-assertion <assertion.json> <private.pem> <new-signed.json>\nverify-assertion <signed.json> <pinned-public.pem>\n\nKeys need an existing owner-only directory outside this repository. No network, payment, automatic receipt, authorship or certification claim. Verification reports unchecked revocation explicitly.');return;
 }
 if(command==='keygen'&&a.length===3){
  const alg=a[0];if(!['Ed25519','ECDSA-P256-SHA256'].includes(alg))throw Error('Unsupported algorithm');
  const {privateKey,publicKey}=crypto.generateKeyPairSync(alg==='Ed25519'?'ed25519':'ec',alg==='Ed25519'?{}:{namedCurve:'prime256v1'});
  // Refuse existing destinations before either write; never overwrite a key.
  for(const name of a.slice(1))if(fs.existsSync(name))throw Error('Choose new key destinations');
  write(a[1],privateKey.export({type:'pkcs8',format:'pem'}),true);
  try{write(a[2],publicKey.export({type:'spki',format:'pem'}));}catch(e){fs.unlinkSync(a[1]);throw e;}
  console.log('New local key files created. Public-key trust must be established separately.');return;
 }
 if(command==='issue'&&a.length===4){
  if(!choice.authorize(choice.profile(),'issue',true))throw Error('Receipt declined');
  const artifact=read(a[0],false,80000),observation=receipts.parse(read(a[1]));
  const expected=receipts.hash(read(path.join(root,'tools/composition/core.cjs')));
  if(observation.source_sha256!==expected)throw Error('Observation method source unavailable or changed');
  const record=receipts.receipt(artifact,observation,Math.floor(Date.now()/1000));
  write(a[3],receipts.bytes(receipts.sign(record,read(a[2],true)))+'\n');
  console.log('Optional receipt created locally. It proves neither authorship nor an independent timestamp.');return;
 }
 if(command==='verify'&&a.length===3){
  const result=receipts.inspectReceipt(receipts.parse(read(a[0])),read(a[1]),read(a[2],false,80000),Math.floor(Date.now()/1000));
  console.log(JSON.stringify(result));return result.expiry==='within_declared_window'?0:3;
 }
 if(command==='sign-assertion'&&a.length===3){
  const value=receipts.parse(read(a[0]));schema(value);
  write(a[2],receipts.bytes(receipts.sign(value,read(a[1],true)))+'\n');console.log('Detached assertion signature created; truth remains unverified.');return;
 }
 if(command==='verify-assertion'&&a.length===2){
  const value=receipts.verify(receipts.parse(read(a[0])),read(a[1]));schema(value);
  console.log(JSON.stringify({record_integrity:'verified_under_pinned_key',assertion_schema:'valid',truth:'unestablished',revocation:'unchecked',certification:false}));return;
 }
 throw Error('Unsupported command. Run: node scripts/receipt.cjs help');
}
if(require.main===module){try{process.exitCode=main(process.argv.slice(2))||0;}catch(error){console.error(error.code==='AITRUST_PRIVATE_CLEANUP'?'Receipt operation refused. Temporary output cleanup failed; inspect your selected folder before retrying.':'Receipt operation refused: invalid input, trust, permissions or unavailable prerequisites. No valid verdict issued.');process.exitCode=2;}}
module.exports={main,read,write};
