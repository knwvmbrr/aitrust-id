#!/usr/bin/env node
'use strict';

const witnesses=require('../protocol/revocation-witnesses.cjs');
const receipts=require('../protocol/receipts.cjs');
const io=require('./receipt.cjs');

const json=file=>receipts.parse(io.read(file));
const pub=file=>io.read(file,false,4096).toString('utf8');
const save=(file,value)=>io.write(file,Buffer.concat([receipts.bytes(value),Buffer.from('\n')]));

function main([command,...args]){
 if(!command||command==='help'){
  console.log([
   'AI Trust ID · offline revocation witness observations',
   '',
   'policy <authority.pub> <minimum> <new-policy.json> <witness.pub> <witness.pub> [...]',
   'sign <log.json> <authority.pub> <witness-private.pem> <new-observation.json> --first-observation',
   'sign <log.json> <authority.pub> <witness-private.pem> <new-observation.json> --after <saved-observation.json>',
   'verify <log.json> <authority.pub> <your-policy.json> [observation.json ...]',
   '',
   'Select public keys yourself through trusted channels. Keep your previous observation separately.',
   'Verify exits 0 when the selected key count meets policy, 3 when too few valid keys signed, or 2 on refusal.',
   'Results do not prove independent operators, a public log, current key status or tag validity.',
  ].join('\n'));
  return 0;
 }
 if(command==='policy'&&args.length>=5&&args.length<=3+witnesses.MAX_WITNESSES){
  const [authority,minimum,output,...keys]=args;
  if(!/^[2-8]$/.test(minimum))throw Error('Invalid minimum');
  save(output,witnesses.createPolicy(pub(authority),Number(minimum),keys.map(pub)));
  console.log('Selected witness policy saved locally. It does not establish who controls the keys.');
  return 0;
 }
 if(command==='sign'){
  const [logFile,authority,privateKey,output,flag,priorFile]=args;
  let prior;
  if(args.length===5&&flag==='--first-observation')prior=null;
  else if(args.length===6&&flag==='--after')prior=json(priorFile);
  else throw Error('Select a first or advancing observation');
  if(flag==='--after'&&prior===null)throw Error('A saved signed observation is required');
  save(output,witnesses.sign(json(logFile),pub(authority),io.read(privateKey,true,4096),prior));
  console.log('Signed observation saved locally. No files were sent.');
  return 0;
 }
 if(command==='verify'&&args.length>=3&&args.length<=3+witnesses.MAX_WITNESSES){
  const [logFile,authority,policy,...observations]=args;
  const result=witnesses.verify(json(logFile),pub(authority),json(policy),observations.map(json));
  console.log(JSON.stringify(result));
  return result.status==='selected_witness_threshold_met'?0:3;
 }
 throw Error('Unsupported witness operation');
}

if(require.main===module){
 try{process.exitCode=main(process.argv.slice(2));}
 catch(error){
  console.error(error?.code==='AITRUST_PRIVATE_CLEANUP'
   ?'Witness operation refused. Inspect your output directory: temporary file cleanup failed.'
   :'Witness operation refused: invalid input, trust, history or file permissions. No valid result issued.');
  process.exitCode=2;
 }
}
module.exports={main};
