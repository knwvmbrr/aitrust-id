// Build current source, then check that exact build on an owned ephemeral server.
const path=require('node:path');
const {BuildPhases}=require('./website-build-phases.cjs');
const {writeReport}=require('./execution-report.cjs');
const {startSiteFixture}=require('./site-fixture-server.cjs');
const root=path.resolve(__dirname,'..'),dist=path.join(root,'site/dist');
const phases=new BuildPhases(root);
const run=(name,command,args,env=process.env)=>phases.run(name,command,args,env);
async function main(){
 await run('private-file-controls',process.execPath,['--test','tests/blind-review-files.cjs','tests/site-fixture-server.cjs']);
 await run('build',process.platform==='win32'?'npm.cmd':'npm',['run','build:site']);
 const fixture=await startSiteFixture({directory:dist});
 try{
  const env={...process.env,AITRUST_SITE_URL:fixture.url};
  // Ignore a caller's stale external fixture URL. Both tools see this new build.
  await run('catalogue',process.execPath,['scripts/verify-site.cjs'],env);
  await run('performance',process.execPath,['scripts/verify-performance.cjs'],env);
  await run('workflows',process.execPath,['scripts/verify-workflows.cjs'],env);
  await run('accessibility',process.execPath,['scripts/verify-site-accessibility.cjs'],env);
  await run('mobile-payload',process.execPath,['scripts/verify-mobile-payload.cjs'],env);
 await run('feedback',process.execPath,['scripts/verify-research-feedback.cjs'],env);
 await run('policies',process.execPath,['scripts/verify-policies.cjs'],env);
 }finally{await fixture.close();}
}
// Invalidate any previous success before starting even the first child.
try{writeReport('output/verification/website-build-phases.json',phases.report());}
catch{console.error('BUILD_PHASE_REPORT_UNAVAILABLE');process.exitCode=1;}
if(!process.exitCode)main().catch(()=>{phases.abortController();console.error('CURRENT_BUILD_WEBSITE_REVALIDATION_FAILED');process.exitCode=1;}).finally(()=>{
 try{const report=phases.report();writeReport('output/verification/website-build-phases.json',report);if(!report.pass)process.exitCode=1;}
 catch{console.error('BUILD_PHASE_REPORT_UNAVAILABLE');process.exitCode=1;}
});
