globalThis.fixtureRoots=new Map();
const attach=Element.prototype.attachShadow;
Element.prototype.attachShadow=function(options){const root=attach.call(this,new URLSearchParams(location.search).has("open-shadow")?{...options,mode:"open"}:options);fixtureRoots.set(this,root);return root;};
// Synthetic responses only; deterministic delayed checks exercise revision races.
globalThis.fixtureRequests=[];
globalThis.fixtureResponders=[];
globalThis.chrome={runtime:{sendMessage:msg=>new Promise(resolve=>{fixtureRequests.push(msg);fixtureResponders.push(resolve);})}};
globalThis.fixtureResult=(text,signal='sig.piped_installer.v2')=>({status:'ok',assertion:{assertion_id:crypto.randomUUID(),subject:{char_len:Array.from(text).length},tags:text.includes('curl')?[{code:'PS',signals:[{id:signal,score:.97,spans:[[0,Array.from(text).length]]}]}]:[],abstentions:[],evaluator:{calibration_id:'synthetic-uncalibrated'}}});
