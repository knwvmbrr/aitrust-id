// Owned disposable paths: no private evidence or real browser needed.
const fs=require('node:fs'),os=require('node:os'),path=require('node:path'),assert=require('node:assert/strict');
const {receiptPath,captureReplayDownload,validateDownloadedReplay}=require('./verify-replay-export.cjs');
const {spawnSync}=require('node:child_process'),crypto=require('node:crypto');
const root=fs.mkdtempSync(path.join(os.tmpdir(),'aitrust-replay-input-'));
try {
 fs.mkdirSync(path.join(root,'runs'));
 const file=path.join(root,'runs','fixture.json');fs.writeFileSync(file,'{}');
 assert.equal(receiptPath('runs/fixture.json',root),file);
 let refused=0;
 for(const value of [null,'/private/credential.json','../credential.json','runs/../credential.json','runs/fixture.json/other','runs/not-there.json']){
  assert.throws(()=>receiptPath(value,root));refused++;
 }
 fs.symlinkSync(file,path.join(root,'runs','linked.json'));
 assert.throws(()=>receiptPath('runs/linked.json',root));refused++;
 fs.writeFileSync(file,Buffer.alloc(2000001));
 assert.throws(()=>receiptPath('runs/fixture.json',root));refused++;
 const repo=path.resolve(__dirname,'..'),python=process.env.AITRUST_PYTHON||process.env.AITRUST_VERIFY_PYTHON||'python3';
 const selected=JSON.parse(fs.readFileSync(path.join(repo,'eval/route-boundaries.json'))).replay_evidence;
 const fixture=JSON.parse(fs.readFileSync(receiptPath(selected,repo))).synthetic_browser_fixture;
 const bytes=Buffer.from(JSON.stringify(fixture)),download=path.join(root,'download.json');fs.writeFileSync(download,bytes,{mode:0o600});
 assert(captureReplayDownload(download).equals(bytes));
 let ownedFd,called=0;
 const observing=(command,args,options)=>{called++;assert.equal(command,python);assert.equal(args.length,2);assert.equal(args[0],'-c');assert(!args.some(v=>v.includes(download)||v.includes(bytes.toString())));assert.equal(options.timeout,10000);assert.equal(options.maxBuffer,4096);assert.equal(options.killSignal,'SIGKILL');assert(!Object.hasOwn(options,'input'));ownedFd=options.stdio[0];assert(fs.fstatSync(ownedFd).isFile());return spawnSync(command,args,options);};
 assert.equal(validateDownloadedReplay(download,bytes,python,repo,observing),crypto.createHash('sha256').update(bytes).digest('hex'));assert.equal(called,1);assert.throws(()=>fs.fstatSync(ownedFd),{code:'EBADF'});
 let controls=1;
 assert.throws(()=>validateDownloadedReplay(download,Buffer.from('{}'),python,repo),/^Error: Downloaded replay validation unavailable$/);controls++;
 fs.writeFileSync(download,'{}');assert.throws(()=>validateDownloadedReplay(download,Buffer.from('{}'),python,repo),/^Error: Downloaded replay validation unavailable$/);controls++;
 const changed=structuredClone(fixture);changed.evaluator.models[0].sha256='0'.repeat(64);const changedBytes=Buffer.from(JSON.stringify(changed));fs.writeFileSync(download,changedBytes);assert.throws(()=>validateDownloadedReplay(download,changedBytes,python,repo),/^Error: Downloaded replay validation unavailable$/);controls++;
 fs.writeFileSync(download,bytes);
 assert.throws(()=>validateDownloadedReplay(download,bytes,python,repo,()=>({status:0,signal:null,stdout:'validated '+'0'.repeat(64),stderr:''})));controls++;
 assert.throws(()=>validateDownloadedReplay(download,bytes,python,repo,()=>({status:0,signal:null,stdout:'validated '+crypto.createHash('sha256').update(bytes).digest('hex'),stderr:'PRIVATE_CHILD_DIAGNOSTIC'})));controls++;
 let timedout=false;
 assert.throws(()=>validateDownloadedReplay(download,bytes,python,repo,(command,args,options)=>{const result=spawnSync(command,['-c','import time;time.sleep(2)'],{...options,timeout:40});timedout=result.error?.code==='ETIMEDOUT'&&result.signal==='SIGKILL';return result;}));assert(timedout);controls++;
 let outputBounded=false;
 assert.throws(()=>validateDownloadedReplay(download,bytes,python,repo,(command,args,options)=>{const result=spawnSync(command,['-c','print("x"*5000)'],options);outputBounded=Boolean(result.error);return result;}));assert(outputBounded);controls++;
 assert.throws(()=>validateDownloadedReplay(download,bytes,python,repo,(command,args,options)=>{const result=spawnSync(command,args,options);fs.writeFileSync(download,Buffer.from('changed'));return result;}));controls++;
 fs.writeFileSync(download,bytes);const linked=path.join(root,'download-link.json');fs.symlinkSync(download,linked);assert.throws(()=>captureReplayDownload(linked),/^Error: Downloaded replay capture unavailable$/);assert.throws(()=>validateDownloadedReplay(linked,bytes,python,repo));controls++;
 const hard=path.join(root,'download-hard.json');fs.linkSync(download,hard);assert.throws(()=>captureReplayDownload(download));fs.unlinkSync(hard);controls++;
 fs.writeFileSync(download,Buffer.alloc(2000001));assert.throws(()=>captureReplayDownload(download));assert.throws(()=>validateDownloadedReplay(download,Buffer.alloc(2000001),python,repo));controls++;
 fs.writeFileSync(download,Buffer.alloc(0));assert.throws(()=>captureReplayDownload(download));controls++;
 assert.throws(()=>validateDownloadedReplay(path.join(root,'PRIVATE_MISSING_FILE'),bytes,python,repo),/^Error: Downloaded replay validation unavailable$/);controls++;
 console.log(JSON.stringify({pass:true,public_receipt_accepted:true,unsafe_receipts_refused:refused,actual_regular_file_validator_passed:true,bounded_transport_controls:controls,actual_hung_child_killed:true,exact_schema_and_digest_checks_retained:true,independent_accuracy_evidence:false}));
} finally {fs.rmSync(root,{recursive:true,force:true});}
