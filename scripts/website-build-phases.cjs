const {spawn}=require('node:child_process');
const {performance}=require('node:perf_hooks');

const PHASES=Object.freeze(['private-file-controls','build','catalogue','performance',
 'workflows','accessibility','mobile-payload','feedback']);
class StageError extends Error {
 constructor(){super('Website check phase failed.');this.name='StageError';}
}
class BuildPhases {
 constructor(cwd){this.cwd=cwd;this.rows=[];this.failed=false;this.running=false;this.inputRefused=false;this.controllerAborted=false;}
 async run(name,command,args,env=process.env){
  if(this.failed||this.running||name!==PHASES[this.rows.length]||typeof command!=='string'
   ||!command||!Array.isArray(args)||args.some(a=>typeof a!=='string')){
   this.failed=true;this.inputRefused=true;throw new StageError();
  }
  this.running=true;
  const started=performance.now();
  const row={phase:name,started_at:new Date().toISOString(),finished_at:null,
   elapsed_ms:null,exit_status:null,signal:null,failure:null,pass:false};
  this.rows.push(row);
  const finish=(code,signal,startupError)=>{
   row.finished_at=new Date().toISOString();row.elapsed_ms=Math.max(0,Math.round(performance.now()-started));
   row.exit_status=Number.isInteger(code)?code:null;
   row.signal=typeof signal==='string'&&/^SIG[A-Z0-9]{1,12}$/.test(signal)?signal:null;
   row.failure=startupError?'child_startup_failed':row.signal?'child_terminated':code===0?null:'child_exit_failed';
   row.pass=code===0&&!startupError&&!signal;
   this.running=false;this.failed=this.failed||!row.pass;
  };
  await new Promise((resolve,reject)=>{
   let settled=false;
   const settle=(code,signal,startupError)=>{
    if(settled)return;settled=true;finish(code,signal,startupError);
    row.pass?resolve():reject(new StageError());
   };
   try{
    const child=spawn(command,args,{cwd:this.cwd,env,stdio:'inherit',shell:false});
    child.once('error',()=>settle(null,null,true));
    child.once('close',(code,signal)=>settle(code,signal,false));
   }catch{settle(null,null,true);}
  });
 }
 abortController(){this.failed=true;this.controllerAborted=true;}
 report(){
  return {schema_version:1,kind:'website_build_phases',captured_at:new Date().toISOString(),
   pass:!this.failed&&!this.running&&this.rows.length===PHASES.length&&this.rows.every(r=>r.pass),
   expected_phases:[...PHASES],phases:this.rows.map(r=>({...r})),
   sequence_request_refused:this.inputRefused,controller_aborted:this.controllerAborted,
   raw_child_output_included:false,command_arguments_included:false,
   independent_accuracy_evidence:false,human_accessibility_verified:false};
 }
}
module.exports={PHASES,BuildPhases,StageError};
