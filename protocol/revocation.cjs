/* Selected signed checkpoint history: conditional offline status, not global transparency. */
'use strict';
const crypto=require('node:crypto'),r=require('./receipts.cjs');
const VERSION='offline-revocation-log/1.0.0',POLICY='offline-freshness-policy/1.0.0',COMPARISON='offline-revocation-comparison/1.0.0',ZERO='0'.repeat(64),MAX=64;
function fields(v,n){if(!v||typeof v!=='object'||Array.isArray(v)||Object.keys(v).sort().join('|')!==[...n].sort().join('|'))throw Error('Missing or unknown revocation field');}
function fp(v){if(typeof v!=='string'||!/^([a-f0-9]{64})$/.test(v))throw Error('Invalid key or checkpoint fingerprint');return v;}
function time(v){if(!Number.isSafeInteger(v)||v<0)throw Error('Unsupported local clock');return v;}
function id(pem){if(typeof pem!=='string'||pem.length>4096||!pem.startsWith('-----BEGIN PUBLIC KEY-----\n'))throw Error('One canonical public key required');const k=crypto.createPublicKey(pem);const pub=k.export({type:'spki',format:'pem'});if(pem!==pub)throw Error('One canonical public key required');if(k.asymmetricKeyType!=='ed25519'&&!(k.asymmetricKeyType==='ec'&&k.asymmetricKeyDetails.namedCurve==='prime256v1'))throw Error('Unsupported revocation key algorithm');return r.hash(k.export({type:'spki',format:'der'}));}
function checkpoint(v){
 fields(v,['version','record_type','authority_key_sha256','sequence','previous_sha256','issued_at','expires_at','revoked_keys','clock','global_status_proven','tag_issuance']);
 if(v.version!==VERSION||v.record_type!=='selected_revocation_checkpoint'||v.clock!=='issuer_local_clock_unverified'||v.global_status_proven!==false||v.tag_issuance!==false)throw Error('Unsupported revocation claim');
 fp(v.authority_key_sha256);fp(v.previous_sha256);time(v.issued_at);time(v.expires_at);
 if(!Number.isSafeInteger(v.sequence)||v.sequence<1||v.sequence>MAX||v.expires_at-v.issued_at<60||v.expires_at-v.issued_at>604800)throw Error('Checkpoint bounds');
 if(!Array.isArray(v.revoked_keys)||v.revoked_keys.length>128||new Set(v.revoked_keys).size!==v.revoked_keys.length||r.canonical(v.revoked_keys)!==r.canonical([...v.revoked_keys].sort()))throw Error('Invalid revoked-key set');
 v.revoked_keys.forEach(fp);return v;
}
function history(log,pinnedAuthority){
 fields(log,['version','checkpoints']);
 if(log.version!==VERSION||!Array.isArray(log.checkpoints)||log.checkpoints.length<1||log.checkpoints.length>MAX)throw Error('History bounds');
 const authority=id(pinnedAuthority);r.bytes(log);let prior=null,previous=ZERO;const checked=[];
 for(const signed of log.checkpoints){
  const v=checkpoint(r.verify(signed,pinnedAuthority));
  if(v.authority_key_sha256!==authority||v.sequence!==checked.length+1||v.previous_sha256!==previous||(prior&&(v.issued_at<prior.issued_at||prior.revoked_keys.some(k=>!v.revoked_keys.includes(k)))))throw Error('Changed, incomplete or nonmonotonic history');
  previous=r.hash(r.bytes(signed));checked.push({payload:v,sha256:previous});prior=v;
 }
 return checked;
}
function compareHistories(leftLog,rightLog,pinnedAuthority){
 // Verify both complete inputs even when they already differ at an early checkpoint.
 const left=history(leftLog,pinnedAuthority),right=history(rightLog,pinnedAuthority);
 const overlap=Math.min(left.length,right.length);
 let common=0;
 while(common<overlap&&left[common].sha256===right[common].sha256)common++;
 const branch=common<overlap;
 let differentStatement=null;
 // Ignore the predecessor digest here: a re-signing can change linkage without
 // changing the declared time window or the set of revoked keys.
 for(let i=common;i<overlap;i++){
  const a=left[i].payload,b=right[i].payload;
  if(a.issued_at!==b.issued_at||a.expires_at!==b.expires_at||r.canonical(a.revoked_keys)!==r.canonical(b.revoked_keys)){
   differentStatement=i+1;break;
  }
 }
 const outcome=branch?'divergent_signed_histories':left.length===right.length?'same_signed_history':left.length<right.length?'left_is_signed_prefix':'right_is_signed_prefix';
 return {
  profile:COMPARISON,outcome,authority_key_sha256:left[0].payload.authority_key_sha256,
  left_checkpoints:left.length,right_checkpoints:right.length,
  common_checkpoint:common?{sequence:common,sha256:left[common-1].sha256}:null,
  first_divergence:branch?{sequence:common+1,left_checkpoint_sha256:left[common].sha256,right_checkpoint_sha256:right[common].sha256}:null,
  first_different_statement_sequence:differentStatement,
  key_status_evaluated:false,global_log_completeness_proven:false,public_transparency_witnessed:false,tag_issuance:false,
 };
}
function extend(log,privateKey,revokedPublicKey,issuedAt,lifetime){
 time(issuedAt);if(!Number.isSafeInteger(lifetime)||lifetime<60||lifetime>604800)throw Error('Declare checkpoint lifetime');
 const publicKey=crypto.createPublicKey(privateKey).export({type:'spki',format:'pem'}),old=log===null?[]:history(log,publicKey);
 if(old.length>=MAX)throw Error('Bounded history exhausted; do not discard history');
 const last=old.at(-1),revoked=last?[...last.payload.revoked_keys]:[];
 if(revokedPublicKey!==null){const selected=id(revokedPublicKey);if(revoked.includes(selected))throw Error('Key already revoked');revoked.push(selected);}
 const value=checkpoint({version:VERSION,record_type:'selected_revocation_checkpoint',authority_key_sha256:id(publicKey),sequence:old.length+1,previous_sha256:last?.sha256||ZERO,issued_at:issuedAt,expires_at:issuedAt+lifetime,revoked_keys:revoked.sort(),clock:'issuer_local_clock_unverified',global_status_proven:false,tag_issuance:false});
 const result={version:VERSION,checkpoints:[...(log?.checkpoints||[]),r.sign(value,privateKey)]};history(result,publicKey);return result;
}
function policy(v){
 fields(v,['version','minimum_sequence','minimum_checkpoint_sha256','maximum_age_seconds','maximum_lifetime_seconds']);
 if(v.version!==POLICY||!Number.isSafeInteger(v.minimum_sequence)||v.minimum_sequence<1||v.minimum_sequence>MAX||!Number.isSafeInteger(v.maximum_age_seconds)||v.maximum_age_seconds<1||v.maximum_age_seconds>604800||!Number.isSafeInteger(v.maximum_lifetime_seconds)||v.maximum_lifetime_seconds<60||v.maximum_lifetime_seconds>604800)throw Error('Explicit supported freshness policy required');
 fp(v.minimum_checkpoint_sha256);return v;
}
function assess(log,pinnedAuthority,selectedPolicy,keys,now){
 time(now);policy(selectedPolicy);id(pinnedAuthority);
 if(!Array.isArray(keys)||keys.length<1||keys.length>16||new Set(keys).size!==keys.length)throw Error('Select distinct verification keys');keys.forEach(fp);
 const common={profile:VERSION,selected_policy:{...selectedPolicy},clock:'verifier_local_clock_unverified',authority_clock_independently_verified:false,global_current_revocation_known:false,public_transparency_witnessed:false,authorship:'unestablished',certified_valid:false,tag_issuance:false};
 if(log===null)return {...common,checkpoint:null,freshness:'unavailable',keys:keys.map(k=>({key_sha256:k,status:'unknown'})),can_continue_under_selected_policy:false};
 const chain=history(log,pinnedAuthority),head=chain.at(-1),p=head.payload,anchor=chain[selectedPolicy.minimum_sequence-1];
 if(!anchor||anchor.sha256!==selectedPolicy.minimum_checkpoint_sha256)throw Error('Selected checkpoint absent: rollback or different history');
 if(p.expires_at-p.issued_at>selectedPolicy.maximum_lifetime_seconds)throw Error('Snapshot exceeds selected lifetime policy');
 const freshness=now<p.issued_at?'future':now>=p.expires_at?'expired':now-p.issued_at>selectedPolicy.maximum_age_seconds?'stale':'within_selected_policy';
 const statuses=keys.map(k=>({key_sha256:k,status:p.revoked_keys.includes(k)?'revoked_in_selected_log':freshness==='within_selected_policy'?'not_recorded_revoked_as_of_selected_checkpoint':'unknown'}));
 return {...common,checkpoint:{sequence:p.sequence,sha256:head.sha256,issued_at:p.issued_at,expires_at:p.expires_at,clock:p.clock},freshness,status_age_seconds:now-p.issued_at,keys:statuses,can_continue_under_selected_policy:freshness==='within_selected_policy'&&statuses.every(k=>k.status==='not_recorded_revoked_as_of_selected_checkpoint')};
}
module.exports=Object.freeze({VERSION,POLICY,COMPARISON,MAX,id,checkpoint,history,compareHistories,extend,policy,assess});
