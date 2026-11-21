// Fixed source-bound entrypoint. Diagnostic outcomes contain no child error text.
const {spawnSync}=require('node:child_process');
const path=require('node:path');
const {writeReport}=require('./execution-report.cjs');
const COMMANDS=Object.freeze([
 Object.freeze({id:'fixture',args:['scripts/build-nf-device-fixture.mjs'],timeout:90000}),
 Object.freeze({id:'client_controls',args:['--test','tests/nf-device-client.mjs'],timeout:30000}),
 Object.freeze({id:'canonical_browser',args:['scripts/verify-nf-device.cjs'],timeout:180000}),
 Object.freeze({id:'input_controls',args:['scripts/verify-nf-input.cjs'],timeout:120000})
]);
const ENGINES=new Set(['setup','Chromium','WebKit']);
const STAGES=new Set(['server','launch','mount','whole_record_parity','form_negation_and_privacy','invalid_cosine_then_literal','appearance','privacy','optional_failures','lifecycle','corrupt_closed_records','chunk_import_render','source_stability','complete']);
const SUBSTEPS=new Set(['start','complete','case_begin','case_complete','negation_submit','negation_result','details','private_submit','private_result','cosine_fill','cosine_submit','cosine_alert_wait','cosine_alert_observed','literal_select','literal_submit','literal_result_wait','literal_result_observed','payload','validator','edit','clear','cancel','unmount','claim_raw','passage_raw','claim_nfc','passage_nfc','unknown','source','omitted','score','chunk','import','render']);
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
function createStageDiagnostics({clock=()=>performance.now(),record=()=>{}}={}){
 const started=clock();let previous=started,stageStarted=started,currentEngine=null,currentStage=null;const events=[];
 return {enter(engine,stage,substep='start',item=null){
  if(!ENGINES.has(engine)||!STAGES.has(stage)||!SUBSTEPS.has(substep)||!(item===null||Number.isInteger(item)&&item>=0&&item<33)||events.length>=512)throw Error('Invalid diagnostic transition');
  const now=clock();if(currentEngine!==engine||currentStage!==stage){stageStarted=now;currentEngine=engine;currentStage=stage;}
  const event={engine,stage,substep,authored_case_index:item,elapsed_ms:ms(now-started),stage_elapsed_ms:ms(now-stageStarted),since_previous_ms:ms(now-previous)};
  previous=now;events.push(event);
  const value={profile:'nf-browser-progress/v1',captured_at:new Date().toISOString(),completed:stage==='complete'&&substep==='complete',last:event,events:events.map(v=>({...v}))};
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
module.exports={COMMANDS,classifyChild,createStageDiagnostics,runCommands};
if(require.main===module){try{if(!runCommands())process.exitCode=1;}catch{console.error('NF diagnostic recording unavailable');process.exitCode=1;}}
