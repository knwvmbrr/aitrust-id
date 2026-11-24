'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),crypto=require('node:crypto'),fs=require('node:fs'),os=require('node:os'),path=require('node:path'),cp=require('node:child_process');
const r=require('../protocol/receipts.cjs'),v=require('../protocol/reviewer-attestations.cjs'),cli=require('../scripts/reviewer-attestation.cjs');
// PUBLIC RFC8032 section7.1 test1/test2 seeds: no operating key generation/identity.
// https://www.rfc-editor.org/rfc/rfc8032.txt -- never trust these known test keys.
function key(second=false){return crypto.createPrivateKey({key:Buffer.from('302e020100300506032b657004220420'+(second?'4ccd089b28ff96da9db6c346ec114e0f5b8a319f35aba624da8cf6ed4fb8a6fb':'9d61b19deffd5a60ba844af492ec2cc44449c5697b326919703bac031cae7f60'),'hex'),format:'der',type:'pkcs8'}).export({format:'pem',type:'pkcs8'});}
function fixture(now=1000){
 const subject=Buffer.from('Synthetic reviewed artifact.\n'),privateKey=key(),publicKey=crypto.createPublicKey(privateKey).export({format:'pem',type:'spki'});
 const policy={profile:v.POLICY,review_id:'synthetic-review-1',reviewer:{handle:'synthetic-reviewer',public_key:publicKey},subject:{sha256:r.hash(subject),bytes:subject.length,revision:'revision-1'},scope:{id:'claim-1',version:'scope-1',statement:'Only the supplied arithmetic example was reviewed.',evidence:[{id:'evidence-1',kind:'example',sha256:r.hash(Buffer.from('1+1=2')),bytes:5}]},checkpoint:{head_sha256:v.ZERO,sequence:1,observed_at:now,valid_until:now+100}};
 const review={consent:true,human_review_declared:true,decision:'supports',conflicts:[],reviewed_at:now-20,expires_at:now+90};
 const event={profile:v.EVENT,review_id:policy.review_id,reviewer_handle:policy.reviewer.handle,subject:structuredClone(policy.subject),scope_sha256:r.hash(r.bytes(policy.scope)),sequence:1,previous_sha256:v.ZERO,action:'review',issued_at:now-10,review,replacement:null};
 const f={subject,privateKey,policy,events:[event],history:{profile:v.HISTORY,events:[]},now};return resign(f);
}
function resign(f,privateKey=f.privateKey){let previous=v.ZERO;f.history.events=f.events.map((event,i)=>{event.sequence=i+1;event.previous_sha256=previous;const e=r.sign(event,privateKey);previous=r.hash(r.bytes(e));return e;});f.policy.checkpoint.head_sha256=previous;f.policy.checkpoint.sequence=f.events.length;return f;}
function run(f,change={}){return v.verify({subject:f.subject,policy:r.bytes(f.policy),history:r.bytes(f.history),now:f.now,...change});}
function append(f,action='withdraw'){f.events.push({...f.events[0],action,issued_at:f.now-1,review:null,replacement:action==='supersede'?{review_id:'replacement-2',head_sha256:'a'.repeat(64)}:null});return resign(f);}
const refused=f=>assert.equal(run(f).state,'UNAVAILABLE');
test('real fixed PUBLIC test-key integrity yields declaration only, never IV/human independence',()=>{
 const f=fixture(),out=run(f);assert.equal(out.state,'REVIEW_RECORD_VERIFIED');assert.equal(out.review_status,'ACTIVE_DECLARATION');assert.equal(out.subject.binding,'exact_bytes_matched');assert.equal(out.attributed_review.decision,'supports');assert.equal(out.scope.evidence_reference_count,1);
 for(const k of ['tag_issuance','IV_asserted','human_identity_established','reviewer_independence_established','accuracy_established','independent_timestamp','global_revocation_or_withdrawal_completeness'])assert.equal(out[k],false);
 assert.equal(crypto.createPublicKey(f.privateKey).export({format:'der',type:'spki'}).subarray(-32).toString('hex'),'d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a');
 assert(!JSON.stringify(out).includes(f.subject.toString()));
});
test('exact subject bytes and independently selected revision are mandatory',()=>{const f=fixture();assert.equal(run(f,{subject:Buffer.from('changed')}).state,'UNAVAILABLE');f.policy.subject.revision='other';refused(f);});
test('scope, evidence and reviewer handle cannot be rebound by received signed record',()=>{for(const field of ['statement','version','evidence']){const f=fixture();if(field==='evidence')f.policy.scope.evidence[0].sha256='a'.repeat(64);else f.policy.scope[field]='other';refused(f);}const f=fixture();f.policy.reviewer.handle='other';refused(f);});
test('explicit consent and human self-declaration are required without proving either',()=>{for(const k of ['consent','human_review_declared'])for(const bad of [false,1,'yes',null]){const f=fixture();f.events[0].review[k]=bad;resign(f);refused(f);}});
test('untrusted signature, tampering, payload canonicalization and private/appended public keys refuse',()=>{
 let f=fixture();resign(f,key(true));refused(f);f=fixture();f.history.events[0].signature=Buffer.alloc(64).toString('base64');refused(f);
 for(const pem of [key(),fixture().policy.reviewer.public_key+'extra']){f=fixture();f.policy.reviewer.public_key=pem;refused(f);}
 f=fixture();const e=f.history.events[0],raw=Buffer.from(JSON.stringify(f.events[0],null,2));e.payload=raw.toString('base64');e.signature=crypto.sign(null,raw,f.privateKey).toString('base64');f.policy.checkpoint.head_sha256=r.hash(r.bytes(e));refused(f);
});
test('expiry and explicit conflict remain verified but inactive; inconclusive is attributed only',()=>{
 const f=fixture();f.events[0].review.expires_at=f.now;resign(f);assert.equal(run(f).review_status,'EXPIRED');assert.equal(run(f).active_review,false);
 f.events[0].review.expires_at=f.now+10;f.events[0].review.conflicts=['paid_by_subject'];resign(f);assert.equal(run(f).review_status,'CONFLICT_DISCLOSED');assert.equal(run(f).active_review,false);
 f.events[0].review.conflicts=[];f.events[0].review.decision='inconclusive';resign(f);assert.equal(run(f).attributed_review.decision,'inconclusive');assert.equal(run(f).IV_asserted,false);
});
test('withdrawal and supersession are terminal and replacement is not fetched/blessed',()=>{for(const action of ['withdraw','supersede']){const f=append(fixture(),action);const out=run(f);assert.equal(out.review_status,action==='withdraw'?'WITHDRAWN':'SUPERSEDED');assert.equal(out.active_review,false);f.events.push({...f.events[0],issued_at:f.now});resign(f);refused(f);}});
test('trusted external head rejects truncation/reorder/fork/missing and duplicate events',()=>{
 let f=append(fixture());f.history.events.pop();refused(f);f=append(fixture());f.history.events.reverse();refused(f);f=append(fixture());f.history.events[1]=f.history.events[0];refused(f);f=fixture();f.policy.checkpoint.head_sha256='b'.repeat(64);refused(f);
});
test('future events, stale/unopened checkpoints, nonmonotonic event clocks refuse',()=>{for(const modify of [f=>f.events[0].issued_at=f.now+1,f=>f.policy.checkpoint.valid_until=f.now,f=>f.policy.checkpoint.observed_at=f.now+1]){const f=fixture();modify(f);resign(f);refused(f);}const f=append(fixture());f.events[1].issued_at=f.events[0].issued_at-1;resign(f);refused(f);});
test('strict fields/numbers/duplicate JSON and bounded counts refuse',()=>{
 let f=fixture();assert.equal(run(f,{policy:Buffer.from('{"profile":1,"profile":2}')}).state,'UNAVAILABLE');assert.equal(run(f,{history:Buffer.alloc(v.MAX_HISTORY+1)}).state,'UNAVAILABLE');assert.equal(run(f,{subject:Buffer.alloc(v.MAX_SUBJECT+1)}).state,'UNAVAILABLE');
 for(const mutate of [f=>f.policy.checkpoint.sequence=true,f=>f.policy.extra=true]){f=fixture();mutate(f);refused(f);}
 for(const mutate of [f=>f.events[0].review.expires_at=true,f=>f.events[0].review.conflicts=['same','same'],f=>f.events[0].unknown=true]){f=fixture();mutate(f);resign(f);refused(f);}
 f=fixture();f.history.events=Array(129).fill(f.history.events[0]);refused(f);
});
test('saturated closed history cannot damage subsequent independent verification',()=>{const f=fixture();f.history.events=Array(129).fill(f.history.events[0]);refused(f);assert.equal(run(fixture()).state,'REVIEW_RECORD_VERIFIED');});
test('cooperative monotonic deadline and clock rollback produce fixed Unavailable',t=>{
 const {performance}=require('node:perf_hooks');let n=0;t.mock.method(performance,'now',()=>n++===0?0:6000);assert.equal(run(fixture()).reason,'deadline_exceeded');t.mock.restoreAll();t.mock.method(performance,'now',()=>{throw Error('clock unavailable');});assert.equal(run(fixture()).state,'UNAVAILABLE');t.mock.restoreAll();let x=100;t.mock.method(performance,'now',()=>x--);assert.equal(run(fixture()).reason,'deadline_exceeded');
});
function files(f,dir){for(const [name,raw]of [['policy.json',r.bytes(f.policy)],['history.json',r.bytes(f.history)],['subject.txt',f.subject]])fs.writeFileSync(path.join(dir,name),raw,{mode:0o600});}
function invoke(dir,...args){return cp.spawnSync(process.execPath,[path.resolve(__dirname,'../scripts/reviewer-attestation.cjs'),...(args.length?args:['verify',path.join(dir,'policy.json'),path.join(dir,'history.json'),path.join(dir,'subject.txt')])],{encoding:'utf8',timeout:10000,maxBuffer:65536});}
test('actual CLI positive, verified withdrawal, tamper refusal and approachable help',()=>{
 const dir=fs.mkdtempSync(path.join(fs.realpathSync(os.tmpdir()),'iv-review-test-'));try{
  const f=fixture(Math.floor(Date.now()/1000));files(f,dir);let p=invoke(dir);assert.equal(p.status,0,p.stderr);assert.equal(JSON.parse(p.stdout).review_status,'ACTIVE_DECLARATION');
  append(f);files(f,dir);p=invoke(dir);assert.equal(p.status,3,p.stderr);assert.equal(JSON.parse(p.stdout).review_status,'WITHDRAWN');
  fs.writeFileSync(path.join(dir,'subject.txt'),'private canary not for output');p=invoke(dir);assert.equal(p.status,2);assert.equal(JSON.parse(p.stdout).state,'UNAVAILABLE');assert(!p.stdout.includes('private canary'));assert(!p.stderr.includes(dir));
  p=invoke(dir,'--help');assert.equal(p.status,0);assert(p.stdout.includes('trusted-policy.json'));assert(p.stdout.includes('unestablished human independence'));
 }finally{fs.rmSync(dir,{recursive:true,force:true});}
});
test('actual received symlink, FIFO and oversized file refuse promptly without reading',()=>{
 const dir=fs.mkdtempSync(path.join(fs.realpathSync(os.tmpdir()),'iv-input-test-'));try{const f=fixture(Math.floor(Date.now()/1000));files(f,dir);fs.unlinkSync(path.join(dir,'policy.json'));fs.symlinkSync(path.join(dir,'history.json'),path.join(dir,'policy.json'));assert.equal(invoke(dir).status,2);fs.unlinkSync(path.join(dir,'policy.json'));cp.execFileSync('/usr/bin/mkfifo',[path.join(dir,'policy.json')]);assert.equal(invoke(dir).status,2);fs.unlinkSync(path.join(dir,'policy.json'));fs.writeFileSync(path.join(dir,'policy.json'),Buffer.alloc(v.MAX_POLICY+1));assert.equal(invoke(dir).status,2);}finally{fs.rmSync(dir,{recursive:true,force:true});}
});
test('captured input drift and independently attempted close failures refuse',()=>{
 const dir=fs.mkdtempSync(path.join(fs.realpathSync(os.tmpdir()),'iv-input-test-'));try{const file=path.join(dir,'x');fs.writeFileSync(file,'old');const inputs=new cli.Inputs();inputs.read(file,10);fs.writeFileSync(file,'new');assert.throws(()=>inputs.check());const expected=inputs.fds.length,real=fs.closeSync;let count=0;fs.closeSync=fd=>{real(fd);if(++count===1)throw Error('post-close');};try{assert.throws(()=>inputs.close());assert.equal(count,expected);assert.equal(inputs.fds.length,0);inputs.close();}finally{fs.closeSync=real;}}finally{fs.rmSync(dir,{recursive:true,force:true});}
});

test('CLI original clock rejects nonfinite startup, monotonic rollback and exhausted total window',t=>{
 const {performance}=require('node:perf_hooks');t.mock.method(performance,'now',()=>NaN);assert.throws(()=>new cli.Inputs());t.mock.restoreAll();
 let values=[0,100,99];t.mock.method(performance,'now',()=>values.shift());const a=new cli.Inputs();a.tick();assert.throws(()=>a.tick());a.close();t.mock.restoreAll();
 values=[0,5001];t.mock.method(performance,'now',()=>values.shift());const b=new cli.Inputs();assert.throws(()=>b.tick());b.close();
});
