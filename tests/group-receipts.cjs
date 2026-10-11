'use strict';
const {test}=require('node:test'),assert=require('node:assert/strict'),crypto=require('node:crypto'),fs=require('node:fs'),os=require('node:os'),path=require('node:path'),{spawnSync}=require('node:child_process');
const g=require('../protocol/group-receipts.cjs'),r=require('../protocol/receipts.cjs');
function team(n=4,mixed=false){
 const keys=Array.from({length:n},(_,i)=>{const ec=mixed&&i%2;const k=crypto.generateKeyPairSync(ec?'ec':'ed25519',ec?{namedCurve:'prime256v1'}:{});return {private:k.privateKey.export({type:'pkcs8',format:'pem'}),public:k.publicKey.export({type:'spki',format:'pem'})};});
 const roster={version:g.ROSTER,public_keys:keys.map(k=>k.public)},artifact=Buffer.from('Synthetic group artifact\n');
 const manifest=g.create(artifact,roster,1000);
 const endorsements=keys.map(k=>g.endorse(manifest,k.private,true));
 return {keys,roster,artifact,manifest,endorsements,group:g.assemble(manifest,roster,endorsements)};
}
for(const n of [2,4,16])for(const mixed of [false,true])test(`${n} distinct selected keys ${mixed?'mixed Ed25519/P256':'Ed25519'} sign the exact same record`,()=>{
 const t=team(n,mixed),result=g.inspect(t.group,t.roster,t.artifact,1001);
 assert.equal(result.signer_count,n);assert.equal(result.record_integrity,'all_signatures_verified_under_selected_roster');
 assert.equal(result.revocation,'unchecked');assert.equal(result.authorship,'unestablished');assert.equal(result.distinct_people,'unestablished');assert.equal(result.certified_valid,false);assert.equal(result.tag_issuance,false);
});
test('public four-key cross-platform vector verifies under an explicit historical test clock',()=>{
 const dir=path.join(__dirname,'fixtures/group-receipt-2026'),read=name=>fs.readFileSync(path.join(dir,name));
 const evidence=r.parse(read('manifest.json'));
 for(const [name,hash] of Object.entries(evidence.files))assert.equal(r.hash(read(name)),hash);
 const group=r.parse(read('group.json')),result=g.inspect(group,r.parse(read('roster.json')),read('artifact.txt'),group.manifest.issued_at+1);
 assert.equal(result.signer_count,4);assert.equal(result.authorship,'unestablished');assert.equal(result.distinct_people,'unestablished');assert.equal(result.revocation,'unchecked');assert.equal(result.certified_valid,false);
 assert.equal(evidence.synthetic_keys_only,true);assert.equal(evidence.private_keys_never_persisted,true);
});
for(const permission of [false,undefined,null,1,'yes'])test(`explicit agreement refuses ${String(permission)}`,()=>{const t=team(2);assert.throws(()=>g.endorse(t.manifest,t.keys[0].private,permission));});
for(const change of ['artifact','signature','payload','key','missing','extra','duplicate','manifest','version','ordering','trust-roster'])test(`refuses changed ${change}`,()=>{
 const t=team(),group=JSON.parse(JSON.stringify(t.group));let artifact=t.artifact,roster=t.roster;
 if(change==='artifact')artifact=Buffer.from('different');
 if(change==='signature')group.endorsements[0].signature='AAAA'+group.endorsements[0].signature.slice(4);
 if(change==='payload')group.endorsements[0].payload='AAAA'+group.endorsements[0].payload.slice(4);
 if(change==='key')group.endorsements[0].key_sha256='a'.repeat(64);
 if(change==='missing')group.endorsements.pop();
 if(change==='extra')group.endorsements.push(team(2).endorsements[0]);
 if(change==='duplicate')group.endorsements[1]=group.endorsements[0];
 if(change==='manifest')group.manifest.group_id=crypto.randomUUID();
 if(change==='version')group.version='group-receipt/99.0.0';
 if(change==='ordering')group.endorsements.reverse();
 if(change==='trust-roster')roster=team().roster;
 assert.throws(()=>g.inspect(group,roster,artifact,1001));
});
test('different valid signed manifests cannot assemble',()=>{const t=team(),changed={...t.manifest,group_id:crypto.randomUUID()};t.endorsements[0]=g.endorse(changed,t.keys[0].private,true);assert.throws(()=>g.assemble(t.manifest,t.roster,t.endorsements));});
test('key outside selected roster cannot endorse',()=>{const t=team();assert.throws(()=>g.endorse(t.manifest,team(2).keys[0].private,true));});
for(const count of [0,1,17])test(`unsupported roster size ${count}`,()=>{const t=team(2);const roster={version:g.ROSTER,public_keys:Array.from({length:count},()=>t.keys[0].public)};assert.throws(()=>g.create(t.artifact,roster,1000));});
test('duplicate public key and unsupported RSA/private-key/appended material roster refuse',()=>{const t=team(2);for(const second of [t.keys[0].public,t.keys[1].private,t.keys[1].public+t.keys[1].private,t.keys[1].public+'appended personal material',crypto.generateKeyPairSync('rsa',{modulusLength:2048}).publicKey.export({type:'spki',format:'pem'})])assert.throws(()=>g.create(t.artifact,{version:g.ROSTER,public_keys:[t.keys[0].public,second]},1000));});
for(const field of ['authorship_proven','distinct_people_proven','tag_issuance'])test(`cannot assert ${field}`,()=>{const t=team(2);assert.throws(()=>g.endorse({...t.manifest,[field]:true},t.keys[0].private,true));});
for(const lifetime of [-1,0,59,604801,NaN,'86400'])test(`unsupported lifetime ${lifetime}`,()=>{const t=team(2);assert.throws(()=>g.create(t.artifact,t.roster,1000,lifetime));});
test('expiry, clock, UUID and input bounds',()=>{
 const t=team(2);assert.equal(g.inspect(t.group,t.roster,t.artifact,999).expiry,'not_yet_current');assert.equal(g.inspect(t.group,t.roster,t.artifact,87400).expiry,'expired');
 for(const now of [undefined,NaN,-1,'1001'])assert.throws(()=>g.inspect(t.group,t.roster,t.artifact,now));
 for(const group_id of ['________-____-4___-a___-____________',123,'not UUID'])assert.throws(()=>g.validate({...t.manifest,group_id}));
 assert.throws(()=>g.create(Buffer.alloc(g.LIMIT+1),t.roster,1000));assert.throws(()=>g.create('raw text',t.roster,1000));
 assert.throws(()=>g.inspect({...t.group,public_keys:t.roster.public_keys},t.roster,t.artifact,1001));
});
test('real independent participant CLI workflow, no private key in group and refusal safety',()=>{
 const dir=fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(),'aitrust-group-test-')));fs.chmodSync(dir,0o700);
 try{
  const t=team(4,true),file=name=>path.join(dir,name),cli=(...a)=>spawnSync(process.execPath,[path.resolve(__dirname,'../scripts/group-receipt.cjs'),...a],{encoding:'utf8'});
  fs.writeFileSync(file('artifact.txt'),t.artifact);
  for(let i=0;i<t.keys.length;i++)fs.writeFileSync(file(`public-${i}.pem`),t.keys[i].public);
  assert.equal(cli('roster',file('roster.json'),...t.keys.map((_,i)=>file(`public-${i}.pem`))).status,0);
  for(let i=0;i<t.keys.length;i++)fs.writeFileSync(file(`key-${i}.pem`),t.keys[i].private,{mode:0o600});
  assert.equal(cli('create',file('artifact.txt'),file('roster.json'),file('manifest.json')).status,0);
  assert.equal(cli('sign',file('manifest.json'),file('key-0.pem'),file('not-agreed.json')).status,2);assert(!fs.existsSync(file('not-agreed.json')));
  for(let i=0;i<t.keys.length;i++)assert.equal(cli('sign',file('manifest.json'),file(`key-${i}.pem`),file(`signature-${i}.json`),'--agree').status,0);
  const signatures=t.keys.map((_,i)=>file(`signature-${i}.json`));
  assert.equal(cli('assemble',file('manifest.json'),file('roster.json'),file('group.json'),...signatures).status,0);
  const verification=cli('verify',file('group.json'),file('roster.json'),file('artifact.txt'));assert.equal(verification.status,0);assert.equal(JSON.parse(verification.stdout).signer_count,4);
  const raw=fs.readFileSync(file('group.json'),'utf8');for(const k of t.keys)assert(!raw.includes(k.private));assert(!raw.includes(t.artifact.toString()));
  assert.equal(fs.statSync(file('group.json')).mode&0o777,0o600);
  assert.equal(cli('assemble',file('manifest.json'),file('roster.json'),file('group.json'),...signatures).status,2);
  const link=file('link');fs.symlinkSync(file('artifact.txt'),link);assert.equal(cli('verify',file('group.json'),file('roster.json'),link).status,2);
  fs.chmodSync(file('key-0.pem'),0o644);assert.equal(cli('sign',file('manifest.json'),file('key-0.pem'),file('unsafe.json'),'--agree').status,2);
  fs.writeFileSync(file('artifact.txt'),'changed');const bad=cli('verify',file('group.json'),file('roster.json'),file('artifact.txt'));assert.equal(bad.status,2);assert.equal(bad.stdout,'');assert(!bad.stderr.includes('PRIVATE KEY'));
 }finally{fs.rmSync(dir,{recursive:true,force:true});}
});
