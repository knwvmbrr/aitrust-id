'use strict';

const {createPublicKey}=require('node:crypto');
const receipts=require('./receipts.cjs');
const revocation=require('./revocation.cjs');

const OBSERVATION='offline-revocation-witness/1.0.0';
const POLICY='offline-revocation-witness-policy/1.0.0';
const MAX_WITNESSES=8;

function selectKeys(policy,authority){
 if(!policy||typeof policy!=='object'||Array.isArray(policy)
    ||Object.keys(policy).length!==3||!['version','minimum_witnesses','witness_public_keys'].every(k=>Object.hasOwn(policy,k))
    ||policy.version!==POLICY||!Array.isArray(policy.witness_public_keys)
    ||policy.witness_public_keys.length<2||policy.witness_public_keys.length>MAX_WITNESSES
    ||!Number.isSafeInteger(policy.minimum_witnesses)||policy.minimum_witnesses<2
    ||policy.minimum_witnesses>policy.witness_public_keys.length)throw Error('Invalid witness policy');
 const selected=new Map();
 for(const key of policy.witness_public_keys){
  const id=revocation.id(key);
  if(id===authority||selected.has(id))throw Error('Authority or duplicate witness key');
  selected.set(id,key);
 }
 return selected;
}

function createPolicy(authorityKey,minimum,witnessKeys){
 const policy={version:POLICY,minimum_witnesses:minimum,witness_public_keys:witnessKeys};
 selectKeys(policy,revocation.id(authorityKey));
 return policy;
}

function observation(checkpoint){
 return {
  version:OBSERVATION,
  record_type:'observed_revocation_checkpoint',
  authority_key_sha256:checkpoint.payload.authority_key_sha256,
  checkpoint_sequence:checkpoint.payload.sequence,
  checkpoint_sha256:checkpoint.sha256,
 };
}

function comparePayload(signed,pinnedKey,expected){
 const parsed=receipts.verify(signed,pinnedKey);
 if(!receipts.bytes(parsed).equals(receipts.bytes(expected)))throw Error('Observation names a different checkpoint');
}

function sign(log,authorityKey,witnessPrivateKey,prior){
 const chain=revocation.history(log,authorityKey);
 const witnessPublicKey=createPublicKey(witnessPrivateKey).export({type:'spki',format:'pem'});
 const head=chain.at(-1);
 if(revocation.id(witnessPublicKey)===head.payload.authority_key_sha256)throw Error('Authority cannot sign as witness');
 // Null denotes an explicitly selected first observation. Undefined is refused.
 if(prior!==null){
  const saved=receipts.verify(prior,witnessPublicKey);
  const sequence=saved?.checkpoint_sequence;
  if(!Number.isSafeInteger(sequence)||sequence<1||sequence>=chain.length)throw Error('Advance requires a later checkpoint');
  if(!receipts.bytes(saved).equals(receipts.bytes(observation(chain[sequence-1]))))throw Error('Previously observed checkpoint absent');
 }
 return receipts.sign(observation(head),witnessPrivateKey);
}

function verify(log,authorityKey,policy,signedObservations){
 const head=revocation.history(log,authorityKey).at(-1);
 const expected=observation(head);
 const selected=selectKeys(policy,expected.authority_key_sha256);
 if(!Array.isArray(signedObservations)||signedObservations.length>selected.size)throw Error('Witness input exceeds roster');
 const verified=new Set();
 for(const envelope of signedObservations){
  const id=envelope?.key_sha256;
  if(!selected.has(id)||verified.has(id))throw Error('Unknown or duplicate witness');
  comparePayload(envelope,selected.get(id),expected);
  verified.add(id);
 }
 return {
  profile:OBSERVATION,
  status:verified.size>=policy.minimum_witnesses?'selected_witness_threshold_met':'insufficient_selected_witnesses',
  authority_key_sha256:expected.authority_key_sha256,
  checkpoint_sequence:expected.checkpoint_sequence,
  checkpoint_sha256:expected.checkpoint_sha256,
  verified_witness_key_count:verified.size,
  minimum_witnesses:policy.minimum_witnesses,
  independent_operators_proven:false,
  independently_timestamped:false,
  public_distribution_proven:false,
  completeness_proven:false,
  key_status_evaluated:false,
  tag_issuance:false,
 };
}

module.exports=Object.freeze({OBSERVATION,POLICY,MAX_WITNESSES,createPolicy,sign,verify});
