#!/usr/bin/env node
'use strict';
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const {read,write}=require('./receipt.cjs');
const PROFILE='loopback-response/p256-sha256/v1';
function profile(privateKey){
 if(privateKey.asymmetricKeyType!=='ec'||privateKey.asymmetricKeyDetails.namedCurve!=='prime256v1')throw Error('P-256 key required');
 const jwk=crypto.createPublicKey(privateKey).export({format:'jwk'});
 const raw=Buffer.concat([Buffer.from([4]),Buffer.from(jwk.x,'base64url'),Buffer.from(jwk.y,'base64url')]);
 return {profile:PROFILE,public_key:raw.toString('base64url'),key_id:crypto.createHash('sha256').update(raw).digest('hex')};
}
function main(args){
 const [command,...a]=args;
 if(command==='help'||!command){console.log('Gateway response authentication\nkeygen <new-private.pem> <new-public.json>\npublic <private.pem> <new-public.json>\n\nUse an existing owner-only directory outside the repository. No overwrite or network. Public-key trust requires a separate operator handoff.');return;}
 if(!['keygen','public'].includes(command)||a.length!==2)throw Error('Invalid command');
 const paths=a.map(x=>path.resolve(x));if(paths[0]===paths[1])throw Error('Separate destinations required');
 for(const p of paths)if(fs.realpathSync(path.dirname(p))!==path.dirname(p))throw Error('Directory links refused');
 if(fs.existsSync(paths[1])||(command==='keygen'&&fs.existsSync(paths[0])))throw Error('Choose new destinations');
 const key=command==='keygen'?crypto.generateKeyPairSync('ec',{namedCurve:'prime256v1'}).privateKey:crypto.createPrivateKey(read(paths[0],true,16384));
 const publicBytes=JSON.stringify(profile(key),null,2)+'\n';let identity;
 if(command==='keygen'){write(paths[0],key.export({type:'pkcs8',format:'pem'}),true);identity=fs.lstatSync(paths[0]);}
 try{write(paths[1],publicBytes);}catch(error){
  if(identity){const now=fs.lstatSync(paths[0]);if(now.dev!==identity.dev||now.ino!==identity.ino)throw Error('Private key changed; owner inspection required');fs.unlinkSync(paths[0]);}
  throw error;
 }
 console.log(JSON.stringify({public_key_file:paths[1],key_id:profile(key).key_id,accuracy_verified:false}));
}
module.exports={main,profile};
if(require.main===module)try{main(process.argv.slice(2));}catch{console.error('Gateway key operation refused. Check private permissions, key type and new output destinations.');process.exitCode=2;}
