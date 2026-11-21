const test=require('node:test'),assert=require('node:assert/strict');
const {spawnSync}=require('node:child_process');
const fs=require('node:fs'),os=require('node:os'),path=require('node:path');
const {classifyChild,createStageDiagnostics,runCommands}=require('../scripts/verify-nf-client.cjs');
const {writeReport}=require('../scripts/execution-report.cjs');
test('typed outcomes distinguish deadline, startup, signal and ordinary exit without diagnostic text',()=>{
 const rows=[
  [{error:{code:'ETIMEDOUT',message:'/PRIVATE/input'},signal:'SIGTERM',status:null},'deadline','ETIMEDOUT'],
  [{error:{code:'ENOENT',path:'/PRIVATE/input'},signal:null,status:null},'startup_error','ENOENT'],
  [{error:{code:'EACCES'},signal:null,status:null},'startup_error','EACCES'],
  [{error:{code:'PRIVATE_SECRET'},signal:null,status:null},'process_error','OTHER'],
  [{signal:'SIGKILL',status:null},'signal',null],
  [{signal:'PRIVATE_SECRET',status:null},'signal',null],
  [{signal:null,status:2},'exit_status',null],
  [{signal:null,status:0},'success',null],
  [{signal:null,status:null},'invalid_result',null]
 ];
 for(const [input,outcome,code] of rows){const value=classifyChild(input,12.3);assert.equal(value.outcome,outcome);assert.equal(value.error_code,code);assert.equal(value.elapsed_ms,12);assert(!JSON.stringify(value).includes('PRIVATE'));}
 assert.deepEqual(classifyChild(null,NaN),{outcome:'invalid_result',error_code:null,signal:null,status:null,elapsed_ms:0});
});
test('actual bounded inert child yields deadline rather than assertion failure',()=>{
 const started=performance.now();const result=spawnSync(process.execPath,['-e','setInterval(()=>{},1000)'],{timeout:80,stdio:'ignore'});
 const value=classifyChild(result,performance.now()-started);assert.equal(value.outcome,'deadline');assert.equal(value.error_code,'ETIMEDOUT');assert(value.elapsed_ms>=50&&value.elapsed_ms<5000);
});
test('runner stops at actual typed failure and retains fixed command identity and original budget',()=>{
 let time=100,calls=0;const observations=[];
 const ok=runCommands({clock:()=>time,spawn:(executable,args,options)=>{calls++;assert.equal(executable,process.execPath);time+=7;return calls===3?{error:{code:'ETIMEDOUT',message:'/PRIVATE'},signal:'SIGTERM',status:null}:{status:0,signal:null};},record:v=>observations.push(structuredClone(v))});
 assert.equal(ok,false);assert.equal(calls,3);assert.equal(observations.length,3);const last=observations.at(-1);assert.equal(last.pass,false);assert.deepEqual(last.commands.map(v=>v.timeout_ms),[90000,30000,180000]);assert.equal(last.commands.at(-1).command_id,'canonical_browser');assert.equal(last.commands.at(-1).outcome,'deadline');assert(!JSON.stringify(last).includes('PRIVATE'));
});
test('runner only claims completion after every unchanged command succeeds',()=>{
 const records=[];let time=0;
 assert(runCommands({clock:()=>time++,spawn:()=>({status:0,signal:null}),record:v=>records.push(structuredClone(v))}));
 assert.equal(records.length,4);assert(records.slice(0,3).every(v=>!v.pass));assert.equal(records[3].pass,true);assert.equal(records[3].commands[3].timeout_ms,120000);
});
test('throwing startup transport and malformed process fields never leak private diagnostics',()=>{
 const records=[];assert.equal(runCommands({spawn:()=>{throw Error('/PRIVATE/path payload');},record:v=>records.push(structuredClone(v))}),false);
 assert.equal(records[0].commands[0].outcome,'process_error');assert(!JSON.stringify(records).includes('PRIVATE'));
 assert.equal(classifyChild({status:Infinity,signal:null},1).outcome,'invalid_result');
});
test('browser stage sequence records exact substep timing while interrupted work remains incomplete',()=>{
 let time=0;const records=[];const d=createStageDiagnostics({clock:()=>time,record:v=>records.push(v)});
 time=5;d.enter('WebKit','invalid_cosine_then_literal','cosine_alert_wait');time=15;d.enter('WebKit','invalid_cosine_then_literal','cosine_alert_observed');time=25;d.enter('WebKit','invalid_cosine_then_literal','literal_submit');time=35;d.enter('WebKit','invalid_cosine_then_literal','literal_result_wait');
 assert.equal(records.at(-1).completed,false);assert.equal(records.at(-1).last.stage_elapsed_ms,30);assert.equal(records.at(-1).last.since_previous_ms,10);assert.equal(records.at(-1).last.substep,'literal_result_wait');
 d.enter('WebKit','complete','complete');assert.equal(records.at(-1).completed,true);
});
test('closed browser diagnostics reject private strings, unknown phases and unbounded indices',()=>{
 const records=[];const d=createStageDiagnostics({record:v=>records.push(v)});
 for(const args of [['PRIVATE','mount'],['WebKit','PRIVATE'],['WebKit','mount','PRIVATE'],['WebKit','whole_record_parity','case_begin',33],['WebKit','whole_record_parity','case_begin',-1]])assert.throws(()=>d.enter(...args),/^Error: Invalid diagnostic transition$/);
 assert.equal(records.length,0);d.enter('Chromium','whole_record_parity','case_begin',32);assert.equal(records[0].last.authored_case_index,32);
});
test('progress has finite event budget and persists before child completion',()=>{
 const root=fs.mkdtempSync(path.join(os.tmpdir(),'nf-fixed-progress-'));
 try{const d=createStageDiagnostics({record:v=>writeReport('output/progress.json',v,root)});for(let i=0;i<512;i++)d.enter('Chromium','mount');const file=path.join(root,'output/progress.json'),before=fs.readFileSync(file);assert.equal(JSON.parse(before).completed,false);assert.equal(JSON.parse(before).events.length,512);assert.throws(()=>d.enter('Chromium','mount'));assert.deepEqual(fs.readFileSync(file),before);}finally{fs.rmSync(root,{recursive:true,force:true});}
});
