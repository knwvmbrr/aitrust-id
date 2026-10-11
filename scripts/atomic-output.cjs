/* Internal publisher. Callers validate their own path and private-directory policy. */
'use strict';
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
function publish(file,raw,io=fs) {
 const temporary=path.join(path.dirname(file),'.aitrust-output-'+crypto.randomUUID());
 let fd,created=false,published=false,identity;
 try {
  fd=io.openSync(temporary,fs.constants.O_WRONLY|fs.constants.O_CREAT|fs.constants.O_EXCL|fs.constants.O_NOFOLLOW,0o600);
  created=true;identity=io.fstatSync(fd);io.fchmodSync(fd,0o600);
  io.writeFileSync(fd,raw);io.fsyncSync(fd);io.closeSync(fd);fd=undefined;
  // Complete, synced bytes become visible atomically without overwriting a
  // concurrently created file or dangling symlink.
  io.linkSync(temporary,file);published=true;
  io.unlinkSync(temporary);created=false;
 }catch(error){
  if(fd!==undefined){try{io.closeSync(fd);}catch{}fd=undefined;}
  let cleanupFailed=false;
  for(const target of [published?file:null,created?temporary:null].filter(Boolean)){
   try{const stat=io.lstatSync(target);if(!identity||stat.dev!==identity.dev||stat.ino!==identity.ino)throw Error('Output identity changed');io.unlinkSync(target);}
   catch(cleanupError){if(cleanupError.code!=='ENOENT')cleanupFailed=true;}
  }
  if(cleanupFailed){const refused=Error('Private output cleanup requires owner inspection');refused.code='AITRUST_PRIVATE_CLEANUP';throw refused;}
  throw error;
 }
}
module.exports=Object.freeze({publish});
