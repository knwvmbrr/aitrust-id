globalThis.fixtureRoots=new Map();
const attach=Element.prototype.attachShadow;
Element.prototype.attachShadow=function(options){const root=attach.call(this,new URLSearchParams(location.search).has("open-shadow")?{...options,mode:"open"}:options);fixtureRoots.set(this,root);return root;};
// Synthetic responses only; deterministic delayed checks exercise revision races.
globalThis.fixtureRequests=[];
globalThis.fixtureResponders=[];
globalThis.fixtureSettings={checks_enabled:true};globalThis.fixtureStorageListeners=[];
globalThis.chrome={storage:{local:{get:async()=>({...fixtureSettings})},onChanged:{addListener:listener=>fixtureStorageListeners.push(listener)}},runtime:{sendMessage:msg=>{if(msg.type==='open_settings')return Promise.resolve({status:'ok'});return new Promise(resolve=>{fixtureRequests.push(msg);fixtureResponders.push(resolve);});}}};
globalThis.fixtureConsent=value=>{const oldValue=fixtureSettings.checks_enabled;fixtureSettings.checks_enabled=value;fixtureStorageListeners.forEach(listener=>listener({checks_enabled:{oldValue,newValue:value}},'local'));};
globalThis.fixtureResult=(text,signal='sig.piped_installer.v3')=>({status:'ok',assertion:{assertion_id:crypto.randomUUID(),spec_version:'0.1.0',subject:{sha256:'a'.repeat(64),char_len:Array.from(text).length,modality:'text',origin_host:'chatgpt.com',captured_at:new Date().toISOString()},tags:text.includes('curl')?[{code:'PS',state:'asserted',confidence:.97,floor:.7,signals:[{id:signal,score:.97,spans:[[0,Array.from(text).length]]}]}]:[],abstentions:[],evaluator:{models:[{name:'synthetic fixture',sha256:'b'.repeat(64),revision:'fixture-v1'}],calibration_id:'synthetic-uncalibrated',latency_ms:1}}});
