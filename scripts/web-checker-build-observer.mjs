/** Closed observations of the actual pinned bundler. No permission or release decision. */
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {fileURLToPath} from 'node:url';
import {execFileSync} from 'node:child_process';

export const PROFILE = 'web-checker-build-observations/v1';
export const LIMITS = Object.freeze({files:2048, modules:2048, bytes:2_000_000, source:2_000_000, totalSource:32_000_000, seconds:60});
const repository = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const fixedInputs = Object.freeze(['site/package.json','site/package-lock.json','site/vite.config.js',
  'site/scripts/prepare.mjs','site/scripts/prepare-device.mjs','site/scripts/prepare-performance.mjs',
  'site/scripts/prepare-offline.mjs','site/scripts/render-reference.mjs','scripts/web-checker-build-observer.mjs']);
const virtual = new Map([['\0rolldown/runtime.js','rolldown-runtime'],['\0vite/preload-helper.js','vite-preload-helper'],['vite/modulepreload-polyfill','vite-modulepreload'],['\0vite/modulepreload-polyfill.js','vite-modulepreload']]);
const hash = bytes => crypto.createHash('sha256').update(bytes).digest('hex');
const blob = bytes => crypto.createHash('sha1').update(Buffer.from(`blob ${bytes.length}\0`)).update(bytes).digest('hex');
export class BuildObservationUnavailable extends Error {constructor(){super('Web build observation unavailable.');}}
export class BuildObservationUncertain extends Error {constructor(){super('Web build observation output may exist; inspect before retrying.');this.output_may_exist=true;}}
const fail = () => { throw new BuildObservationUnavailable(); };
const need = value => {if(!value) fail();};
const relative = name => {
  need(typeof name==='string' && name.length>0 && name.length<=240 && /^[A-Za-z0-9_.@+~\/-]+$/.test(name)
    && !name.startsWith('/') && name.split('/').every(p=>p && p!=='.' && p!=='..'));
  return name;
};
function stable(info) {return [info.dev,info.ino,info.mode,info.nlink,info.size,info.mtimeNs,info.ctimeNs].map(String).join(':');}
function canonical(value) {
  if(value===null || typeof value!=='object') return JSON.stringify(value).replace(/[\u007f-\uffff]/g,c=>'\\u'+c.charCodeAt(0).toString(16).padStart(4,'0'));
  if(Array.isArray(value)) return '['+value.map(canonical).join(',')+']';
  return '{'+Object.keys(value).sort().map(k=>JSON.stringify(k)+':'+canonical(value[k])).join(',')+'}';
}
function ownEntries(object, limit) {
  need(object && typeof object==='object' && !Array.isArray(object));
  const result=[];
  for(const key in object) if(Object.hasOwn(object,key)) {need(result.length<limit);result.push([key,object[key]]);}
  return result;
}

