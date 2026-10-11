#!/usr/bin/env node
'use strict';
const g=require('../protocol/group-receipts.cjs'),r=require('../protocol/receipts.cjs'),io=require('./receipt.cjs');
function json(file){return r.parse(io.read(file));}
function main(args){
 const [command,...a]=args;
 if(!command||command==='help'){
  console.log('AI Trust ID · optional local group receipts\n\nroster <new-roster.json> <selected-public-1.pem> <selected-public-2.pem> ...\ncreate <artifact> <trusted-roster.json> <new-manifest.json>\nsign <manifest.json> <your-private.pem> <new-endorsement.json> --agree\nassemble <manifest.json> <trusted-roster.json> <new-group.json> <endorsement-1.json> <endorsement-2.json> ...\nverify <group.json> <trusted-roster.json> <artifact>\n\nEach participant signs independently. Select public-key trust separately. The local record exposes a collaboration graph. No upload, identity/authorship proof, checked revocation, compulsory receipt or tag issuance.');return 0;
 }
 if(command==='roster'&&a.length>=3&&a.length<=17){
  const value={version:g.ROSTER,public_keys:a.slice(1).map(file=>io.read(file,false,4096).toString('utf8'))};
  g.roster(value);io.write(a[0],r.bytes(value)+'\n');console.log('Selected public-key roster saved locally. Confirm these keys through your own trusted channel.');return 0;
 }
 if(command==='create'&&a.length===3){io.write(a[2],r.bytes(g.create(io.read(a[0],false,g.LIMIT),json(a[1]),Math.floor(Date.now()/1000)))+'\n');console.log('Local manifest created. Share it only with willing participants.');return 0;}
 if(command==='sign'&&a.length===4&&a[3]==='--agree'){
  io.write(a[2],r.bytes(g.endorse(json(a[0]),io.read(a[1],true),true))+'\n');
  console.log('Your selected key signed this manifest. No authorship verdict issued.');return 0;
 }
 if(command==='assemble'&&a.length>=5&&a.length<=19){
  io.write(a[2],r.bytes(g.assemble(json(a[0]),json(a[1]),a.slice(3).map(json)))+'\n');
  console.log('All required signatures verified; group record saved locally.');return 0;
 }
 if(command==='verify'&&a.length===3){
  const result=g.inspect(json(a[0]),json(a[1]),io.read(a[2],false,g.LIMIT),Math.floor(Date.now()/1000));
  console.log(JSON.stringify(result));return result.expiry==='within_declared_window'?0:3;
 }
 throw Error('Unsupported group command');
}
if(require.main===module){try{process.exitCode=main(process.argv.slice(2));}catch(_){console.error('Group receipt refused: invalid input, trust, signatures, permissions or prerequisites. No valid verdict issued.');process.exitCode=2;}}
module.exports={main};
