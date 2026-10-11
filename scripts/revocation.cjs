#!/usr/bin/env node
'use strict';
const v=require('../protocol/revocation.cjs'),r=require('../protocol/receipts.cjs'),g=require('../protocol/group-receipts.cjs'),io=require('./receipt.cjs');
const json=file=>r.parse(io.read(file)),pub=file=>io.read(file,false,4096).toString('utf8');
function lifetime(a){if(!/^\d+$/.test(a))throw Error('Explicit lifetime required');return Number(a);}
function main(args){
 const [command,...a]=args,now=Math.floor(Date.now()/1000);
 if(!command||command==='help'){console.log('AI Trust ID · optional offline revocation status\n\ncreate <authority-private.pem> <lifetime-seconds> <new-log.json>\nrefresh <log.json> <authority-private.pem> <lifetime-seconds> <new-log.json>\nrevoke <log.json> <authority-private.pem> <revoke-public.pem> <lifetime-seconds> <new-log.json>\ncheckpoint <log.json> <selected-authority-public.pem>\npolicy <log.json> <selected-authority-public.pem> <max-age-seconds> <max-lifetime-seconds> <new-policy.json> --trust-checkpoint\nverify-receipt <receipt.json> <selected-public.pem> <artifact> <log.json|-> <selected-authority-public.pem> <policy.json>\nverify-group <group.json> <selected-roster.json> <artifact> <log.json|-> <selected-authority-public.pem> <policy.json>\n\nCreate policy separately using a trusted checkpoint. No network or automatic sharing. A fresh selected log does not prove global/current non-revocation, identity or authorship. Exit 3 means expiry, revoked key or unavailable/stale status; exit 2 means malformed/untrusted input.');return 0;}
 if(command==='create'&&a.length===3){io.write(a[2],r.bytes(v.extend(null,io.read(a[0],true),null,now,lifetime(a[1])))+'\n');console.log('Local selected-authority log created; not a publicly witnessed transparency service.');return 0;}
 if(command==='refresh'&&a.length===4){io.write(a[3],r.bytes(v.extend(json(a[0]),io.read(a[1],true),null,now,lifetime(a[2])))+'\n');console.log('New signed checkpoint saved; old history preserved.');return 0;}
 if(command==='revoke'&&a.length===5){io.write(a[4],r.bytes(v.extend(json(a[0]),io.read(a[1],true),pub(a[2]),now,lifetime(a[3])))+'\n');console.log('Selected key revocation recorded locally. Distribute only through your accepted trust channel.');return 0;}
 if(command==='checkpoint'&&a.length===2){const head=v.history(json(a[0]),pub(a[1])).at(-1);console.log(JSON.stringify({sequence:head.payload.sequence,sha256:head.sha256,authority_key_sha256:head.payload.authority_key_sha256,clock:'issuer_local_clock_unverified',global_status_proven:false}));return 0;}
 if(command==='policy'&&a.length===6&&a[5]==='--trust-checkpoint'){const head=v.history(json(a[0]),pub(a[1])).at(-1);const chosen=v.policy({version:v.POLICY,minimum_sequence:head.payload.sequence,minimum_checkpoint_sha256:head.sha256,maximum_age_seconds:lifetime(a[2]),maximum_lifetime_seconds:lifetime(a[3])});io.write(a[4],r.bytes(chosen)+'\n');console.log('Selected checkpoint pinned locally. This detects rollback against your chosen history, not independent log completeness.');return 0;}
 if(['verify-receipt','verify-group'].includes(command)&&a.length===6){
  let integrity,keys;
  if(command==='verify-receipt'){const envelope=json(a[0]);integrity=r.inspectReceipt(envelope,io.read(a[1],false,4096),io.read(a[2],false,80000),now);keys=[envelope.key_sha256];}
  else{integrity=g.inspect(json(a[0]),json(a[1]),io.read(a[2],false,g.LIMIT),now);keys=integrity.signers.map(k=>k.key_sha256);}
  const status=v.assess(a[3]==='-'?null:json(a[3]),pub(a[4]),json(a[5]),keys,now);
  const usable=integrity.expiry==='within_declared_window'&&status.can_continue_under_selected_policy;
  console.log(JSON.stringify({integrity,selected_revocation:status,can_continue_under_selected_policy:usable,certified_valid:false,tag_issuance:false}));return usable?0:3;
 }
 throw Error('Unsupported revocation operation');
}
if(require.main===module){try{process.exitCode=main(process.argv.slice(2));}catch(_){console.error('Revocation operation refused: invalid input, trust, history, policy, permissions or prerequisites. No valid verdict issued.');process.exitCode=2;}}
module.exports={main};
