// Fixed source-bound entrypoint. Diagnostic outcomes contain no child error text.
const {spawnSync}=require('node:child_process');
const path=require('node:path');
const os=require('node:os');
const {writeReport}=require('./execution-report.cjs');
const COMMANDS=Object.freeze([
 Object.freeze({id:'fixture',args:['scripts/build-nf-device-fixture.mjs'],timeout:90000}),
 Object.freeze({id:'client_controls',args:['--test','tests/nf-device-client.mjs'],timeout:30000}),
 Object.freeze({id:'canonical_browser',args:['scripts/verify-nf-device.cjs'],timeout:180000}),
 Object.freeze({id:'input_controls',args:['scripts/verify-nf-input.cjs'],timeout:120000})
]);
const ENGINES=new Set(['setup','Chromium','WebKit']);
const STAGES=new Set(['configuration','server','launch','mount','whole_record_parity','form_negation_and_privacy','invalid_cosine_then_literal','appearance','privacy','optional_failures','lifecycle','corrupt_closed_records','chunk_import_render','source_stability','cleanup','complete']);
const SUBSTEPS=new Set(['start','complete','case_begin','case_complete','negation_submit','negation_result','details','private_submit','private_result','cosine_fill','cosine_submit','cosine_alert_wait','cosine_alert_observed','literal_select','literal_submit','literal_result_wait','literal_result_observed','payload','validator','edit','clear','cancel','unmount','claim_raw','passage_raw','claim_nfc','passage_nfc','unknown','source','omitted','score','chunk','import','render','browser_close','fault_context_begin','fault_context_ready','fault_navigation_begin','fault_navigation_complete','fault_trigger_begin','fault_trigger_complete','fault_fallback_wait','fault_fallback_observed','peer_checks_begin','peer_ps_begin','peer_ps_complete','peer_mt_begin','peer_mt_complete','peer_checks_complete','fault_context_close_begin','fault_context_close_complete','browser_close_begin','browser_close_complete']);
const SIGNALS=new Set(['SIGTERM','SIGKILL','SIGABRT','SIGSEGV','SIGINT','SIGHUP','SIGQUIT','SIGILL','SIGBUS','SIGFPE','SIGPIPE']);
const CODES=new Set(['ETIMEDOUT','ENOENT','EACCES','EIO','ENOBUFS','E2BIG','EINVAL']);
function ms(value){if(typeof value!=='number'||!Number.isFinite(value)||value<0)throw Error('Invalid diagnostic timing');return Math.round(value);}
function classifyChild(result,elapsed){
 try{
  const duration=ms(elapsed),error=result?.error,code=error?(CODES.has(error.code)?error.code:'OTHER'):null;
  const status=Number.isInteger(result?.status)&&result.status>=0&&result.status<=255?result.status:null;
  const signal=result?.signal?(SIGNALS.has(result.signal)?result.signal:'OTHER'):null;
  const outcome=code==='ETIMEDOUT'?'deadline':code==='ENOENT'||code==='EACCES'?'startup_error':error?'process_error':signal?'signal':status===0?'success':status!==null?'exit_status':'invalid_result';
  return {outcome,error_code:code,signal,status,elapsed_ms:duration};
 }catch{return {outcome:'invalid_result',error_code:null,signal:null,status:null,elapsed_ms:0};}
}
function hostCapacity(){
 const integer=value=>Number.isSafeInteger(value)&&value>0?value:null;
 return {platform:['linux','darwin','win32'].includes(os.platform())?os.platform():'other',
  available_cpu_threads:integer(typeof os.availableParallelism==='function'?os.availableParallelism():null),
  total_memory_bytes:integer(os.totalmem()),
  available_memory_bytes:integer(typeof process.availableMemory==='function'?Math.min(os.freemem(),process.availableMemory()):null),
  constrained_memory_bytes:integer(typeof process.constrainedMemory==='function'?process.constrainedMemory():null)};
}
function engineExecution({env=process.env,capacity=hostCapacity()}={}){
 const flag=env.AITRUST_NF_ENGINE_CONCURRENCY;
 if(flag!==undefined&&flag!=='1'&&flag!=='2')throw Error('Unsupported NF engine profile');
 const concurrency=flag==='2'?2:1;
 const hosted=capacity.platform==='linux'&&env.GITHUB_ACTIONS==='true'&&env.AITRUST_CI_RUNNER_ENV==='github-hosted'&&env.AITRUST_CI_RUNNER_OS==='Linux';
 if(concurrency===2&&(!hosted||!Number.isSafeInteger(capacity.available_cpu_threads)||capacity.available_cpu_threads<2||!Number.isSafeInteger(capacity.total_memory_bytes)||capacity.total_memory_bytes<4*1024**3||!Number.isSafeInteger(capacity.available_memory_bytes)||capacity.available_memory_bytes<2*1024**3||(capacity.constrained_memory_bytes!==null&&(!Number.isSafeInteger(capacity.constrained_memory_bytes)||capacity.constrained_memory_bytes<4*1024**3))))throw Error('Unsupported NF engine profile');
 return {profile:'nf-engine-execution/v1',mode:concurrency===1?'sequential':'hosted_parallel_two',concurrency,declared_host:hosted?'github-hosted-linux':'local-or-other',host_capacity:capacity};
}
async function settleEngineChecks(concurrency,run){
 if(![1,2].includes(concurrency)||typeof run!=='function')throw Error('Unsupported NF engine profile');
 const names=['Chromium','WebKit'];
 if(concurrency===2)return Promise.allSettled(names.map(name=>run(name)));
 const settled=[];for(const name of names)settled.push(...await Promise.allSettled([Promise.resolve().then(()=>run(name))]));return settled;
}
async function closeWithDiagnostics(close,mark,begin,end){
 let diagnosticError=null,closeError=null;
 try{await mark(begin);}catch(error){diagnosticError=error||Error('Diagnostic checkpoint failed');}
 try{await close();}catch(error){closeError=error||Error('Owned close failed');}
 if(closeError===null){try{await mark(end);}catch(error){diagnosticError??=error||Error('Diagnostic checkpoint failed');}}
 return {complete:closeError===null,diagnostics_complete:diagnosticError===null,error:closeError||diagnosticError};
}
function publicStageEvent(event){
 const fields=['engine','stage','substep','authored_case_index','elapsed_ms','engine_elapsed_ms','stage_elapsed_ms','since_previous_ms'];
 if(!event||typeof event!=='object'||Array.isArray(event)||Object.getPrototypeOf(event)!==Object.prototype||Object.keys(event).sort().join(',')!==[...fields].sort().join(','))throw Error('Invalid diagnostic event');
 const descriptors=Object.getOwnPropertyDescriptors(event);if(Object.values(descriptors).some(d=>!('value'in d)))throw Error('Invalid diagnostic event');
 if(!ENGINES.has(event.engine)||!STAGES.has(event.stage)||!SUBSTEPS.has(event.substep)||!(event.authored_case_index===null||Number.isInteger(event.authored_case_index)&&event.authored_case_index>=0&&event.authored_case_index<33)||fields.slice(4).some(k=>!Number.isSafeInteger(event[k])||event[k]<0))throw Error('Invalid diagnostic event');
 return Object.fromEntries(fields.map(k=>[k,event[k]]));
}
function createStageDiagnostics({clock=()=>performance.now(),record=()=>{}}={}){
 const started=clock(),states=new Map(),events=[];
 return {enter(engine,stage,substep='start',item=null){
  if(!ENGINES.has(engine)||!STAGES.has(stage)||!SUBSTEPS.has(substep)||!(item===null||Number.isInteger(item)&&item>=0&&item<33)||events.length>=512)throw Error('Invalid diagnostic transition');
  const now=clock();let state=states.get(engine);
  if(!state){state={started:now,previous:now,stageStarted:now,stage};states.set(engine,state);}
  if(state.stage!==stage){state.stageStarted=now;state.stage=stage;}
  const event={engine,stage,substep,authored_case_index:item,elapsed_ms:ms(now-started),engine_elapsed_ms:ms(now-state.started),stage_elapsed_ms:ms(now-state.stageStarted),since_previous_ms:ms(now-state.previous)};
  state.previous=now;events.push(event);
  const value={profile:'nf-browser-progress/v1',captured_at:new Date().toISOString(),completed:engine==='setup'&&stage==='complete'&&substep==='complete',last:event,events:events.map(v=>({...v}))};
  if(Buffer.byteLength(JSON.stringify(value))>120000)throw Error('Diagnostic budget exceeded');record(value);return event;
 }};
}
function runCommands({spawn=spawnSync,clock=()=>performance.now(),record=value=>writeReport(process.env.AITRUST_NF_CLIENT_REPORT||'output/verification/nf-client-diagnostic.json',value)}={}){
 const report={profile:'nf-client-process-diagnostic/v1',captured_at:new Date().toISOString(),pass:false,commands:[]};
 for(const command of COMMANDS){
  const start=clock();let result;
  try{result=spawn(process.execPath,command.args,{cwd:path.resolve(__dirname,'..'),stdio:'inherit',timeout:command.timeout});}
  catch{result={error:{code:'OTHER'},signal:null,status:null};}
  const row={command_id:command.id,timeout_ms:command.timeout,...classifyChild(result,clock()-start)};
  report.commands.push(row);report.pass=report.commands.length===COMMANDS.length&&row.outcome==='success';record(report);
  console.log(JSON.stringify({nf_command:row}));
  if(row.outcome!=='success')return false;
 }
 return true;
}
module.exports={COMMANDS,classifyChild,hostCapacity,engineExecution,settleEngineChecks,closeWithDiagnostics,publicStageEvent,createStageDiagnostics,runCommands};
if(require.main===module){try{if(!runCommands())process.exitCode=1;}catch{console.error('NF diagnostic recording unavailable');process.exitCode=1;}}