/** A deliberately strict HTML profile: balanced tags, no executable inline bodies. */
function* htmlComments(text) {
  const voids=new Set(['area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr']);
  const names=/[A-Za-z][A-Za-z0-9:-]*/y,attributes=/[A-Za-z_:][A-Za-z0-9_:.-]*/y;
  const stack=[];let at=0,tokens=0;
  const space=()=>{const start=at;while(at<text.length && /[\t\n\r\f ]/.test(text[at]))at++;return at>start;};
  while(at<text.length) {
    if(text[at]!=='<'){at++;continue;}
    need(++tokens<=10000);
    if(text.startsWith('<!--',at)) {
      const start=at,end=text.indexOf('-->',at+4);need(end>=0 && !text.slice(at+4,end).includes('<!--'));
      at=end+3;yield {index:start,0:text.slice(start,at)};continue;
    }
    if(/^<!doctype html>/i.test(text.slice(at,at+15))){need(stack.length===0);at+=15;continue;}
    at++;const closing=text[at]==='/';if(closing)at++;
    names.lastIndex=at;const match=names.exec(text);need(match);const tag=match[0].toLowerCase();at=names.lastIndex;
    need(tag!=='style');const attrs=new Map();let selfClosing=false,ended=false;
    while(at<text.length) {
      const separated=space();
      if(text[at]==='>'){at++;ended=true;break;}
      if(text[at]==='/' && text[at+1]==='>'){selfClosing=true;at+=2;ended=true;break;}
      need(!closing && separated);attributes.lastIndex=at;const name=attributes.exec(text);need(name);at=attributes.lastIndex;
      const key=name[0].toLowerCase();need(!attrs.has(key));let value=null;const afterName=at;
      space();
      if(text[at]==='=') {
        at++;space();need(at<text.length);const quote=text[at];
        if(quote==='"' || quote==="'") {
          const start=++at;while(at<text.length && text[at]!==quote){need(text[at]!=='<');at++;}
          need(at<text.length);value=text.slice(start,at);at++;
        } else {
          const start=at;while(at<text.length && !/[\t\n\r\f >]/.test(text[at])){need(!/["'<=`]/.test(text[at]));at++;}
          need(at>start);value=text.slice(start,at);
        }
      } else at=afterName;
      attrs.set(key,value);
      // Preserve the separator for the next attribute instead of accepting concatenated names.
      if(at<text.length && !/[\t\n\r\f />]/.test(text[at]))fail();
    }
    need(ended);
    if(closing){need(!selfClosing && attrs.size===0 && stack.pop()===tag);continue;}
    if(voids.has(tag))continue;
    need(!selfClosing);
    if(tag==='script') {
      const close=/<\/script[\t\n\r\f ]*>/ig;close.lastIndex=at;const found=close.exec(text);need(found);
      const body=text.slice(at,found.index);
      if(body.trim()) {need(attrs.get('type')==='application/ld+json' && !attrs.has('src'));JSON.parse(body);}
      at=close.lastIndex;continue;
    }
    need(stack.length<32);stack.push(tag);
  }
  need(stack.length===0);
}

export function createWebBuildObserver({root=repository, sourceCommit, sourceTree}={}) {
  root=fs.realpathSync(root);
  need(typeof sourceCommit==='string' && /^[a-f0-9]{40}$/.test(sourceCommit)
    && typeof sourceTree==='string' && /^[a-f0-9]{40}$/.test(sourceTree));
  const started=performance.now(), snapshots=new Map(), sourceInputs={}, total={bytes:0,outputBytes:0,noticeBytes:0};
  const tick=()=>need(performance.now()-started<LIMITS.seconds*1000);
  function read(name, limit=LIMITS.source, output=false) {
    tick();relative(name);const absolute=path.join(root,name);
    // This observer runs only in the trusted builder. Stable no-link source
    // witnesses supplement, rather than replace, receiver Git/blob checks.
    need(fs.realpathSync(absolute)===absolute);
    let fd;
    try {
      fd=fs.openSync(absolute,fs.constants.O_RDONLY|fs.constants.O_NOFOLLOW|fs.constants.O_NONBLOCK);
      const before=fs.fstatSync(fd,{bigint:true});
      need(before.isFile() && before.nlink===1n && before.size>=0n && before.size<=BigInt(limit));
      const key=output?'outputBytes':'bytes',cap=output?64_000_000:LIMITS.totalSource;
      need(total[key]+Number(before.size)<=cap);total[key]+=Number(before.size);
      const raw=Buffer.alloc(Number(before.size));let at=0;
      while(at<raw.length){tick();const n=fs.readSync(fd,raw,at,Math.min(65536,raw.length-at),null);need(n>0);at+=n;}
      need(stable(before)===stable(fs.fstatSync(fd,{bigint:true})) && stable(before)===stable(fs.lstatSync(absolute,{bigint:true})));
      snapshots.set(name,stable(before));return raw;
    } finally {if(fd!==undefined)fs.closeSync(fd);}
  }
  function notices(raw,syntax="javascript") {
    const text=raw.toString('utf8');
    if(!Buffer.from(text).equals(raw))return {text_source:false,notices:[]};
    if(syntax==='json'){JSON.parse(text);return {text_source:true,notices:[]};}
    need(syntax==='javascript' || syntax==='html');
    const result=[];let cursor=0,byteCursor=0,retained=0;
    const comments=syntax==='html'?htmlComments(text):text.matchAll(/\/\*[\s\S]*?\*\/|\/\/[^\r\n]*/g);
    for(const match of comments) {
      tick();const value=Buffer.from(match[0]);const offset=byteCursor+Buffer.byteLength(text.slice(cursor,match.index));
      cursor=match.index+match[0].length;byteCursor=offset+value.length;
      if(!/copyright|permission|licen[sc]e|SPDX/i.test(match[0]))continue;
      need(result.length<64 && retained+value.length<=16384 && total.noticeBytes+value.length<=256000);
      retained+=value.length;total.noticeBytes+=value.length;
      result.push({offset,bytes:value.length,sha256:hash(value),text:match[0]});
    }
    return {text_source:true,notices:result};
  }
  function source(name) {
    if(!Object.hasOwn(sourceInputs,name)) {
      const raw=read(name);sourceInputs[name]={bytes:raw.length,sha256:hash(raw),git_blob_oid:blob(raw),...notices(raw,name.endsWith('.html')?'html':name.endsWith('.json')?'json':'javascript')};
    }
    return sourceInputs[name];
  }
  function moduleRecord(id, info) {
    need(typeof id==='string' && id.length>0 && id.length<=1024 && info && typeof info==='object');
    const code=info.code;need(code===null || typeof code==='string');
    need(code===null || Buffer.byteLength(code)<=LIMITS.source);
    const transformed=code===null ? null : Buffer.from(code);
    need(transformed===null || transformed.length<=LIMITS.source);
    if(virtual.has(id)) return {id:'virtual:'+virtual.get(id),kind:'virtual',provider:virtual.get(id).startsWith('rolldown')?'rolldown':'vite',
      source_path:null,source:null,source_notices:transformed===null?[]:notices(transformed).notices,transformed:transformed===null?null:{bytes:transformed.length,sha256:hash(transformed)}};
    need(!id.includes('\0'));
    const physical=id.split('?',1)[0];need(path.isAbsolute(physical));
    const rel=path.relative(root,physical).split(path.sep).join('/');relative(rel);
    need(!rel.startsWith('../') && fs.realpathSync(physical)===physical);
    const rawSource=source(rel), query=id.slice(physical.length);
    need(query.length<=160 && /^[A-Za-z0-9_.?=&%-]*$/.test(query));
    return {id:'file:'+rel+query,kind:rel.startsWith('site/node_modules/')?'npm':'project',provider:null,
      source_path:rel,source:rawSource,source_notices:rawSource.notices,transformed:transformed===null?null:{bytes:transformed.length,sha256:hash(transformed)}};
  }
  function recheck() {
    for(const [name,before] of snapshots){tick();need(fs.realpathSync(path.join(root,name))===path.join(root,name));need(stable(fs.lstatSync(path.join(root,name),{bigint:true}))===before);}
  }
  return {
    name:'aitrust-web-build-observations',enforce:'post',
    writeBundle(outputOptions,bundle) {
      let fd,attempted=false,failure=null;
      try {
        tick();need(outputOptions && typeof outputOptions.dir==='string');
        const directory=path.resolve(outputOptions.dir);need(directory===path.join(root,'site/dist') && fs.realpathSync(directory)===directory);
        for(const name of fixedInputs)source(name);
        for(const [provider,version] of [['vite','8.3.4'],['rolldown','1.2.13']]) {
          const name='site/node_modules/'+provider+'/package.json';source(name);
          const metadata=JSON.parse(read(name).toString('utf8'));
          need(metadata && metadata.name===provider && metadata.version===version);
        }
        const ids=[], records={}, outputs={},translated=new Map(),chunkOnly=new Map();let associations=0;
        for(const id of this.getModuleIds()){need(ids.length<LIMITS.modules);ids.push(id);}
        for(const id of ids){const record=moduleRecord(id,this.getModuleInfo(id));need(!Object.hasOwn(records,record.id));records[record.id]=record;translated.set(id,record.id);}
        for(const [name,value] of ownEntries(bundle,LIMITS.files)) {
          tick();relative(name);need(value && value.fileName===name && ['chunk','asset'].includes(value.type));
          let raw,modules=[];
          if(value.type==='chunk') {
            need(typeof value.code==='string');need(Buffer.byteLength(value.code)<=12_000_000);raw=Buffer.from(value.code);
            for(const [id,item] of ownEntries(value.modules,LIMITS.modules)) {
              if(!translated.has(id)) {
                // Rolldown's generated runtime can be absent from its module graph.
                // Only this existing provider identity may come from actual chunk code.
                need(id==='\0rolldown/runtime.js' && item && typeof item.code==='string');
                need(Object.keys(records).length<LIMITS.modules);
                const record=moduleRecord(id,{code:item.code});need(!Object.hasOwn(records,record.id));
                records[record.id]=record;translated.set(id,record.id);chunkOnly.set(id,item.code);
              }
              if(chunkOnly.has(id))need(item && item.code===chunkOnly.get(id));
              need(translated.has(id) && item && Number.isSafeInteger(item.renderedLength) && item.renderedLength>=0);
              need(++associations<=8192 && item.renderedLength<=12_000_000);
              modules.push({id:translated.get(id),rendered_length:item.renderedLength});
            }
            need(Array.isArray(value.imports) && Array.isArray(value.dynamicImports));
            need(value.imports.length<=2048 && value.dynamicImports.length<=2048);
            for(const list of [value.imports,value.dynamicImports])for(const dependency of list){need(++associations<=8192);relative(dependency);}
          } else {
            need(typeof value.source==='string' || value.source instanceof Uint8Array);
            need((typeof value.source==='string'?Buffer.byteLength(value.source):value.source.byteLength)<=12_000_000);raw=Buffer.from(value.source);
          }
          need(raw.length<=12_000_000);
          const actual=read('site/dist/'+name,12_000_000,true);need(actual.equals(raw));
          outputs[name]={kind:value.type,bytes:raw.length,sha256:hash(raw),modules:modules.sort((a,b)=>a.id<b.id?-1:a.id>b.id?1:0),
            imports:value.type==='chunk'?[...value.imports].sort():[],dynamic_imports:value.type==='chunk'?[...value.dynamicImports].sort():[]};
        }
        need(Object.keys(outputs).length>0 && Object.values(outputs).some(o=>o.kind==='chunk'));
        recheck();
        const record={profile:PROFILE,source_commit:sourceCommit,source_tree_oid:sourceTree,
          sources:sourceInputs,modules:records,outputs,toolchain:{vite:'8.3.4',rolldown:'1.2.13'},
          claims:{permission_issued:false,release_authorized:false,compiled_equivalence_proved:false}};
        let nodes=0;
        function encodedLength(v,depth=0) {
          need(++nodes<=100000 && depth<=32);
          if(v===null || typeof v!=='object')return Buffer.byteLength(JSON.stringify(v));
          if(Array.isArray(v)){let n=2;for(const x of v){n+=encodedLength(x,depth+1)+1;need(n<=LIMITS.bytes);}return n;}
          let n=2;for(const [k,x] of Object.entries(v)){n+=Buffer.byteLength(JSON.stringify(k))+1+encodedLength(x,depth+1)+1;need(n<=LIMITS.bytes);}return n;
        }
        need(encodedLength(record)+1<=LIMITS.bytes);
        const raw=Buffer.from(canonical(record)+'\n');need(raw.length<=LIMITS.bytes);
        const name=path.join(directory,'web-build-observations.json');
        try{fs.lstatSync(name);fail();}catch(error){if(error.code!=='ENOENT')throw error;}
        attempted=true;fd=fs.openSync(name,fs.constants.O_RDWR|fs.constants.O_CREAT|fs.constants.O_EXCL|fs.constants.O_NOFOLLOW,0o644);
        let at=0;while(at<raw.length){tick();const n=fs.writeSync(fd,raw,at,Math.min(65536,raw.length-at));need(n>0);at+=n;}
        fs.fsyncSync(fd);need(fs.fstatSync(fd).size===raw.length);recheck();
      } catch(error) {failure=error;}
      finally {
        if(fd!==undefined){const owned=fd;fd=undefined;try{fs.closeSync(owned);}catch(error){failure??=error;}}
      }
      if(failure)throw attempted?new BuildObservationUncertain():new BuildObservationUnavailable();
    }
  };
}

export default async function config() {
  // Imported only for an intentional real build. Importing the inert factory
  // above does not load Vite, Rolldown, Tailwind or a native package.
  const env={PATH:process.env.PATH||'/usr/bin:/bin'};
  if(Object.hasOwn(process.env,'HOME'))env.HOME=process.env.HOME;
  const git=(args)=>execFileSync('git',args,{cwd:repository,env,timeout:5000,maxBuffer:256,encoding:'utf8'}).trim();
  const commit=git(['rev-parse','HEAD']),tree=git(['rev-parse','HEAD^{tree}']);
  need(/^[a-f0-9]{40}$/.test(commit) && /^[a-f0-9]{40}$/.test(tree));
  for(const [provider,version] of [['vite','8.3.4'],['rolldown','1.2.13'],['@tailwindcss/vite','4.3.3']]) {
    const name=path.join(repository,'site/node_modules',provider,'package.json');
    need(fs.realpathSync(name)===name);const fd=fs.openSync(name,fs.constants.O_RDONLY|fs.constants.O_NOFOLLOW);
    let raw;try{const info=fs.fstatSync(fd);need(info.isFile() && info.size>0 && info.size<=2_000_000);raw=Buffer.alloc(info.size);let at=0;while(at<raw.length){const n=fs.readSync(fd,raw,at,raw.length-at,null);need(n>0);at+=n;}}finally{fs.closeSync(fd);}
    const metadata=JSON.parse(raw.toString('utf8'));need(metadata.name===provider && metadata.version===version);
  }
  const loaded=await import(new URL('../site/vite.config.js',import.meta.url));
  need(loaded.default && typeof loaded.default==='object' && Array.isArray(loaded.default.plugins));
  return {...loaded.default,plugins:[...loaded.default.plugins,createWebBuildObserver({root:repository,sourceCommit:commit,sourceTree:tree})]};
}
