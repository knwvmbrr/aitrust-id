#!/usr/bin/env node
'use strict';
const fs=require('node:fs'),path=require('node:path'),{performance}=require('node:perf_hooks'),v=require('../protocol/reviewer-attestations.cjs');
class Inputs{
 constructor(){this.fds=[];this.nodes=[];this.start=performance.now();if(!Number.isFinite(this.start))throw Error('Input clock');this.last=this.start;}
 tick(){const n=performance.now();if(!Number.isFinite(n)||n<this.last||n-this.start>5000)throw Error('Input deadline');this.last=n;}
 identity(s){return [s.dev,s.ino,s.mode,s.size,s.mtimeNs,s.ctimeNs,s.nlink].map(String).join(':');}
 open(name,directory=false){
  this.tick();if(this.fds.length>=128)throw Error('Input FD limit');
  const fd=fs.openSync(name,fs.constants.O_RDONLY|fs.constants.O_NOFOLLOW|fs.constants.O_NONBLOCK|(directory?fs.constants.O_DIRECTORY:0));this.fds.push(fd);
  const s=fs.fstatSync(fd,{bigint:true});if(directory?!s.isDirectory():!s.isFile())throw Error('Regular input required');
  const row={fd,name,before:this.identity(s),directory};this.nodes.push(row);return {fd,s};
 }
 read(name,limit){
  if(typeof name!=='string'||Buffer.byteLength(name)>4096)throw Error('Input path');
  const absolute=path.resolve(name),parts=absolute.split(path.sep).filter(Boolean);if(parts.length>32)throw Error('Input depth');
  let prefix=path.parse(absolute).root;this.open(prefix,true);
  for(const part of parts.slice(0,-1)){prefix=path.join(prefix,part);this.open(prefix,true);}
  const {fd,s}=this.open(absolute);if(s.size<0n||s.size>BigInt(limit))throw Error('Input size');
  const raw=Buffer.alloc(Number(s.size));let offset=0;
  while(offset<raw.length){this.tick();const n=fs.readSync(fd,raw,offset,Math.min(65536,raw.length-offset),null);if(!n)throw Error('Input truncated');offset+=n;}
  if(fs.readSync(fd,Buffer.alloc(1),0,1,null)!==0)throw Error('Input grew');this.check();return raw;
 }
 check(){this.tick();for(const n of this.nodes){if(this.identity(fs.fstatSync(n.fd,{bigint:true}))!==n.before||this.identity(fs.lstatSync(n.name,{bigint:true}))!==n.before)throw Error('Input changed');}}
 close(){let failed=false;while(this.fds.length){const fd=this.fds.pop();try{fs.closeSync(fd);}catch(_){failed=true;}}if(failed)throw Error('Input close failed');}
}
function main(args){
 if(args.length===1&&['help','--help','-h'].includes(args[0])){
  console.log('Inspect an explicit signed review record locally.\n\n  node scripts/reviewer-attestation.cjs verify trusted-policy.json history.json subject.txt\n\nSelect the reviewer key, subject revision, checked scope and latest known chain head independently. JSON reports signature integrity and declared lifecycle separately from unestablished human independence/accuracy. No IV tag is issued. Output includes linkable hashes and reviewer metadata: use a private terminal. No key generation, signing, upload or file writes. Exit0 active declaration;3 verified inactive;2 Unavailable.');return 0;
 }
 let result=v.unavailable('input_unavailable'),inputs;
 try{
  if(args.length!==4||args[0]!=='verify')throw Error('Unsupported invocation');inputs=new Inputs();
  const policy=inputs.read(args[1],v.MAX_POLICY),history=inputs.read(args[2],v.MAX_HISTORY),subject=inputs.read(args[3],v.MAX_SUBJECT);
  result=v.verify({subject,policy,history,now:Math.floor(Date.now()/1000)});inputs.check();
 }catch(_){result=v.unavailable('input_unavailable');}
 finally{if(inputs)try{inputs.close();}catch(_){result=v.unavailable('input_unavailable');}}
 console.log(JSON.stringify(result));return result.state==='UNAVAILABLE'?2:result.active_review?0:3;
}
if(require.main===module){try{process.exitCode=main(process.argv.slice(2));}catch(_){console.error('Review evidence Unavailable. No IV tag or human-independence verdict issued.');process.exitCode=2;}}
module.exports=Object.freeze({main,Inputs});
