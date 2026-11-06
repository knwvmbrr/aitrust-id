'use strict';
// Pipe-only reuse of the existing canonical receipt signature implementation.
const fs=require('node:fs'),crypto=require('node:crypto'),r=require('../protocol/receipts.cjs');
try {
 const buffer=Buffer.alloc(262145);let length=0;
 while(length<buffer.length){const n=fs.readSync(0,buffer,length,buffer.length-length,null);if(!n)break;length+=n;}
 if(length>262144)throw Error('limit');const raw=buffer.subarray(0,length);
 const q=r.parse(raw);
 if(Object.keys(q).sort().join('|')!=='key|operation|record'||!['sign','verify','practice-keygen'].includes(q.operation))throw Error('request');
 if(q.operation==='practice-keygen'){
  if(q.key!==null||q.record!==null)throw Error('request');
  const pair=crypto.generateKeyPairSync('ed25519');
  fs.writeFileSync(1,r.bytes({private_key:pair.privateKey.export({type:'pkcs8',format:'pem'}),public_key:pair.publicKey.export({type:'spki',format:'pem'})}));
  process.exit(0);
 }
 if(typeof q.key!=='string'||q.key.length>8192)throw Error('key');
 const key=q.operation==='sign'?crypto.createPrivateKey(q.key):crypto.createPublicKey(q.key);
 if(key.asymmetricKeyType!=='ed25519')throw Error('algorithm');
 const value=q.operation==='sign'?r.sign(q.record,q.key):r.verify(q.record,q.key);
 fs.writeFileSync(1,r.bytes(value));
} catch {process.stderr.write('Agent signature operation unavailable.\n');process.exitCode=2;}
