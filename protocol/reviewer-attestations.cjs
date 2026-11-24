/* Explicit signed review declarations; integrity is never human independence. */
'use strict';
const crypto=require('node:crypto'),{performance}=require('node:perf_hooks'),r=require('./receipts.cjs');
const PROFILE='reviewer-attestation-verification/1.0.0',POLICY='reviewer-attestation-policy/1.0.0',HISTORY='reviewer-attestation-history/1.0.0',EVENT='explicit-review-event/1.0.0';
const MAX_SUBJECT=8*1024*1024,MAX_POLICY=65536,MAX_HISTORY=262144,MAX_EVENTS=128,ZERO='0'.repeat(64),SHA=/^[a-f0-9]{64}$/,ID=/^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$/;
class Unavailable extends Error{constructor(reason){super('Review evidence unavailable');this.reason=reason;}}
const need=(v,reason='invalid_contract')=>{if(!v)throw new Unavailable(reason);};
function fields(v,names){need(v&&typeof v==='object'&&!Array.isArray(v)&&Object.keys(v).sort().join('|')===[...names].sort().join('|'));}
function text(v,max=128){need(typeof v==='string'&&v.length>0&&v.length<=max&&!/[\u0000-\u001f\u007f]/.test(v));}
function id(v){need(typeof v==='string'&&ID.test(v));}
function integer(v,min=0,max=Number.MAX_SAFE_INTEGER){need(Number.isSafeInteger(v)&&v>=min&&v<=max);}
function digest(v){need(typeof v==='string'&&SHA.test(v));}
function identity(v){fields(v,['sha256','bytes','revision']);digest(v.sha256);integer(v.bytes,0,MAX_SUBJECT);id(v.revision);}
function scope(v){
 fields(v,['id','version','statement','evidence']);id(v.id);id(v.version);text(v.statement,2048);
 need(Array.isArray(v.evidence)&&v.evidence.length>0&&v.evidence.length<=32);
 let prior='';for(const e of v.evidence){fields(e,['id','kind','sha256','bytes']);id(e.id);id(e.kind);digest(e.sha256);integer(e.bytes,0,32*1024*1024);need(e.id>prior);prior=e.id;}
}
function parse(raw,limit){need(Buffer.isBuffer(raw)&&raw.length<=limit,'resource_limit');return r.parse(raw);}
function policy(value,now){
 fields(value,['profile','review_id','reviewer','subject','scope','checkpoint']);need(value.profile===POLICY);id(value.review_id);identity(value.subject);scope(value.scope);
 fields(value.reviewer,['handle','public_key']);id(value.reviewer.handle);const pem=value.reviewer.public_key;
 need(typeof pem==='string'&&Buffer.byteLength(pem)<=4096&&pem.startsWith('-----BEGIN PUBLIC KEY-----\n'));
 const key=crypto.createPublicKey(pem);need(pem===key.export({type:'spki',format:'pem'}));
 need(key.asymmetricKeyType==='ed25519'||key.asymmetricKeyType==='ec'&&key.asymmetricKeyDetails.namedCurve==='prime256v1');
 const c=value.checkpoint;fields(c,['head_sha256','sequence','observed_at','valid_until']);digest(c.head_sha256);integer(c.sequence,1,MAX_EVENTS);integer(c.observed_at);integer(c.valid_until);
 need(c.valid_until>c.observed_at&&c.valid_until-c.observed_at<=604800);need(now>=c.observed_at&&now<c.valid_until,'checkpoint_not_current');
 return value;
}
function event(v,p){
 fields(v,['profile','review_id','reviewer_handle','subject','scope_sha256','sequence','previous_sha256','action','issued_at','review','replacement']);
 need(v.profile===EVENT&&v.review_id===p.review_id&&v.reviewer_handle===p.reviewer.handle,'review_identity_mismatch');identity(v.subject);
 need(r.canonical(v.subject)===r.canonical(p.subject),'subject_mismatch');digest(v.scope_sha256);need(v.scope_sha256===r.hash(r.bytes(p.scope)),'scope_mismatch');
 integer(v.sequence,1,MAX_EVENTS);digest(v.previous_sha256);integer(v.issued_at);need(['review','withdraw','supersede'].includes(v.action));
 if(v.action==='review'){
  const x=v.review;fields(x,['consent','human_review_declared','decision','conflicts','reviewed_at','expires_at']);
  need(x.consent===true&&x.human_review_declared===true,'consent_missing');need(['supports','does_not_support','inconclusive'].includes(x.decision));
  need(Array.isArray(x.conflicts)&&x.conflicts.length<=16);let prior='';for(const c of x.conflicts){id(c);need(c>prior);prior=c;}
  integer(x.reviewed_at);integer(x.expires_at);need(x.reviewed_at<=v.issued_at&&x.expires_at>v.issued_at&&x.expires_at-v.issued_at<=2592000);need(v.replacement===null);
 }else{
  need(v.review===null);
  if(v.action==='withdraw')need(v.replacement===null);
  else{fields(v.replacement,['review_id','head_sha256']);id(v.replacement.review_id);digest(v.replacement.head_sha256);need(v.replacement.review_id!==v.review_id);}
 }
 return v;
}
function unavailable(reason='invalid_contract'){
 return {profile:PROFILE,state:'UNAVAILABLE',reason,active_review:false,tag_issuance:false,IV_asserted:false,human_identity_established:false,reviewer_independence_established:false,accuracy_established:false};
}
function verify(input){
 try{
  const start=performance.now();need(Number.isFinite(start),'deadline_exceeded');let last=start;
  const tick=()=>{const t=performance.now();need(Number.isFinite(t)&&t>=last&&t-start<=5000,'deadline_exceeded');last=t;};
  fields(input,['subject','policy','history','now']);integer(input.now);tick();
  need(Buffer.isBuffer(input.subject)&&input.subject.length<=MAX_SUBJECT,'resource_limit');
  const p=policy(parse(input.policy,MAX_POLICY),input.now);tick();
  need(input.subject.length===p.subject.bytes&&r.hash(input.subject)===p.subject.sha256,'subject_mismatch');
  const h=parse(input.history,MAX_HISTORY);fields(h,['profile','events']);need(h.profile===HISTORY&&Array.isArray(h.events)&&h.events.length>0&&h.events.length<=MAX_EVENTS,'resource_limit');
  need(h.events.length===p.checkpoint.sequence,'incomplete_selected_history');
  let previous=ZERO,issued=0,closed=false,review=null,latest=null;
  for(let i=0;i<h.events.length;i++){
   tick();const envelope=h.events[i];let value;
   try{value=r.verify(envelope,p.reviewer.public_key);}catch(_){throw new Unavailable('signature_unavailable');}
   tick();event(value,p);
   need(!closed&&value.sequence===i+1&&value.previous_sha256===previous&&value.issued_at>=issued,'lifecycle_conflict');
   need(value.issued_at<=input.now&&value.issued_at<=p.checkpoint.observed_at,'future_event');
   if(i===0)need(value.action==='review'&&value.previous_sha256===ZERO,'lifecycle_conflict');
   if(value.action==='review')review=value.review;else closed=true;
   previous=r.hash(r.bytes(envelope));issued=value.issued_at;latest=value;
  }
  need(previous===p.checkpoint.head_sha256,'selected_head_mismatch');tick();
  const result={profile:PROFILE,state:'REVIEW_RECORD_VERIFIED',review_status:null,active_review:false,review_id:p.review_id,
   reviewer:{selected_handle:p.reviewer.handle,key_sha256:r.hash(crypto.createPublicKey(p.reviewer.public_key).export({type:'spki',format:'der'})),human_review:'self_declared_only',identity:'not_established',independence:'not_established'},
   integrity:'verified_under_caller_selected_key',subject:{...p.subject,binding:'exact_bytes_matched'},
   scope:{id:p.scope.id,version:p.scope.version,statement:p.scope.statement,sha256:r.hash(r.bytes(p.scope)),evidence_reference_count:p.scope.evidence.length,evidence:'references_bound_not_content_or_accuracy_verified'},
   attributed_review:{decision:review.decision,reviewed_at:review.reviewed_at,expires_at:review.expires_at,conflict_disclosure:review.conflicts.length?'conflicts_declared':'none_declared_not_established',conflicts:review.conflicts},
   lifecycle:{sequence:p.checkpoint.sequence,head_sha256:previous,status:'selected_checkpoint_only',observed_at:p.checkpoint.observed_at,valid_until:p.checkpoint.valid_until,replacement:latest.replacement},
   evaluated_at:null,clock:'local_clock_unverified',independent_timestamp:false,global_revocation_or_withdrawal_completeness:false,
   tag_issuance:false,IV_asserted:false,human_identity_established:false,reviewer_independence_established:false,accuracy_established:false};
  tick();const effective=input.now+Math.floor((last-start)/1000);need(Number.isSafeInteger(effective)&&effective<p.checkpoint.valid_until,'checkpoint_not_current');
  result.evaluated_at=effective;result.review_status=latest.action==='withdraw'?'WITHDRAWN':latest.action==='supersede'?'SUPERSEDED':effective>=review.expires_at?'EXPIRED':review.conflicts.length?'CONFLICT_DISCLOSED':'ACTIVE_DECLARATION';result.active_review=result.review_status==='ACTIVE_DECLARATION';return result;
 }catch(e){return unavailable(e instanceof Unavailable?e.reason:'invalid_contract');}
}
module.exports=Object.freeze({PROFILE,POLICY,HISTORY,EVENT,MAX_SUBJECT,MAX_POLICY,MAX_HISTORY,MAX_EVENTS,ZERO,verify,unavailable});
