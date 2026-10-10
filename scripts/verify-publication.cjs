const {writeReport}=require('./execution-report.cjs');
// Compare a reviewed static build with each declared public delivery origin.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const {execFileSync}=require('node:child_process');const {chromium}=require('playwright');
const args=process.argv.slice(2),origins=[];let source,output;
for(let i=0;i<args.length;i++){
 const value=args[++i];if(!value)throw Error('Missing option value');
 if(args[i-1]==='--origin')origins.push(value);
 else if(args[i-1]==='--source')source=value;
 else if(args[i-1]==='--output')output=value;
 else throw Error('Unknown option');
}
if(!/^[a-f0-9]{40}$/.test(source||'')||!origins.length)throw Error('Full source commit and origins required');
for(const origin of origins){const u=new URL(origin);if(u.protocol!=='https:'||u.username||u.password||u.port||u.pathname!=='/'||u.search||u.hash)throw Error('Require HTTPS origin without credentials or path');}
const root=path.resolve('site/dist');function walk(dir){return fs.readdirSync(dir,{withFileTypes:true}).flatMap(e=>{if(e.isSymbolicLink())throw Error('Build symlink refused');const p=path.join(dir,e.name);return e.isDirectory()?walk(p):[p];});}
const files=walk(root).filter(p=>!['_headers','_redirects'].includes(path.relative(root,p)));
if(fs.readFileSync(path.join(root,'reference/changelog.md'),'utf8')!==execFileSync('git',['show',source+':CHANGELOG.md'],{encoding:'utf8'}))throw Error('Build changelog differs from declared source');
const sha=bytes=>crypto.createHash('sha256').update(bytes).digest('hex');
(async()=>{const browser=await chromium.launch({headless:true});const context=await browser.newContext();const checked=[];
 try{for(const origin of origins){let matches=0;
  // Use the real browser's ordinary transport. Do not impersonate another client,
  // solve a challenge, reduce edge protections or accept a non-200 response.
  const page=await context.newPage();
  try{const response=await page.goto(origin,{waitUntil:'domcontentloaded',timeout:30000});if(!response||response.status()!==200)throw Error('Public browser entry unavailable');}
  finally{await page.close();}
  for(let start=0;start<files.length;start+=6){await Promise.all(files.slice(start,start+6).map(async file=>{
   let relative=path.relative(root,file).split(path.sep).join('/');if(relative.endsWith('index.html'))relative=relative.slice(0,-10);else if(relative.endsWith('.html'))relative=relative.slice(0,-5);
   const response=await context.request.get(origin+'/'+relative,{timeout:30000,maxRedirects:0});if(response.status()!==200)throw Error('Public artifact unavailable: '+relative);
   if(sha(await response.body())!==sha(fs.readFileSync(file)))throw Error('Public artifact differs: '+relative);matches++;
  }));}
  const headers=(await context.request.get(origin+'/',{timeout:30000,maxRedirects:0})).headers();if(!headers['content-security-policy']||!headers['cache-control']?.includes('no-transform')||headers['x-content-type-options']!=='nosniff')throw Error('Required public security headers missing');
  checked.push({origin,matching_artifacts:matches,security_headers_present:true});
 }
 const report={captured_at:new Date().toISOString(),pass:true,source_commit:source,artifacts_per_origin:files.length,origins:checked,matching_artifacts:files.length*checked.length,scope:'Exact decoded HTTP bytes of the reviewed build; not an independent source audit or detector accuracy test',independent_accuracy_evidence:false};if(output)writeReport(output,report);console.log(JSON.stringify(report));
 }finally{await browser.close();}
})().catch(error=>{console.error(error.message);process.exitCode=1;});
