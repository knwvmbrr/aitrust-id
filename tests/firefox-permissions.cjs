const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const source=fs.readFileSync('extension/src/firefox/permissions.js','utf8');
const flush=async()=>{for(let i=0;i<4;i++)await new Promise(resolve=>setImmediate(resolve));};
function fixture({granted=false,initial={}}={}){
 const events={},storageEvents=[],removedEvents=[],requests=[];let permissions=granted,resolveRequest,rejectRequest;
 const values={...initial},control={checked:false,disabled:false,addEventListener:(name,fn)=>events[name]=fn},status={textContent:''};
 const changes=data=>{const result={};for(const [key,value]of Object.entries(data)){result[key]={oldValue:values[key],newValue:value};values[key]=value;}for(const listener of storageEvents)listener(result,'local');};
 const clear={addEventListener:(_,fn)=>events.reset=fn};
 const sandbox={document:{querySelector:id=>({'#checks-enabled':control,'#status':status,'#clear':clear}[id])},
  chrome:{storage:{onChanged:{addListener:fn=>storageEvents.push(fn)},local:{set:async data=>changes(data)}}},
  browser:{permissions:{contains:async()=>permissions,onRemoved:{addListener:fn=>removedEvents.push(fn)},
   request:input=>{requests.push(input);return new Promise((resolve,reject)=>{resolveRequest=value=>{permissions=value;resolve(value);};rejectRequest=reject;});}}},
  refresh:()=>{control.checked=values.checks_enabled===true;control.disabled=false;}};
 vm.runInNewContext(source,sandbox);
 return {values,control,status,requests,changes,events,grant:value=>resolveRequest(value),reject:()=>rejectRequest(Error('synthetic refusal')),
  revoke:async origins=>{permissions=false;await removedEvents[0]({origins});},
  click:()=>{control.checked=true;let prevented=false,stopped=false;events.click({preventDefault:()=>prevented=true,stopImmediatePropagation:()=>stopped=true});return{prevented,stopped};}};
}
test('startup never requests browser permission and invalid saved consent is paused',async()=>{
 const f=fixture({initial:{checks_enabled:true}});await flush();assert.equal(f.requests.length,0);assert.equal(f.values.checks_enabled,false);
});
test('enable synchronously requests only the declared two origins',async()=>{
 const f=fixture();await flush();assert.deepEqual(f.click(),{prevented:true,stopped:true});assert.equal(f.requests.length,1);
 assert.deepEqual(Array.from(f.requests[0].origins),['https://chatgpt.com/*','http://127.0.0.1/*']);assert.equal(f.values.checks_enabled,false);
 f.grant(true);await flush();assert.equal(f.values.checks_enabled,true);assert.equal(f.control.disabled,false);
});
test('already granted browser permission is not application consent',async()=>{
 const f=fixture({granted:true,initial:{checks_enabled:false}});await flush();assert.equal(f.requests.length,0);assert.equal(f.values.checks_enabled,false);
 assert.deepEqual(f.click(),{prevented:false,stopped:false});assert.equal(f.requests.length,0);
});
for(const action of ['reset','token','gateway_public_key','revoked'])test('late grant cannot undo '+action,async()=>{
 const f=fixture();await flush();f.click();
 if(action==='reset')f.events.reset();else if(action==='revoked')await f.revoke(['http://127.0.0.1/*']);else f.changes({[action]:'replacement'});
 f.grant(true);await flush();assert.equal(f.values.checks_enabled,false);assert.equal(f.control.disabled,false);
});
test('denial leaves checks paused',async()=>{
 const f=fixture();await flush();f.click();f.grant(false);await flush();assert.equal(f.values.checks_enabled,false);assert.match(f.status.textContent,/not granted/);assert.equal(f.control.disabled,false);
});
test('request failure leaves checks paused',async()=>{
 const f=fixture();await flush();f.click();f.reject();await flush();assert.equal(f.values.checks_enabled,false);assert.equal(f.control.disabled,false);
});
test('canonicalized origin revocation pauses active checks',async()=>{
 const f=fixture({granted:true,initial:{checks_enabled:true}});await flush();await f.revoke(['http://127.0.0.1/*']);assert.equal(f.values.checks_enabled,false);
});
