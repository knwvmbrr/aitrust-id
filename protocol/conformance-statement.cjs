/* Evidence-bound self-declaration; no certification or trademark authorization. */
'use strict';
const fs=require('node:fs'),crypto=require('node:crypto'),path=require('node:path');
const {parse,canonical}=require('./receipts.cjs');
const VERSION='implementation-self-declaration/1.0.0',MAX=262144;
const keys=(v,n)=>{if(!v||typeof v!=='object'||Array.isArray(v)||Object.keys(v).sort().join('|')!==[...n].sort().join('|'))throw Error('Unknown or missing declaration field');};
function text(v,max=240){if(typeof v!=='string'||!v.trim()||v.length>max||/[\u0000-\u001f\u007f]|[\uD800-\uDBFF](?![\uDC00-\uDFFF])|(?<![\uD800-\uDBFF])[\uDC00-\uDFFF]/u.test(v))throw Error('Invalid declaration text');return v;}
function read(file){
 const absolute=path.resolve(file);if(fs.realpathSync(path.dirname(absolute))!==path.dirname(absolute))throw Error('Symlink directory refused');
 const fd=fs.openSync(absolute,fs.constants.O_RDONLY|fs.constants.O_NOFOLLOW|fs.constants.O_NONBLOCK);
 try{const stat=fs.fstatSync(fd);if(!stat.isFile()||stat.size>MAX)throw Error('Unsupported evidence file');const raw=Buffer.alloc(MAX+1);let size=0;while(size<raw.length){const n=fs.readSync(fd,raw,size,raw.length-size,null);if(!n)break;size+=n;}if(size>MAX)throw Error('Evidence read limit');return raw.subarray(0,size);}finally{fs.closeSync(fd);}
}
function declaration(input,base,issuedAt=new Date().toISOString()){
 keys(input,['version','publisher','implementation','source_revision','profile','limitations','checks']);
 if(input.version!==VERSION||typeof input.source_revision!=='string'||!/^[a-f0-9]{40}$/.test(input.source_revision)||input.profile!=='engineering-self-declaration')throw Error('Unsupported declaration profile or revision');
 text(input.publisher,160);text(input.implementation,160);
 if(!Array.isArray(input.limitations)||!input.limitations.length||input.limitations.length>16)throw Error('Explicit limitations required');input.limitations.forEach(v=>text(v,400));
 if(!Array.isArray(input.checks)||!input.checks.length||input.checks.length>64)throw Error('Evidence checks required');
 const names=new Set();const checks=input.checks.map(c=>{
  keys(c,['name','result','evidence']);text(c.name,100);
  if(names.has(c.name)||!['pass','fail','not_tested'].includes(c.result))throw Error('Duplicate or unsupported check');names.add(c.name);
  if(c.result==='not_tested'){if(c.evidence!==null)throw Error('Untested check must not invent evidence');return {name:c.name,result:c.result,evidence_sha256:null,evidence_bytes:null};}
  text(c.evidence,512);if(path.isAbsolute(c.evidence)||c.evidence.split(/[\\/]/).some(p=>['..','','.'].includes(p)))throw Error('Use a relative evidence path without traversal');
  const file=path.resolve(base,c.evidence);const raw=read(file);
  return {name:c.name,result:c.result,evidence_sha256:crypto.createHash('sha256').update(raw).digest('hex'),evidence_bytes:raw.length};
 });
 if(typeof issuedAt!=='string'||!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$/.test(issuedAt)||!Number.isFinite(Date.parse(issuedAt))||new Date(issuedAt).toISOString()!==issuedAt)throw Error('Invalid declaration date');
 return {version:VERSION,issued_at:issuedAt,clock:'publisher_local_clock_unverified',publisher:input.publisher,implementation:input.implementation,source_revision:input.source_revision,profile:input.profile,claim:'self_declared_engineering_checks',checks,limitations:input.limitations,all_declared_checks_pass:checks.every(c=>c.result==='pass'),independent_accuracy_validated:false,certification:false,mark_authorization:false,signature_verified:false,evidence_contents_included:false};
}
function load(file){return parse(read(file));}
function verify(input,base,statement){
 const expected=declaration(input,base,statement.issued_at);
 if(canonical(expected)!==canonical(statement))throw Error('Statement or evidence changed');
 return {status:'local_evidence_bytes_match',declared_results_verified_as_truth:false,publisher_and_time_authenticated:false,source_revision_verified:false,certification:false,mark_authorization:false};
}
module.exports=Object.freeze({VERSION,declaration,verify,load,read});
