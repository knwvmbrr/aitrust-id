// Build current source, then check that exact build on an owned ephemeral server.
const fs=require('node:fs'),path=require('node:path'),http=require('node:http');
const {spawn}=require('node:child_process');
const {parseHeaders,headersFor}=require('./static-headers.cjs');
const root=path.resolve(__dirname,'..'),dist=path.join(root,'site/dist');
const run=(command,args,env=process.env)=>new Promise((resolve,reject)=>{
 const child=spawn(command,args,{cwd:root,env,stdio:'inherit'});
 child.on('error',reject);child.on('exit',(code,signal)=>code===0?resolve():reject(Error('Website check failed: '+(signal||code))));
});
async function main(){
 await run(process.platform==='win32'?'npm.cmd':'npm',['run','build:site']);
 const rules=parseHeaders(fs.readFileSync(path.join(dist,'_headers'),'utf8'));
 const mime={'.html':'text/html','.js':'text/javascript','.mjs':'text/javascript','.css':'text/css','.json':'application/json','.svg':'image/svg+xml','.png':'image/png','.wasm':'application/wasm','.woff2':'font/woff2','.txt':'text/plain','.md':'text/plain','.py':'text/plain'};
 const server=http.createServer((req,res)=>{
  try{
   if(req.method!=='GET'&&req.method!=='HEAD'){res.writeHead(405);res.end();return;}
   const relative=decodeURIComponent(new URL(req.url,'http://127.0.0.1').pathname);
   let file=path.resolve(dist,'.'+relative);
   if(file!==dist&&!file.startsWith(dist+path.sep))throw Error('path');
   if(fs.statSync(file).isDirectory())file=path.join(file,'index.html');
   let current=file;
   while(current!==dist){if(fs.lstatSync(current).isSymbolicLink())throw Error('symlink');current=path.dirname(current);}
   if(!fs.statSync(file).isFile())throw Error('file');
   res.writeHead(200,{'content-type':mime[path.extname(file)]||'application/octet-stream',...headersFor(rules,relative)});
   if(req.method==='HEAD')res.end();else fs.createReadStream(file).on('error',()=>res.destroy()).pipe(res);
  }catch{res.writeHead(404);res.end();}
 });
 try{
  await new Promise((resolve,reject)=>{server.once('error',reject);server.listen(0,'127.0.0.1',resolve);});
  const env={...process.env,AITRUST_SITE_URL:'http://127.0.0.1:'+server.address().port};
  // Ignore a caller's stale external fixture URL. Both tools see this new build.
  await run(process.execPath,['scripts/verify-site.cjs'],env);
  await run(process.execPath,['scripts/verify-site-accessibility.cjs'],env);
 await run(process.execPath,['scripts/verify-research-feedback.cjs'],env);
 }finally{server.closeAllConnections();await new Promise(resolve=>server.close(resolve));}
}
main().catch(()=>{console.error('CURRENT_BUILD_WEBSITE_REVALIDATION_FAILED');process.exitCode=1;});
