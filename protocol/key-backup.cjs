/* Optional offline key custody: encrypted backup, no hosted escrow or tag claim. */
'use strict';
const crypto = require('node:crypto');
const receipts = require('./receipts.cjs');
const VERSION = 'offline-key-backup/1.0.0';
const KDF = Object.freeze({name:'scrypt', N:32768, r:8, p:1, bytes:32});
const LIMIT = 8192;
function fields(value, names) {
 if (!value || typeof value !== 'object' || Array.isArray(value) ||
     Object.keys(value).sort().join('|') !== [...names].sort().join('|')) throw Error('Unsupported fields');
}
function algorithm(key) {
 if (key.asymmetricKeyType === 'ed25519') return 'Ed25519';
 if (key.asymmetricKeyType === 'ec' && key.asymmetricKeyDetails.namedCurve === 'prime256v1') return 'ECDSA-P256-SHA256';
 throw Error('Unsupported signing key');
}
function pem(raw, privateKey) {
 if (!Buffer.isBuffer(raw) || raw.length > 4096) throw Error('Unsupported key size');
 const text = new TextDecoder('utf-8',{fatal:true}).decode(raw);
 const label = privateKey ? 'PRIVATE KEY' : 'PUBLIC KEY';
 if (!new RegExp('^-----BEGIN '+label+'-----\\n(?:[A-Za-z0-9+/=]+\\n)+-----END '+label+'-----\\n$').test(text)) throw Error('Canonical PEM required');
 const key = privateKey ? crypto.createPrivateKey(raw) : crypto.createPublicKey(raw);
 algorithm(key);
 // Byte comparison also refuses appended or noncanonical encodings.
 if (!Buffer.from(key.export({type:privateKey?'pkcs8':'spki',format:'pem'})).equals(raw)) throw Error('Noncanonical key');
 return key;
}
function fingerprint(key) {
 const pub = key.type === 'private' ? crypto.createPublicKey(key) : key;
 return receipts.hash(pub.export({type:'spki',format:'der'}));
}
function password(raw) {
 if (!Buffer.isBuffer(raw) || raw.length < 12 || raw.length > 1024) throw Error('Password length unsupported');
 const value = new TextDecoder('utf-8',{fatal:true}).decode(raw);
 if (Array.from(value).length < 12 || /[\u0000-\u001f\u007f]/u.test(value) || value.trim() !== value) throw Error('Password whitespace/control characters unsupported');
 return raw;
}
function decode(text, length) {
 if (typeof text !== 'string' || text.length !== Math.ceil(length/3)*4 || !/^(?:[A-Za-z0-9+/]{4})*(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?$/.test(text)) throw Error('Invalid encoding');
 const raw = Buffer.from(text,'base64');
 if (raw.length !== length || raw.toString('base64') !== text) throw Error('Unsupported encoded length');
 return raw;
}
function derive(pass, salt) {
 return crypto.scryptSync(password(pass),salt,32,{N:KDF.N,r:KDF.r,p:KDF.p,maxmem:64*1024*1024});
}
function header(record) {
 return {version:record.version,algorithm:record.algorithm,key_sha256:record.key_sha256,kdf:record.kdf,cipher:record.cipher};
}
function backup(privatePem, pass) {
 const key = pem(privatePem,true), salt = crypto.randomBytes(16), nonce = crypto.randomBytes(12);
 const record = {version:VERSION,algorithm:algorithm(key),key_sha256:fingerprint(key),
  kdf:{...KDF,salt:salt.toString('base64')},cipher:{name:'AES-256-GCM',nonce:nonce.toString('base64')},
  ciphertext:'',authentication_tag:''};
 const derived = derive(pass,salt), plain = key.export({type:'pkcs8',format:'der'});
 try {
  const cipher = crypto.createCipheriv('aes-256-gcm',derived,nonce,{authTagLength:16});
  cipher.setAAD(receipts.bytes(header(record)));
  record.ciphertext = Buffer.concat([cipher.update(plain),cipher.final()]).toString('base64');
  record.authentication_tag = cipher.getAuthTag().toString('base64');
  return record;
 } finally { derived.fill(0); plain.fill(0); }
}
function restore(record, pass, selectedPublicPem) {
 const selected = pem(selectedPublicPem,false);
 fields(record,['version','algorithm','key_sha256','kdf','cipher','ciphertext','authentication_tag']);
 fields(record.kdf,['name','N','r','p','bytes','salt']); fields(record.cipher,['name','nonce']);
 if (record.version !== VERSION || record.algorithm !== algorithm(selected) || record.key_sha256 !== fingerprint(selected) ||
     ['name','N','r','p','bytes'].some(k=>record.kdf[k] !== KDF[k]) || record.cipher.name !== 'AES-256-GCM') throw Error('Unsupported or untrusted backup');
 const salt=decode(record.kdf.salt,16), nonce=decode(record.cipher.nonce,12), tag=decode(record.authentication_tag,16);
 // Canonical PKCS8 lengths for the two supported algorithms, with no arbitrary allocation.
 const size = record.algorithm === 'Ed25519' ? 48 : 138;
 const encrypted=decode(record.ciphertext,size), derived=derive(pass,salt);
 let plain, partial;
 try {
  const cipher=crypto.createDecipheriv('aes-256-gcm',derived,nonce,{authTagLength:16});
  cipher.setAAD(receipts.bytes(header(record))); cipher.setAuthTag(tag);
  partial=cipher.update(encrypted); plain=Buffer.concat([partial,cipher.final()]);
  const key=crypto.createPrivateKey({key:plain,type:'pkcs8',format:'der'});
  if (algorithm(key) !== record.algorithm || fingerprint(key) !== record.key_sha256 ||
      !key.export({type:'pkcs8',format:'der'}).equals(plain)) throw Error('Recovered key mismatch');
  return Buffer.from(key.export({type:'pkcs8',format:'pem'}));
 } finally { derived.fill(0); if(partial) partial.fill(0); if(plain) plain.fill(0); }
}
function parse(raw) {
 if (!Buffer.isBuffer(raw) || raw.length > LIMIT) throw Error('Backup size unsupported');
 return receipts.parse(raw);
}
module.exports=Object.freeze({VERSION,KDF,LIMIT,backup,restore,parse,pem,fingerprint,password});
