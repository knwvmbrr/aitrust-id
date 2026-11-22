'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const ROOT=path.resolve(__dirname,'..'),BASE='026634ea7715c205d5fc6ec4e805409f6dfe573c';
function baseline(){
 const file=path.join(ROOT,'tests/fixtures/fa-image-main-baseline.json');let fd=fs.openSync(file,fs.constants.O_RDONLY|fs.constants.O_NOFOLLOW|fs.constants.O_NONBLOCK);
 try{const info=fs.fstatSync(fd);assert(info.isFile()&&info.size>0&&info.size<=200000);const bytes=Buffer.alloc(200001);let length=0;while(true){const n=fs.readSync(fd,bytes,length,bytes.length-length,null);if(!n)break;length+=n;assert(length<=200000);}const raw=bytes.subarray(0,length);assert.equal(crypto.createHash('sha256').update(raw).digest('hex'),'7567b8d6ff6229f73e274badbfa4beff3cd691c3bf6f523f7ea72c164af6621a');const value=JSON.parse(raw);assert.equal(value.format,'FA-integration-sibling-baseline/v1');assert.equal(value.source_commit,BASE);return value;}finally{const owned=fd;fd=undefined;fs.closeSync(owned);}
}
(async()=>{
 const [catalog,presentation,usage]=await Promise.all([import('../site/src/catalog.js'),import('../site/src/presentation.js'),import('../site/src/usage.js')]);
 const original=baseline(),oldBy=new Map(original.records.map(r=>[r.id,r]));let siblings=0;
 for(const tag of catalog.allTags){const before=oldBy.get(tag.id);assert(before);if(tag.id==='FA')continue;assert.deepEqual(tag,before);assert.deepEqual(presentation.presentation(tag),original.projections[tag.id].presentation);assert.deepEqual(usage.usage(tag),original.projections[tag.id].usage);assert.equal(usage.usageHTML(tag,String),original.projections[tag.id].usageHTML);siblings++;}assert.equal(siblings,19);
 const fa=catalog.allTags.find(t=>t.id==='FA'),prior=oldBy.get('FA');for(const key of ['id','code','name','status','scopeId','claim','outcome','job','floor','release','validation','features','proposed'])assert.deepEqual(fa[key],prior[key]);assert.equal(presentation.presentation(fa).working,false);assert.equal(presentation.presentation(fa).stage,'Planned');assert(presentation.presentation(fa).availability.startsWith('Planned tag'));assert(presentation.presentation(fa).limit.includes('full FA tag is still planned'));assert.equal(usage.usage(fa).available,false);assert.deepEqual(usage.usage(fa).links,[{label:'Private image-details guide',href:'/reference/image-device-guide.md'}]);assert(!usage.usage(fa).links.some(l=>l.label==='Download source'));
 const {waitImageProbeReady,waitDisclosureProbeReady}=require('../scripts/verify-site-accessibility.cjs');
 for(const run of [waitImageProbeReady,waitDisclosureProbeReady]){
  let release,entered;const gate=new Promise(r=>release=r),readyEntered=new Promise(r=>entered=r);let completed=false,child=0,ready=0;
  const detail={async getAttribute(name){return name==='data-image-device-method'?'':null;},locator(selector){return {waitFor:async()=>{if(selector==='[data-image-metadata-explorer]'){child++;return;}assert.equal(selector,'[data-image-metadata-explorer] button[type="submit"]:not([disabled])');ready++;entered();await gate;}};}};
  const checking=run(detail).then(()=>{completed=true;});assert.equal(await Promise.race([checking.then(()=>false),readyEntered.then(()=>true)]),true,'Readiness completed without waiting for the enabled image control');assert.equal(completed,false);assert.equal(child,1);assert.equal(ready,1);release();await checking;assert.equal(completed,true);
 }
 const source=fs.readFileSync(path.join(ROOT,'site/src/main.jsx'),'utf8');assert.equal((source.match(/tag[.]id==='FA'&&<ImageDetailsPreview\/>/g)||[]).length,1);assert(source.includes('data-image-device-method'));const a=source.indexOf('function ImageDetailsPreview(){'),z=source.indexOf('\n}',a)+2,wrapper=source.slice(a,z);assert(wrapper.includes("attributeOldValue:true")&&wrapper.includes('setGeneration')&&wrapper.includes('{open&&<ImageMetadataExplorerSlot key={generation}/>}'));assert(!source.includes("tag.id==='PA'&&<Image"));
 const prepare=fs.readFileSync(path.join(ROOT,'site/scripts/prepare.mjs'),'utf8');assert(prepare.includes("scripts/build-image-metadata-device.py")&&prepare.includes("docs/image-device-guide.md"));

 const guide=fs.readFileSync(path.join(ROOT,'docs/image-device-guide.md'),'utf8');assert(guide.includes('**FA** modal')&&guide.includes('full FA tag remains Planned')&&guide.includes('encoded-file SHA256')&&guide.includes('does not by itself\nguarantee offline availability'));
 console.log(JSON.stringify({pass:true,groups:5,sibling_records_preserved:siblings,PA_unchanged:true,FA_Planned_not_issued:true,closed_epoch_mount:true,ready_control_gate:true,baseline_pinned_portable_no_git:true,production_browser_executed:false}));
})().catch(error=>{console.error(error);process.exitCode=1;});
