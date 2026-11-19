// Loopback verification only: serve one frozen build with its reviewed headers.
'use strict';
const fs=require('node:fs'),path=require('node:path'),http=require('node:http');
const {parseHeaders,headersFor}=require('./static-headers.cjs');
const mime={'.html':'text/html','.js':'text/javascript','.mjs':'text/javascript','.css':'text/css','.json':'application/json','.svg':'image/svg+xml','.png':'image/png','.wasm':'application/wasm','.woff2':'font/woff2','.txt':'text/plain','.md':'text/plain','.py':'text/plain','.zip':'application/zip'};
const same=(a,b)=>a.dev===b.dev&&a.ino===b.ino&&a.mode===b.mode;
function openBuildFile(root,rootIdentity,relative){
 if(!same(fs.lstatSync(root),rootIdentity))throw Error('Build root changed');
 let file=path.resolve(root,'.'+relative);if(file!==root&&!file.startsWith(root+path.sep))throw Error('Outside build');
 if(fs.lstatSync(file).isDirectory())file=path.join(file,'index.html');
 let current=root;
 for(const part of path.relative(root,file).split(path.sep)){
  current=path.join(current,part);const info=fs.lstatSync(current);
  if(info.isSymbolicLink())throw Error('Build link refused');
  if(current!==file&&!info.isDirectory())throw Error('Build ancestor refused');
 }
 const expected=fs.lstatSync(file);if(!expected.isFile())throw Error('Build file refused');
 const fd=fs.openSync(file,fs.constants.O_RDONLY|fs.constants.O_NOFOLLOW|fs.constants.O_NONBLOCK);
 try{const actual=fs.fstatSync(fd);if(!actual.isFile()||!same(actual,expected))throw Error('Build file changed');return {fd,file,info:actual};}
 catch(error){fs.closeSync(fd);throw error;}
}
async function startSiteFixture({directory,port=0}={}){
 if(typeof directory!=='string'||!Number.isSafeInteger(port)||port<0||port>65535)throw Error('Invalid fixture configuration');
 const root=path.resolve(directory),rootIdentity=fs.lstatSync(root);
 if(rootIdentity.isSymbolicLink()||!rootIdentity.isDirectory()||fs.realpathSync(root)!==root)throw Error('Build root refused');
 const headerFile=openBuildFile(root,rootIdentity,'/_headers');let rules;
 try{
  if(headerFile.info.size<=0||headerFile.info.size>65536)throw Error('Header file refused');
  const bytes=Buffer.alloc(65537);let used=0;
  while(used<bytes.length){const n=fs.readSync(headerFile.fd,bytes,used,bytes.length-used,used);if(!n)break;used+=n;}
  const after=fs.fstatSync(headerFile.fd);
  if(used!==headerFile.info.size||!same(after,headerFile.info)||after.size!==used||after.mtimeMs!==headerFile.info.mtimeMs||after.ctimeMs!==headerFile.info.ctimeMs)throw Error('Header file changed');
  rules=parseHeaders(new TextDecoder('utf-8',{fatal:true}).decode(bytes.subarray(0,used)));
  for(const rule of rules)for(const [name,value] of Object.entries(rule.headers)){http.validateHeaderName(name);http.validateHeaderValue(name,value);}
 }finally{fs.closeSync(headerFile.fd);}
 const server=http.createServer((req,res)=>{
  let relative='/',fd;
  // A close error may follow a completed close. Relinquish ownership first,
  // because that numeric descriptor can already belong to something else.
  const closeOwned=()=>{const owned=fd;fd=undefined;if(owned!==undefined)fs.closeSync(owned);};
  const respond=status=>{res.writeHead(status,{'content-type':'text/plain',...headersFor(rules,relative),...(status===405?{allow:'GET, HEAD'}:{})});res.end();};
  try{
   if(req.method!=='GET'&&req.method!=='HEAD'){req.resume();respond(405);return;}
   if(typeof req.url!=='string'||!req.url.startsWith('/')||req.url.startsWith('//'))throw Error('Invalid target');
   relative=decodeURIComponent(req.url.split('?')[0]);
   if(relative.includes('\\')||relative.includes('\0')||relative.split('/').some(p=>p==='.'||p==='..'))throw Error('Invalid path');
   const opened=openBuildFile(root,rootIdentity,relative);fd=opened.fd;
   res.writeHead(200,{'content-type':mime[path.extname(opened.file)]||'application/octet-stream',...headersFor(rules,relative)});
   if(req.method==='HEAD'){closeOwned();res.end();return;}
   const stream=fs.createReadStream(null,{fd,autoClose:true});fd=undefined;
   res.once('close',()=>stream.destroy());stream.once('error',()=>res.destroy());stream.pipe(res);
  }catch{
   try{closeOwned();}catch{res.destroy();return;}
   if(res.headersSent)res.destroy();else respond(404);
  }
 });
 await new Promise((resolve,reject)=>{server.once('error',reject);server.listen(port,'127.0.0.1',()=>{server.removeListener('error',reject);resolve();});});
 let closing;
 return {url:'http://127.0.0.1:'+server.address().port,close(){return closing??=(async()=>{server.closeAllConnections();await new Promise(resolve=>server.close(resolve));})();}};
}
module.exports={startSiteFixture};
if(require.main===module){
 (async()=>{
  const args=process.argv.slice(2);if(args.length!==4||args[0]!=='--directory'||args[2]!=='--port'||!/^\d{1,5}$/.test(args[3]))throw Error('Invalid fixture arguments');
  const fixture=await startSiteFixture({directory:args[1],port:Number(args[3])});console.log('SITE_FIXTURE_READY '+fixture.url);
  const close=()=>fixture.close().then(()=>{process.exitCode=0;});process.once('SIGINT',close);process.once('SIGTERM',close);
 })().catch(()=>{console.error('SITE_FIXTURE_START_FAILED');process.exitCode=1;});
}
