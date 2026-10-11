/* Optional group agreement: several independently selected keys, never authorship. */
'use strict';
const crypto=require('node:crypto'),r=require('./receipts.cjs');
const VERSION='group-receipt/1.0.0',ROSTER='group-trust-roster/1.0.0',LIMIT=32*1024*1024;
function fields(value,names){
 if(!value||typeof value!=='object'||Array.isArray(value)||Object.keys(value).sort().join('|')!==[...names].sort().join('|'))throw Error('Missing or unknown group field');
}
function keyId(key){return r.hash(key.export({type:'spki',format:'der'}));}
function roster(value){
 fields(value,['version','public_keys']);
 if(value.version!==ROSTER||!Array.isArray(value.public_keys)||value.public_keys.length<2||value.public_keys.length>16)throw Error('Unsupported group roster');
 const keys=new Map();
 for(const pem of value.public_keys){
  if(typeof pem!=='string'||pem.length>4096||!pem.startsWith('-----BEGIN PUBLIC KEY-----\n'))throw Error('Public keys only');
  const key=crypto.createPublicKey(pem);
  if(pem!==key.export({type:'spki',format:'pem'}))throw Error('Select one canonical public key without appended material');
  if(key.asymmetricKeyType!=='ed25519'&&!(key.asymmetricKeyType==='ec'&&key.asymmetricKeyDetails.namedCurve==='prime256v1'))throw Error('Unsupported group key');
  const id=keyId(key);if(keys.has(id))throw Error('Duplicate group key');keys.set(id,pem);
 }
 return keys;
}
function validate(manifest){
 fields(manifest,['version','record_type','group_id','artifact_sha256','artifact_bytes','signer_keys','issued_at','expires_at','clock','statement','authorship_proven','distinct_people_proven','revocation_status','tag_issuance']);
 if(manifest.version!==VERSION||manifest.record_type!=='optional_group_agreement'||!/^[a-f0-9]{8}-[a-f0-9]{4}-4[a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}$/.test(manifest.group_id)||!/^[a-f0-9]{64}$/.test(manifest.artifact_sha256))throw Error('Unsupported group identity');
 if(!Number.isSafeInteger(manifest.artifact_bytes)||manifest.artifact_bytes<0||manifest.artifact_bytes>LIMIT||!Number.isSafeInteger(manifest.issued_at)||manifest.issued_at<0||!Number.isSafeInteger(manifest.expires_at)||manifest.expires_at-manifest.issued_at<60||manifest.expires_at-manifest.issued_at>604800)throw Error('Group bounds');
 const ids=manifest.signer_keys;
 if(!Array.isArray(ids)||ids.length<2||ids.length>16||ids.some(id=>typeof id!=='string'||!/^[a-f0-9]{64}$/.test(id))||new Set(ids).size!==ids.length||r.canonical(ids)!==r.canonical([...ids].sort()))throw Error('Unsupported signer set');
 if(manifest.clock!=='issuer_local_clock_unverified'||manifest.statement!=='These keys signed the same artifact-bound record; this does not establish authorship or identity.'||manifest.authorship_proven!==false||manifest.distinct_people_proven!==false||manifest.revocation_status!=='unchecked'||manifest.tag_issuance!==false)throw Error('Unsupported group claim');
 r.bytes(manifest);return manifest;
}
function create(artifact,trustedRoster,issuedAt,lifetime=86400){
 if(!Buffer.isBuffer(artifact)||artifact.length>LIMIT)throw Error('Artifact size unsupported');
 const keys=roster(trustedRoster);
 return validate({version:VERSION,record_type:'optional_group_agreement',group_id:crypto.randomUUID(),artifact_sha256:r.hash(artifact),artifact_bytes:artifact.length,signer_keys:[...keys.keys()].sort(),issued_at:issuedAt,expires_at:issuedAt+lifetime,clock:'issuer_local_clock_unverified',statement:'These keys signed the same artifact-bound record; this does not establish authorship or identity.',authorship_proven:false,distinct_people_proven:false,revocation_status:'unchecked',tag_issuance:false});
}
function endorse(manifest,privateKey,agree=false){
 if(agree!==true)throw Error('Explicit agreement required');validate(manifest);
 const id=keyId(crypto.createPublicKey(privateKey));
 if(!manifest.signer_keys.includes(id))throw Error('Key is not in selected signer set');
 return r.sign(manifest,privateKey);
}
function assemble(manifest,trustedRoster,endorsements){
 validate(manifest);const selected=roster(trustedRoster);
 if(r.canonical([...selected.keys()].sort())!==r.canonical(manifest.signer_keys)||!Array.isArray(endorsements)||endorsements.length!==selected.size)throw Error('Signer roster mismatch');
 const verified=new Map();
 for(const envelope of endorsements){
  if(!envelope||!selected.has(envelope.key_sha256)||verified.has(envelope.key_sha256))throw Error('Missing, extra or duplicate signer');
  const payload=r.verify(envelope,selected.get(envelope.key_sha256));
  if(!r.bytes(payload).equals(r.bytes(manifest)))throw Error('Signers did not agree on the same record');
  verified.set(envelope.key_sha256,envelope);
 }
 const group={version:VERSION,manifest,endorsements:[...verified].sort(([a],[b])=>a.localeCompare(b)).map(([,e])=>e)};
 r.bytes(group);return group;
}
function inspect(group,trustedRoster,artifact,now){
 fields(group,['version','manifest','endorsements']);if(group.version!==VERSION)throw Error('Unsupported group version');
 const checked=assemble(group.manifest,trustedRoster,group.endorsements),m=checked.manifest;
 if(r.canonical(checked)!==r.canonical(group))throw Error('Noncanonical signer ordering');
 if(!Buffer.isBuffer(artifact)||artifact.length>LIMIT||artifact.length!==m.artifact_bytes||r.hash(artifact)!==m.artifact_sha256)throw Error('Group artifact mismatch');
 if(!Number.isSafeInteger(now)||now<0)throw Error('Verifier clock unavailable');
 return {profile:VERSION,record_integrity:'all_signatures_verified_under_selected_roster',artifact_binding:'matched',signer_count:checked.endorsements.length,signers:checked.endorsements.map(e=>({key_sha256:e.key_sha256,algorithm:e.algorithm,record_integrity:'verified_under_pinned_key'})),expiry:now<m.issued_at?'not_yet_current':now>=m.expires_at?'expired':'within_declared_window',clock:'verifier_local_clock_unverified',revocation:'unchecked',authorship:'unestablished',distinct_people:'unestablished',coercion:'not_assessed',certified_valid:false,tag_issuance:false};
}
module.exports=Object.freeze({VERSION,ROSTER,LIMIT,roster,validate,create,endorse,assemble,inspect});
