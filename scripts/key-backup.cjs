#!/usr/bin/env node
'use strict';
const fs=require('node:fs'),path=require('node:path'),readline=require('node:readline');
const custody=require('../protocol/key-backup.cjs'),receipts=require('../protocol/receipts.cjs');
const {read,write}=require('./receipt.cjs');
const root=path.resolve(__dirname,'..');
function destination(name) {
 const file=path.resolve(name),parent=path.dirname(file);
 if (file === root || file.startsWith(root+path.sep)) throw Error('Backups and keys stay outside this repository');
 if (fs.existsSync(file) || fs.realpathSync(parent)!==parent) throw Error('Existing file or symlink directory');
 const stat=fs.statSync(parent);
 if (!stat.isDirectory() || stat.uid!==process.getuid() || (stat.mode&0o077)!==0) throw Error('Use an owner-only directory');
 return file;
}
function hidden(prompt, input=process.stdin, output=process.stderr) {
 if (!input.isTTY || typeof input.setRawMode!=='function') return Promise.reject(Error('Interactive terminal required'));
 return new Promise((resolve,reject)=>{
  let value='',finished=false; const previous=input.isRaw;
  function finish(error) {
   if(finished)return; finished=true; clearTimeout(timer);
   input.removeListener('keypress',keypress); input.removeListener('end',ended);
   input.setRawMode(Boolean(previous)); input.pause(); output.write('\n');
   if(error)reject(error);else resolve(Buffer.from(value,'utf8')); value='';
  }
  function keypress(text,key={}) {
   if(key.ctrl || key.name==='escape')return finish(Error('Cancelled'));
   if(key.name==='return' || key.name==='enter')return finish();
   if(key.name==='backspace'){value=Array.from(value).slice(0,-1).join('');return;}
   if(key.name==='tab' || key.sequence?.startsWith('\x1b'))return;
   if(typeof text==='string' && !/[\u0000-\u001f\u007f]/u.test(text))value+=text;
   if(Buffer.byteLength(value)>1024)finish(Error('Password too long'));
  }
  const ended=()=>finish(Error('Input ended'));
  const timer=setTimeout(()=>finish(Error('Password input timed out')),300000);
  readline.emitKeypressEvents(input); input.setRawMode(true);
  input.on('keypress',keypress); input.once('end',ended); input.resume();
  // Show readiness only after echo is disabled and handlers are installed.
  output.write(prompt);
 });
}
async function secret(file, confirmation) {
 if(file){const raw=read(file,true,1024);try{return custody.password(raw);}catch(error){raw.fill(0);throw error;}}
 let pass,again;
 try {
  pass=await hidden(confirmation?'Choose a strong backup password (hidden): ':'Backup password (hidden): ');
  custody.password(pass);
  if(confirmation){again=await hidden('Repeat the same password (hidden): ');if(!pass.equals(again))throw Error('Passwords differ');}
  return pass;
 }catch(error){if(pass)pass.fill(0);throw error;}finally{if(again)again.fill(0);}
}
async function main(args) {
 const [command,...rest]=args;
 if(!command || command==='help') {
  console.log('AI Trust ID · optional offline key backup\n\nbackup <private.pem> <new-backup.json>\ncheck <backup.json> <separately-saved-public.pem>\nrestore <backup.json> <separately-saved-public.pem> <new-private.pem>\n\nPasswords are entered twice for backup and once for recovery, with no echo.\nFor owner-controlled scripts append: --password-file <owner-only-file>\nNo password arguments, network, cloud recovery or key replacement. Keep keys and\nbackups in a private directory outside the repository. A forgotten password cannot\nbe recovered; restoring a key does not revoke stolen copies. See docs/key-recovery.md.');return 0;
 }
 let passwordFile;const marker=rest.indexOf('--password-file');
 if(marker!==-1){if(marker!==rest.length-2)throw Error('Invalid password-file argument');passwordFile=rest[marker+1];rest.splice(marker);}
 const counts={backup:2,check:2,restore:3};
 if(!Object.hasOwn(counts,command)||rest.length!==counts[command])throw Error('Unsupported command');
 let pass,key,privateInput;
 try {
  if(command==='backup') {
   const file=destination(rest[1]); privateInput=read(rest[0],true,4096); custody.pem(privateInput,true);
   pass=await secret(passwordFile,true);
   write(file,receipts.bytes(custody.backup(privateInput,pass))+'\n',true);
   console.log('Encrypted backup saved locally. Save your password separately and practice recovery.');return 0;
  }
  const file=command==='restore'?destination(rest[2]):null;
  const backup=custody.parse(read(rest[0],true,custody.LIMIT)),publicPem=read(rest[1],false,4096);
  custody.pem(publicPem,false);pass=await secret(passwordFile,false);
  key=custody.restore(backup,pass,publicPem);
  if(file){write(file,key,true);console.log('Signing key restored locally. Its separately saved public key matches. Stolen copies are not revoked.');}
  else console.log('Backup opens and matches your separately saved public key. No private key file was written.');
  return 0;
 }finally{if(pass)pass.fill(0);if(key)key.fill(0);if(privateInput)privateInput.fill(0);}
}
if(require.main===module)main(process.argv.slice(2)).then(code=>{process.exitCode=code;}).catch(()=>{
 console.error('Key operation refused: password, trust, input, permissions, destination or cancellation. No key was accepted.');process.exitCode=2;
});
module.exports=Object.freeze({main,hidden,destination});
