/** Inert builtin-only observer controls; no Vite/Tailwind/native package import. */
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {createWebBuildObserver,BuildObservationUnavailable,BuildObservationUncertain} from '../scripts/web-checker-build-observer.mjs';
const repository=path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const cases=[];
function run(name,fn){fn();cases.push(name);}
function fixture(fn){
  const root=fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(),'web-observer-owned-')));
  try{
    const inputs=['site/package.json','site/package-lock.json','site/vite.config.js','site/scripts/prepare.mjs','site/scripts/prepare-device.mjs',
      'site/scripts/prepare-performance.mjs','site/scripts/prepare-offline.mjs','site/scripts/render-reference.mjs','scripts/web-checker-build-observer.mjs'];
    for(const n of inputs){fs.mkdirSync(path.dirname(path.join(root,n)),{recursive:true});fs.writeFileSync(path.join(root,n),n.endsWith('.json')?'{}\n':'// authored fixture\n');}
    for(const [name,version]of [['vite','8.3.4'],['rolldown','1.2.13']]){
      const p=path.join(root,'site/node_modules',name);fs.mkdirSync(p,{recursive:true});fs.writeFileSync(path.join(p,'package.json'),JSON.stringify({name,version}));
    }
    fs.mkdirSync(path.join(root,'site/src'));const module=path.join(root,'site/src/main.jsx');
    fs.copyFileSync(path.join(repository,'LICENSE'),module);
    fs.mkdirSync(path.join(root,'site/dist'));fs.writeFileSync(path.join(root,'site/dist/fixture.js'),'/* inert fixture */\n');
    const bundle={'fixture.js':{type:'chunk',fileName:'fixture.js',code:'/* inert fixture */\n',modules:{[module]:{renderedLength:0}},imports:[],dynamicImports:[]}};
    const info={code:'/* Copyright fixture é */'};const context={getModuleIds(){return [module]},getModuleInfo(){return info}};
    fn({root,module,bundle,context,plugin:()=>createWebBuildObserver({root,sourceCommit:'a'.repeat(40),sourceTree:'b'.repeat(40)})});
  }finally{
    // This test owns a fixed disposable synthetic root; production code never recursively removes inputs/output.
    fs.rmSync(root,{recursive:true,force:true});
  }
}
run('actual_existing_license_source_and_fixed_record',()=>fixture(({root,bundle,context,plugin})=>{
  plugin().writeBundle.call(context,{dir:path.join(root,'site/dist')},bundle);
  const raw=fs.readFileSync(path.join(root,'site/dist/web-build-observations.json'));
  assert.ok(!raw.includes(Buffer.from('é')));const record=JSON.parse(raw);
  assert.equal(record.sources['site/src/main.jsx'].bytes,fs.statSync(path.join(repository,'LICENSE')).size);
  assert.equal(record.outputs['fixture.js'].kind,'chunk');assert.equal(record.claims.permission_issued,false);
  assert.throws(()=>plugin().writeBundle.call(context,{dir:path.join(root,'site/dist')},bundle),BuildObservationUnavailable);
}));
run('exact_three_virtual_ids_stay_opaque',()=>fixture(({root,module,bundle,context,plugin})=>{
  const virtual=['\0rolldown/runtime.js','\0vite/preload-helper.js','vite/modulepreload-polyfill'];
  context.getModuleIds=()=>[module,...virtual];for(const v of virtual)bundle['fixture.js'].modules[v]={renderedLength:0};
  plugin().writeBundle.call(context,{dir:path.join(root,'site/dist')},bundle);
  const record=JSON.parse(fs.readFileSync(path.join(root,'site/dist/web-build-observations.json')));
  assert.equal(Object.values(record.modules).filter(x=>x.kind==='virtual').length,3);
  for(const item of Object.values(record.modules).filter(x=>x.kind==='virtual'))assert.equal(item.source_path,null);
}));
run('unknown_virtual_refuses_no_record',()=>fixture(({root,context,bundle,plugin})=>{
  context.getModuleIds=()=>['\0unknown/provider'];
  assert.throws(()=>plugin().writeBundle.call(context,{dir:path.join(root,'site/dist')},bundle),BuildObservationUnavailable);
  assert.ok(!fs.existsSync(path.join(root,'site/dist/web-build-observations.json')));
}));
run('changed_output_refuses_no_record',()=>fixture(({root,context,bundle,plugin})=>{
  fs.writeFileSync(path.join(root,'site/dist/fixture.js'),'changed');
  assert.throws(()=>plugin().writeBundle.call(context,{dir:path.join(root,'site/dist')},bundle),BuildObservationUnavailable);
}));
run('postcreate_close_failure_reports_uncertainty',()=>fixture(({root,context,bundle,plugin})=>{
  const close=fs.closeSync,open=fs.openSync;let recordFd;
  fs.openSync=function(name,...args){const fd=open(name,...args);if(name===path.join(root,'site/dist/web-build-observations.json'))recordFd=fd;return fd;};
  fs.closeSync=function(fd){close(fd);if(fd===recordFd){recordFd=undefined;throw new Error('after close');}};
  try{assert.throws(()=>plugin().writeBundle.call(context,{dir:path.join(root,'site/dist')},bundle),BuildObservationUncertain);}
  finally{fs.closeSync=close;fs.openSync=open;}
  assert.ok(fs.existsSync(path.join(root,'site/dist/web-build-observations.json')));
}));
function typedSource(name,text,inspect) {
  fixture(({root,bundle,context,plugin})=>{
    const target=path.join(root,'site',name);fs.writeFileSync(target,text);
    context.getModuleIds=()=>[target];bundle['fixture.js'].modules={[target]:{renderedLength:0}};
    const execute=()=>plugin().writeBundle.call(context,{dir:path.join(root,'site/dist')},bundle);
    inspect({execute,record:()=>JSON.parse(fs.readFileSync(path.join(root,'site/dist/web-build-observations.json'))),root});
  });
}
run('long_html_URL_is_not_a_JS_comment_and_actual_HTML_notice_is_preserved',()=>{
  const html='<!doctype html><html><head><script type=application/ld+json>{"url":"https://example.test/license"}</script><script src="/theme.js"></script></head><body><!-- Copyright retained HTML -->'+
    '<a hidden data-kind="reference" href="https://example.test/license">'+('Legal license data. '.repeat(1500))+'</a></body></html>';
  typedSource('index.html',html,({execute,record})=>{execute();const rows=record().sources['site/index.html'].notices;assert.equal(rows.length,1);assert.equal(rows[0].text,'<!-- Copyright retained HTML -->');});
});
run('JSON_legal_data_and_URLs_are_not_lexical_comments',()=>{
  typedSource('scope.json',JSON.stringify({url:'https://example.test/license',legal:'/* Copyright is data */'}),({execute,record})=>{execute();assert.deepEqual(record().sources['site/scope.json'].notices,[]);});
  typedSource('bad.json','{"url": /* license */ "x"}',({execute})=>assert.throws(execute,BuildObservationUnavailable));
});
run('unsupported_HTML_inline_code_and_ambiguous_grammar_refuse',()=>{
  for(const html of ['<html><script>/* Copyright inline */</script></html>','<html><STYLE>/* license */</STYLE></html>',
    '<html><script TYPE="application/ld+json">not JSON</script></html>','<html><script type=application/ld+json src=x>{}</script></html>',
    '<html><script src="x"src="y"></script></html>','<html><!-- unclosed','<html><script src=x>','<html><div></html>',
    '<html><script type="application/ld+json" TYPE="application/ld+json">{}</script></html>']) {
    typedSource('index.html',html,({execute,root})=>{assert.throws(execute,BuildObservationUnavailable);assert.ok(!fs.existsSync(path.join(root,'site/dist/web-build-observations.json')));});
  }
});
run('JavaScript_legal_comments_and_existing_notice_cap_remain',()=>{
  typedSource('code.js','/* Copyright real JavaScript */\n',({execute,record})=>{execute();assert.equal(record().sources['site/code.js'].notices[0].text,'/* Copyright real JavaScript */');});
  typedSource('code.js','/* Copyright '+('x'.repeat(16384))+' */',({execute})=>assert.throws(execute,BuildObservationUnavailable));
});
console.log(JSON.stringify({pass:true,controls:cases.length,cases,builder_imported:false,whole_build_executed:false}));
