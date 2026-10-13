const test=require('node:test'),assert=require('node:assert/strict');
const {BuildPhases,PHASES,StageError}=require('../scripts/website-build-phases.cjs');
const cwd=__dirname;
test('only all eight successful real children form a passing record',async()=>{
 const phases=new BuildPhases(cwd);assert.equal(phases.report().pass,false);
 for(const name of PHASES){await phases.run(name,process.execPath,['-e','process.exit(0)']);}
 const record=phases.report();assert.equal(record.pass,true);assert.equal(record.phases.length,8);
 for(const row of record.phases){assert.equal(row.exit_status,0);assert.equal(row.pass,true);assert(row.elapsed_ms>=0);assert(new Date(row.finished_at)>=new Date(row.started_at));}
 record.phases[0].pass=false;assert.equal(phases.report().pass,true);
});
test('ordinary failure stays failed and prevents a later child',async()=>{
 const phases=new BuildPhases(cwd);
 await assert.rejects(phases.run(PHASES[0],process.execPath,['-e','process.exit(7)','PRIVATE_ARGUMENT_CANARY']),StageError);
 assert.equal(phases.report().pass,false);assert.equal(phases.report().phases[0].exit_status,7);
 assert.equal(phases.report().phases[0].failure,'child_exit_failed');
 await assert.rejects(phases.run(PHASES[1],process.execPath,['-e','process.exit(0)']),StageError);
 assert.equal(phases.report().phases.length,1);assert(!JSON.stringify(phases.report()).includes('PRIVATE_ARGUMENT_CANARY'));
});
test('real termination signal is a failure with a bounded signal',async()=>{
 const phases=new BuildPhases(cwd);
 await assert.rejects(phases.run(PHASES[0],process.execPath,['-e',"process.kill(process.pid,'SIGTERM')"]),StageError);
 assert.equal(phases.report().phases[0].failure,'child_terminated');assert.equal(phases.report().phases[0].signal,'SIGTERM');assert.equal(phases.report().phases[0].pass,false);
});
test('real startup failure omits the private command and exception text',async()=>{
 const phases=new BuildPhases(cwd);
 await assert.rejects(phases.run(PHASES[0],'/missing-PRIVATE_PATH_CANARY',[]),StageError);
 const record=phases.report();assert.equal(record.pass,false);assert.equal(record.phases[0].failure,'child_startup_failed');assert(!JSON.stringify(record).includes('PRIVATE_PATH_CANARY'));
});
test('invalid or out-of-order stages refuse before starting anything',async()=>{
 const phases=new BuildPhases(cwd);
 await assert.rejects(phases.run('PRIVATE_STAGE_CANARY',process.execPath,[]),StageError);
 await assert.rejects(phases.run(PHASES[1],process.execPath,[]),StageError);
 assert.equal(phases.report().phases.length,0);assert.equal(phases.report().pass,false);assert(!JSON.stringify(phases.report()).includes('PRIVATE_STAGE_CANARY'));
});
test('a partial success never passes and concurrent starts are refused',async()=>{
 const phases=new BuildPhases(cwd);
 const first=phases.run(PHASES[0],process.execPath,['-e','setTimeout(()=>process.exit(0),30)']);
 await assert.rejects(phases.run(PHASES[1],process.execPath,[]),StageError);
 await first;assert.equal(phases.report().phases.length,1);assert.equal(phases.report().pass,false);
});
test('an ignored invalid request cannot leave a passing aggregate record',async()=>{
 const phases=new BuildPhases(cwd);
 for(const name of PHASES){await phases.run(name,process.execPath,['-e','process.exit(0)']);}
 await assert.rejects(phases.run('PRIVATE_STAGE_CANARY',process.execPath,[]),StageError);
 assert.equal(phases.report().pass,false);assert.equal(phases.report().phases.length,8);
});

test('controller failure after successful children cannot produce a pass',async()=>{
 const phases=new BuildPhases(cwd);
 for(const name of PHASES){await phases.run(name,process.execPath,['-e','process.exit(0)']);}
 phases.abortController();assert.equal(phases.report().pass,false);assert.equal(phases.report().controller_aborted,true);
});
