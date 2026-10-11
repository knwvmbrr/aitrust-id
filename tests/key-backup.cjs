'use strict';
const {test}=require('node:test'),assert=require('node:assert/strict'),crypto=require('node:crypto'),fs=require('node:fs'),os=require('node:os'),path=require('node:path');
const {spawnSync}=require('node:child_process'),{PassThrough}=require('node:stream');
const k=require('../protocol/key-backup.cjs'),r=require('../protocol/receipts.cjs'),cli=require('../scripts/key-backup.cjs');
const root=path.resolve(__dirname,'..'),pass=Buffer.from('Synthetic test password 123');
function pair(ec=false){const key=crypto.generateKeyPairSync(ec?'ec':'ed25519',ec?{namedCurve:'prime256v1'}:{});return {private:Buffer.from(key.privateKey.export({type:'pkcs8',format:'pem'})),public:Buffer.from(key.publicKey.export({type:'spki',format:'pem'}))};}
function observation(artifact){const s=require('../tools/composition/core.cjs').create();s.start(0);s.event({kind:'edit',at:1,before:0,after:artifact.toString().length,position:0,removed:0,added:artifact.toString().length,input:'paste'});s.pause(2);return {...s.snapshot(),source_sha256:r.hash(fs.readFileSync(path.join(root,'tools/composition/core.cjs'))),artifact_sha256:r.hash(artifact),artifact_encoding:'UTF-8; exact editor value; no normalization'};}
for(const ec of [false,true]){
 test(`${ec?'P256':'Ed25519'} restore preserves exact key and verifies a receipt`,()=>{
  const key=pair(ec),artifact=Buffer.from('Synthetic recovery artifact'),record=k.backup(key.private,pass);
  const before=Buffer.from(key.private),restored=k.restore(k.parse(r.bytes(record)),pass,key.public);
  assert(restored.equals(before));assert(key.private.equals(before));
  const signed=r.sign(r.receipt(artifact,observation(artifact),1000),restored);
  const result=r.inspectReceipt(signed,key.public,artifact,1001);
  assert.equal(result.record_integrity,'verified_under_pinned_key');assert.equal(result.authorship,'unestablished');assert.equal(result.certified_valid,false);
  assert(!r.bytes(record).includes(key.private));assert(!r.bytes(record).includes(pass));restored.fill(0);
 });
 test(`${ec?'P256':'Ed25519'} salt and nonce differ for separate backups`,()=>{
  const key=pair(ec),one=k.backup(key.private,pass),two=k.backup(key.private,pass);
  assert.notEqual(one.kdf.salt,two.kdf.salt);assert.notEqual(one.cipher.nonce,two.cipher.nonce);assert.notEqual(one.ciphertext,two.ciphertext);
 });
 test(`${ec?'P256':'Ed25519'} wrong password and separately selected key are refused`,()=>{
  const key=pair(ec),record=k.backup(key.private,pass);
  assert.throws(()=>k.restore(record,Buffer.from('Wrong synthetic password'),key.public));
  assert.throws(()=>k.restore(record,pass,pair(ec).public));assert.throws(()=>k.restore(record,pass,key.private));
 });
}
for(const field of ['ciphertext','authentication_tag','salt','nonce','key_sha256','algorithm','version','N','r','p','bytes','kdf_name','cipher_name','unknown_field','missing_field'])test('tampered/unsupported '+field+' fails closed',()=>{
 const key=pair(),record=k.backup(key.private,pass);
 if(['ciphertext','authentication_tag'].includes(field))record[field]='AAAA'+record[field].slice(4);
 else if(field==='salt')record.kdf.salt='AAAA'+record.kdf.salt.slice(4);
 else if(field==='nonce')record.cipher.nonce='AAAA'+record.cipher.nonce.slice(4);
 else if(['N','r','p','bytes'].includes(field))record.kdf[field]++;
 else if(field==='kdf_name')record.kdf.name='PBKDF2';
 else if(field==='cipher_name')record.cipher.name='AES-256-CBC';
 else if(field==='unknown_field')record.claim='authorship';
 else if(field==='missing_field')delete record.authentication_tag;
 else record[field]='changed';
 assert.throws(()=>k.restore(record,pass,key.public));
});
for(const value of ['', 'short', '             ', ' space before123', 'space after123 ', 'a'.repeat(1025), 'password\n12345','password\x0012345','😀😀😀😀'])test('unsupported password form '+JSON.stringify(value.slice(0,20)),()=>assert.throws(()=>k.password(Buffer.from(value))));
test('Unicode passwords retain exact bytes without implicit normalization',()=>{
 const key=pair(),pw=Buffer.from('éééééééééééé'),record=k.backup(key.private,pw);
 assert(k.restore(record,pw,key.public).equals(key.private));assert.throws(()=>k.restore(record,Buffer.from('é'.repeat(12)),key.public));
 assert.throws(()=>k.password(Buffer.from([255])));
});
test('RSA, appended keys, malformed PEM and oversized keys are unsupported',()=>{
 const key=pair(),rsa=crypto.generateKeyPairSync('rsa',{modulusLength:2048});
 for(const raw of [Buffer.from(rsa.privateKey.export({type:'pkcs8',format:'pem'})),Buffer.concat([key.private,key.public]),Buffer.alloc(4097),Buffer.from('bad'),Buffer.from(key.private.toString().replaceAll('\n','\r\n'))])assert.throws(()=>k.backup(raw,pass));
 for(const raw of [Buffer.concat([key.public,key.private]),Buffer.from(rsa.publicKey.export({type:'spki',format:'pem'}))])assert.throws(()=>k.pem(raw,false));
});
for(const raw of [Buffer.from('{"version":1,"version":2}'),Buffer.alloc(8193),Buffer.from([255])])test('ambiguous/bounded input '+raw.length,()=>assert.throws(()=>k.parse(raw)));
test('encoded fields reject oversized, noncanonical and wrong byte lengths',()=>{
 const key=pair(),record=k.backup(key.private,pass);
 for(const text of ['','a'.repeat(100000),'A===',record.ciphertext+'===='])assert.throws(()=>k.restore({...record,ciphertext:text},pass,key.public));
});
test('complete CLI backup, check, restore and recovered-key issuance without leaking secrets',()=>{
 const dir=fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(),'aitrust-custody-test-')));fs.chmodSync(dir,0o700);
 const file=name=>path.join(dir,name),run=(...a)=>spawnSync(process.execPath,['scripts/key-backup.cjs',...a],{cwd:root,encoding:'utf8'});
 try{
  fs.writeFileSync(file('password'),pass,{mode:0o600});
  for(const ec of [false,true]){
   const id=ec?'p256':'ed',key=pair(ec),priv=file(id+'.pem'),pub=file(id+'.public.pem'),backup=file(id+'.backup.json'),restored=file(id+'.restored.pem');
   fs.writeFileSync(priv,key.private,{mode:0o600});fs.writeFileSync(pub,key.public,{mode:0o600});
   for(const a of [['backup',priv,backup],['check',backup,pub],['restore',backup,pub,restored]]){
    const result=run(...a,'--password-file',file('password'));assert.equal(result.status,0,result.stderr);
    assert(!result.stdout.includes(pass.toString()));assert(!result.stderr.includes(pass.toString()));assert(!result.stdout.includes('PRIVATE KEY'));
   }
   assert(fs.readFileSync(restored).equals(key.private));for(const f of [backup,restored])assert.equal(fs.statSync(f).mode&0o777,0o600);
   assert.equal(run('backup',priv,backup,'--password-file',file('password')).status,2);
   assert.equal(run('restore',backup,pub,restored,'--password-file',file('password')).status,2);
   const artifact=Buffer.from('Synthetic CLI artifact');fs.writeFileSync(file('artifact'),artifact);fs.writeFileSync(file('observation'),r.bytes(observation(artifact)));
   const issue=spawnSync(process.execPath,['scripts/receipt.cjs','issue',file('artifact'),file('observation'),restored,file(id+'.receipt')],{cwd:root,encoding:'utf8'});assert.equal(issue.status,0,issue.stderr);
   const verify=spawnSync(process.execPath,['scripts/receipt.cjs','verify',file(id+'.receipt'),pub,file('artifact')],{cwd:root,encoding:'utf8'});assert.equal(verify.status,0,verify.stderr);assert.equal(JSON.parse(verify.stdout).certified_valid,false);
  }
  const before=fs.readdirSync(dir).sort();assert.equal(run('backup',file('ed.pem'),file('cancelled')).status,2);assert.deepEqual(fs.readdirSync(dir).sort(),before);
  fs.chmodSync(file('password'),0o644);assert.equal(run('backup',file('ed.pem'),file('unsafe'),'--password-file',file('password')).status,2);fs.chmodSync(file('password'),0o600);
  for(const kind of ['key','password','backup','public']){
   const from={key:'ed.pem',password:'password',backup:'ed.backup.json',public:'ed.public.pem'}[kind],link=file('symlink-'+kind);fs.symlinkSync(file(from),link);
   const a=kind==='key'?['backup',link,file('unsafe')]:kind==='backup'?['check',link,file('ed.public.pem')]:['check',file('ed.backup.json'),kind==='public'?link:file('ed.public.pem')];
   assert.equal(run(...a,'--password-file',kind==='password'?link:file('password')).status,2);
  }
  fs.chmodSync(file('ed.pem'),0o644);assert.equal(run('backup',file('ed.pem'),file('unsafe'),'--password-file',file('password')).status,2);
  assert(!fs.existsSync(file('unsafe')));
 }finally{fs.rmSync(dir,{recursive:true,force:true});}
});
test('unsafe output directory, repository destination and output symlink are refused',()=>{
 const dir=fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(),'aitrust-custody-dir-')));fs.chmodSync(dir,0o700);
 try{
  assert.throws(()=>cli.destination(path.join(root,'should-not-exist.pem')));
  const link=path.join(dir,'linked-dir');fs.symlinkSync(dir,link);assert.throws(()=>cli.destination(path.join(link,'new')));
  const file=path.join(dir,'existing');fs.writeFileSync(file,'untouched');assert.throws(()=>cli.destination(file));
  fs.symlinkSync(file,path.join(dir,'output-link'));assert.throws(()=>cli.destination(path.join(dir,'output-link')));
  fs.chmodSync(dir,0o755);assert.throws(()=>cli.destination(path.join(dir,'new')));
  assert.equal(fs.readFileSync(file,'utf8'),'untouched');
 }finally{fs.rmSync(dir,{recursive:true,force:true});}
});
function terminal(){const input=new PassThrough();input.isTTY=true;input.isRaw=false;input.setRawMode=v=>{input.isRaw=v;};let text='';const output={write:s=>{text+=s;}};return {input,output,get text(){return text;}};}
test('hidden terminal entry emits no password and restores input mode',async()=>{
 const t=terminal(),promise=cli.hidden('Synthetic password prompt: ',t.input,t.output);
 t.input.emit('keypress','Synthetic secret',{});t.input.emit('keypress','',{name:'return'});
 const value=await promise;assert.equal(value.toString(),'Synthetic secret');assert(!t.text.includes('Synthetic secret'));assert.equal(t.input.isRaw,false);assert.equal(t.input.listenerCount('keypress'),0);value.fill(0);
});
test('hidden terminal backspace preserves Unicode characters and ignores navigation',async()=>{
 const t=terminal(),promise=cli.hidden('Prompt: ',t.input,t.output);
 t.input.emit('keypress','😀a',{});t.input.emit('keypress','',{name:'backspace'});t.input.emit('keypress','\x1b[A',{name:'up',sequence:'\x1b[A'});t.input.emit('keypress','b',{});t.input.emit('keypress','',{name:'return'});
 assert.equal((await promise).toString(),'😀b');assert.equal(t.input.isRaw,false);
});
for(const event of ['control-c','escape','input-end'])test('hidden terminal cancellation '+event,async()=>{
 const t=terminal(),promise=cli.hidden('Prompt: ',t.input,t.output);
 if(event==='input-end')t.input.emit('end');else t.input.emit('keypress','',{ctrl:event==='control-c',name:event==='escape'?'escape':'c'});
 await assert.rejects(promise);assert.equal(t.input.isRaw,false);assert.equal(t.input.listenerCount('keypress'),0);
});
test('hidden input refuses absent terminal and excessively long password',async()=>{
 await assert.rejects(cli.hidden('Prompt',new PassThrough(),{write:()=>{}}));
 const t=terminal(),promise=cli.hidden('Prompt',t.input,t.output);t.input.emit('keypress','x'.repeat(1025),{});await assert.rejects(promise);assert.equal(t.input.isRaw,false);
});
for(const fault of ['writeFileSync','fsyncSync','closeSync','linkSync'])test('failed '+fault+' leaves no final key or temporary file and permits retry',()=>{
 const dir=fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(),'aitrust-key-io-')));fs.chmodSync(dir,0o700);
 try{
  const file=path.join(dir,'restored.pem'),key=pair().private;let failed=false;
  const io=new Proxy(fs,{get(target,name){if(name===fault)return (...args)=>{if(!failed){failed=true;if(fault==='writeFileSync')fs.writeSync(args[0],key.subarray(0,10));const error=Error('Synthetic private output I/O failure');error.code=fault==='writeFileSync'?'ENOSPC':'EIO';throw error;}return target[name](...args);};return target[name];}});
  assert.throws(()=>cli.publish(file,key,io));assert.equal(fs.existsSync(file),false);assert.deepEqual(fs.readdirSync(dir),[]);
  cli.publish(file,key);assert(fs.readFileSync(file).equals(key));assert.equal(fs.statSync(file).mode&0o777,0o600);assert.deepEqual(fs.readdirSync(dir),['restored.pem']);
 }finally{fs.rmSync(dir,{recursive:true,force:true});}
});
test('a concurrent destination is preserved without accepting this key',()=>{
 const dir=fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(),'aitrust-key-race-')));fs.chmodSync(dir,0o700);
 try{
  const file=path.join(dir,'other-writer.pem'),io=new Proxy(fs,{get(target,name){if(name==='linkSync')return (...args)=>{fs.writeFileSync(file,'Other writer owns these bytes',{mode:0o600});return target.linkSync(...args);};return target[name];}});
  assert.throws(()=>cli.publish(file,pair().private,io));assert.equal(fs.readFileSync(file,'utf8'),'Other writer owns these bytes');assert.deepEqual(fs.readdirSync(dir),['other-writer.pem']);
 }finally{fs.rmSync(dir,{recursive:true,force:true});}
});
test('temporary cleanup failure is explicit and rolls back the published final key',()=>{
 const dir=fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(),'aitrust-key-cleanup-')));fs.chmodSync(dir,0o700);
 try{
  const file=path.join(dir,'restored.pem'),io=new Proxy(fs,{get(target,name){if(name==='unlinkSync')return (...args)=>{if(args[0]!==file){const error=Error('Synthetic denied cleanup');error.code='EACCES';throw error;}return target.unlinkSync(...args);};return target[name];}});
  assert.throws(()=>cli.publish(file,pair().private,io),error=>error.code==='AITRUST_PRIVATE_CLEANUP');assert(!fs.existsSync(file));
  const remaining=fs.readdirSync(dir);assert.equal(remaining.length,1);assert.notEqual(remaining[0],'restored.pem');assert.equal(fs.statSync(path.join(dir,remaining[0])).mode&0o777,0o600);
 }finally{fs.rmSync(dir,{recursive:true,force:true});}
});
test('atomic publication preserves an existing dangling destination symlink',()=>{
 const dir=fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(),'aitrust-key-dangling-')));fs.chmodSync(dir,0o700);
 try{
  const file=path.join(dir,'dangling.pem');fs.symlinkSync(path.join(dir,'missing.pem'),file);
  assert.throws(()=>cli.publish(file,pair().private));assert(fs.lstatSync(file).isSymbolicLink());assert.deepEqual(fs.readdirSync(dir),['dangling.pem']);
 }finally{fs.rmSync(dir,{recursive:true,force:true});}
});
test('initial receipt key writer uses the same synced publication and permits retry after I/O failure',()=>{
 const dir=fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(),'aitrust-initial-key-')));fs.chmodSync(dir,0o700);
 const write=require('../scripts/receipt.cjs').write,original=fs.fsyncSync;
 try{
  const file=path.join(dir,'initial-private.pem'),key=pair().private;
  fs.fsyncSync=()=>{const error=Error('Synthetic initial key sync failure');error.code='EIO';throw error;};
  try{assert.throws(()=>write(file,key,true));}finally{fs.fsyncSync=original;}
  assert(!fs.existsSync(file));assert.deepEqual(fs.readdirSync(dir),[]);
  write(file,key,true);assert(fs.readFileSync(file).equals(key));assert.equal(fs.statSync(file).mode&0o777,0o600);
 }finally{fs.fsyncSync=original;fs.rmSync(dir,{recursive:true,force:true});}
});
test('a restrictive owner umask cannot make the restored key unreadable',()=>{
 const dir=fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(),'aitrust-key-umask-')));fs.chmodSync(dir,0o700);const previous=process.umask(0o777);
 try{const file=path.join(dir,'restored.pem'),key=pair().private;cli.publish(file,key);assert.equal(fs.statSync(file).mode&0o777,0o600);assert(fs.readFileSync(file).equals(key));}
 finally{process.umask(previous);fs.rmSync(dir,{recursive:true,force:true});}
});
