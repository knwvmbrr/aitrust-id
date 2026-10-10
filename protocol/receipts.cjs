/* Optional receipt/1.0.0: pinned-key integrity, never identity or authorship. */
'use strict';
const crypto=require('node:crypto');
const VERSION='offline-receipt/1.0.0', SIGNATURE='detached-record/1.0.0';
const hash=raw=>crypto.createHash('sha256').update(raw).digest('hex');
const LIMIT=262144;
function canonical(value,depth=0){
 if(depth>16)throw Error('Record nesting limit');
 if(value===null||typeof value==='boolean')return JSON.stringify(value);
 if(typeof value==='number'){if(!Number.isFinite(value)||(Number.isInteger(value)&&!Number.isSafeInteger(value)))throw Error('Unsafe number');return JSON.stringify(value);}
 if(typeof value==='string'){if(value.length>32768||/[\uD800-\uDBFF](?![\uDC00-\uDFFF])|(?<![\uD800-\uDBFF])[\uDC00-\uDFFF]/u.test(value))throw Error('Invalid string');return JSON.stringify(value);}
 if(Array.isArray(value))return '['+value.map(v=>canonical(v,depth+1)).join(',')+']';
 if(value&&typeof value==='object'&&(Object.getPrototypeOf(value)===Object.prototype||Object.getPrototypeOf(value)===null))return '{'+Object.keys(value).sort().map(k=>canonical(k,depth+1)+':'+canonical(value[k],depth+1)).join(',')+'}';
 throw Error('Unsupported record value');
}
function parse(raw){
 const text=Buffer.isBuffer(raw)?new TextDecoder('utf-8',{fatal:true}).decode(raw):raw;
 if(typeof text!=='string'||Buffer.byteLength(text)>LIMIT)throw Error('Record size limit');
 let i=0;const space=()=>{while(/[\x20\x09\x0a\x0d]/.test(text[i]||'!'))i++;};
 function token(depth=0){
  if(depth>16)throw Error('Record nesting limit');space();const c=text[i];
  if(c==='"'){
   const start=i++;let escaped=false;
   while(i<text.length){const ch=text[i++];if(ch==='"'&&!escaped)return JSON.parse(text.slice(start,i));if(ch==='\\'&&!escaped)escaped=true;else escaped=false;}
   throw Error('Invalid string');
  }
  if(c==='{'||c==='['){
   i++;const object=c==='{',out=object?Object.create(null):[],end=object?'}':']';space();if(text[i]===end){i++;return out;}
   while(true){
    if(object){space();if(text[i]!=='"')throw Error('Invalid object key');const k=token(depth+1);if(Object.hasOwn(out,k))throw Error('Duplicate field');space();if(text[i++]!==':')throw Error('Invalid object');out[k]=token(depth+1);}
    else out.push(token(depth+1));
    space();const separator=text[i++];if(separator===end)return out;if(separator!==',')throw Error('Invalid record separator');
   }
  }
  const m=/^(?:true|false|null|-?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?)/.exec(text.slice(i));
  if(!m)throw Error('Invalid record value');i+=m[0].length;return JSON.parse(m[0]);
 }
 const value=token();space();if(i!==text.length)throw Error('Trailing record content');canonical(value);return value;
}
function bytes(value){const raw=Buffer.from(canonical(value));if(raw.length>LIMIT)throw Error('Record size limit');return raw;}
function keys(value,names){if(!value||typeof value!=='object'||Array.isArray(value)||Object.keys(value).sort().join('|')!==[...names].sort().join('|'))throw Error('Unknown or missing record field');}
function algorithm(key){
 if(key.asymmetricKeyType==='ed25519')return 'Ed25519';
 if(key.asymmetricKeyType==='ec'&&key.asymmetricKeyDetails.namedCurve==='prime256v1')return 'ECDSA-P256-SHA256';
 throw Error('Unsupported signing algorithm');
}
function publicId(key){return hash(crypto.createPublicKey(key.type==='private'?key:{key:key.export({type:'spki',format:'pem'}),format:'pem'}).export({type:'spki',format:'der'}));}
function sign(payload,key){
 key=crypto.createPrivateKey(key);const alg=algorithm(key),raw=bytes(payload);
 const signature=crypto.sign(alg==='Ed25519'?null:'sha256',raw,{key,dsaEncoding:'ieee-p1363'});
 return {version:SIGNATURE,algorithm:alg,key_sha256:publicId(key),payload:raw.toString('base64'),signature:signature.toString('base64')};
}
function base64(text,max){if(typeof text!=='string'||text.length>max||!/^(?:[A-Za-z0-9+/]{4})*(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?$/.test(text))throw Error('Invalid base64');const b=Buffer.from(text,'base64');if(b.toString('base64')!==text)throw Error('Noncanonical base64');return b;}
function verify(envelope,pinnedKey){
 keys(envelope,['version','algorithm','key_sha256','payload','signature']);
 const key=crypto.createPublicKey(pinnedKey),alg=algorithm(key);
 if(envelope.version!==SIGNATURE||envelope.algorithm!==alg||envelope.key_sha256!==publicId(key))throw Error('Untrusted version, algorithm or key');
 const raw=base64(envelope.payload,Math.ceil(LIMIT/3)*4),signature=base64(envelope.signature,128);
 if(signature.length!==64||!crypto.verify(alg==='Ed25519'?null:'sha256',raw,{key,dsaEncoding:'ieee-p1363'},signature))throw Error('Record signature mismatch');
 const payload=parse(raw);if(!bytes(payload).equals(raw))throw Error('Noncanonical signed record');
 return payload;
}
function observation(record){
 const example=require('../tools/composition/core.cjs').create().snapshot();
 keys(record,[...Object.keys(example),'source_sha256','artifact_sha256','artifact_encoding']);
 function shape(value,model){
  if(model===null){if(value!==null&&typeof value!=='number'&&typeof value!=='string')throw Error('Invalid nullable observation');return;}
  if(Array.isArray(model)){if(!Array.isArray(value)||value.length!==0)throw Error('Observation must not issue tags');return;}
  if(typeof model==='object'){keys(value,Object.keys(model));for(const k of Object.keys(model))shape(value[k],model[k]);return;}
  if(typeof value!==typeof model||(typeof value==='number'&&(!Number.isFinite(value)||value<0)))throw Error('Invalid observation value');
 }
 for(const k of Object.keys(example))shape(record[k],example[k]);
 if(record.schema_version!==1||record.record_type!=='composition_observation'||record.method!=='composition-observation/1.0.0'||!['paused','limit_reached'].includes(record.status)||record.authorship_inference!==false||record.independent_accuracy_evidence!==false||record.focus.reading_inferred!==false||record.insertion.origin_inferred!==false||record.safety.detection_complete!==false)throw Error('Unsupported observation claim');
 if(!/^[a-f0-9]{64}$/.test(record.source_sha256)||!/^[a-f0-9]{64}$/.test(record.artifact_sha256)||record.artifact_encoding!=='UTF-8; exact editor value; no normalization')throw Error('Observation artifact identity missing');
 if(record.event_count>10000||record.final_length>20000||!Number.isSafeInteger(record.event_count)||!Number.isSafeInteger(record.final_length)||!['suppressed','observed'].includes(record.timing.status))throw Error('Observation bounds');
 for(const part of ['timing','revision','caret','focus','insertion','safety'])if(record[part].signal!==example[part].signal)throw Error('Unknown observation signal');
 for(const k of ['units','warning'])if(record[k]!==example[k])throw Error('Observation meaning changed');
 if(canonical(record.limits)!==canonical(example.limits)||record.insertion.minimum_units!==64||record.insertion.preceding_key_window_ms!==2000)throw Error('Observation parameters changed');
 if(record.timing.status==='suppressed'&&(record.timing.samples!==0||record.timing.dwell_cv!==null||record.timing.flight_cv!==null||record.safety.timing_suppressed!==true))throw Error('Suppressed timing leaked');
 if(record.timing.status==='observed'&&(record.timing.reason!==null||record.safety.timing_suppressed!==false))throw Error('Timing safety mismatch');
 if(!Number.isSafeInteger(record.timing.samples)||record.timing.samples<0||record.timing.samples>record.event_count)throw Error('Timing sample bounds');
 for(const v of [record.timing.dwell_cv,record.timing.flight_cv,record.caret.entropy_bits])if(v!==null&&(typeof v!=='number'||!Number.isFinite(v)||v<0))throw Error('Invalid observation statistic');
 if(record.caret.entropy_bits>3||record.focus.visible_focused_ms>1800000||record.focus.hidden_ms>1800000)throw Error('Observation window bounds');
 for(const v of [record.revision.deleted,record.revision.rewritten,record.revision.nonadjacent_edits,record.focus.changes,record.focus.visible_focused_edits,record.focus.edit_gaps_at_least_2000_ms,record.insertion.bursts])if(!Number.isSafeInteger(v)||v<0)throw Error('Invalid observation counter');
 if(record.timing.status==='suppressed'&&(typeof record.timing.reason!=='string'||!record.timing.reason))throw Error('Missing suppression reason');
 return record;
}
function receipt(artifact,record,issuedAt,lifetime=86400){
 observation(record);
 if(!Buffer.isBuffer(artifact)||artifact.length>80000||!Number.isSafeInteger(issuedAt)||issuedAt<0||!Number.isSafeInteger(lifetime)||lifetime<60||lifetime>604800)throw Error('Artifact or expiry unsupported');
 const decoded=new TextDecoder('utf-8',{fatal:true,ignoreBOM:true}).decode(artifact);
 if(hash(artifact)!==record.artifact_sha256||decoded.length!==record.final_length)throw Error('Artifact does not match observation');
 return {version:VERSION,record_type:'optional_composition_receipt',artifact_sha256:hash(artifact),artifact_bytes:artifact.length,
  observation:record,issued_at:issuedAt,expires_at:issuedAt+lifetime,clock:'issuer_local_clock_unverified',
  forgery_cost_class:'unvalidated',signature_proves:'record_integrity_only',authorship_proven:false,
  independent_timestamp:false,revocation_status:'unchecked',tag_issuance:false};
}
function inspectReceipt(envelope,pinnedKey,artifact,now){
 const r=verify(envelope,pinnedKey);keys(r,['version','record_type','artifact_sha256','artifact_bytes','observation','issued_at','expires_at','clock','forgery_cost_class','signature_proves','authorship_proven','independent_timestamp','revocation_status','tag_issuance']);
 if(r.version!==VERSION||r.record_type!=='optional_composition_receipt'||r.forgery_cost_class!=='unvalidated'||r.signature_proves!=='record_integrity_only'||r.authorship_proven!==false||r.independent_timestamp!==false||r.revocation_status!=='unchecked'||r.tag_issuance!==false||r.clock!=='issuer_local_clock_unverified')throw Error('Unsupported receipt claim');
 const expected=receipt(artifact,r.observation,r.issued_at,r.expires_at-r.issued_at);
 if(canonical(expected)!==canonical(r))throw Error('Receipt binding mismatch');
 if(!Number.isSafeInteger(now)||now<0)throw Error('Verifier clock unavailable');
 return {record_integrity:'verified_under_pinned_key',artifact_binding:'matched',expiry:now<r.issued_at?'not_yet_current':now>=r.expires_at?'expired':'within_declared_window',clock:'verifier_local_clock_unverified',revocation:'unchecked',authorship:'unestablished',independent_timestamp:false,certified_valid:false,key_sha256:envelope.key_sha256,algorithm:envelope.algorithm,forgery_cost_class:r.forgery_cost_class};
}
module.exports=Object.freeze({VERSION,SIGNATURE,parse,canonical,bytes,hash,sign,verify,receipt,inspectReceipt,observation});
