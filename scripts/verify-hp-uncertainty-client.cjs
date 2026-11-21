// Fixed bounded programs for the standalone HP wording preview. No user commands.
'use strict';
const {spawnSync}=require('node:child_process'),path=require('node:path');
const {performance}=require('node:perf_hooks');
const commands=[
 {id:'fixture',args:['scripts/build-hp-uncertainty-fixture.mjs'],timeout:90000},
 {id:'client_controls',args:['--test','tests/hp-uncertainty-client.mjs'],timeout:30000},
 {id:'two_engine_browser_controls',args:['scripts/verify-hp-uncertainty-device.cjs'],timeout:360000},
];
for(const command of commands){
 const began=performance.now();let result;
 try{result=spawnSync(process.execPath,command.args,{cwd:path.resolve(__dirname,'..'),stdio:'inherit',timeout:command.timeout});}
 catch{result={error:{code:'UNAVAILABLE'}};}
 const pass=!result.error&&!result.signal&&result.status===0;
 const error=result.error?.code;
 console.log(JSON.stringify({profile:'hp-uncertainty-fixed-program/v1',command_id:command.id,pass,
  elapsed_ms:Math.round(performance.now()-began),budget_ms:command.timeout,
  outcome:error==='ETIMEDOUT'?'deadline':result.error?'startup':result.signal?'signal':pass?'completed':'exit_failed',
  status:Number.isInteger(result.status)?result.status:null,
  signal:['SIGTERM','SIGKILL','SIGABRT','SIGSEGV','SIGBUS','SIGILL'].includes(result.signal)?result.signal:null,
  independent_accuracy_evidence:false}));
 if(!pass){process.exitCode=1;break;}
}
