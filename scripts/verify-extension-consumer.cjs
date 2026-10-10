const {writeReport}=require('./execution-report.cjs');
const fs=require('node:fs'),vm=require('node:vm'),crypto=require('node:crypto');
const assert=(v,message)=>{if(!v)throw Error(message);};
const valid=()=>({assertion_id:crypto.randomUUID(),spec_version:'0.1.0',subject:{sha256:'a'.repeat(64),char_len:100,origin_host:'chatgpt.com',captured_at:new Date().toISOString(),modality:'text'},tags:[{code:'PS',confidence:.97,floor:.7,state:'asserted',signals:[{id:'sig.piped_installer.v3',score:.97,spans:[[4,20]]}]}],abstentions:[],evaluator:{models:[{name:'rules-only',sha256:'b'.repeat(64),revision:'fixture-v1'}],calibration_id:'uncalibrated',latency_ms:1}});
const contractSource=fs.readFileSync('extension/src/shared/contract.js','utf8');
async function request({message={type:'evaluate',text:'Synthetic command text'},sender={url:'https://chatgpt.com/c/synthetic'},token=crypto.randomBytes(24).toString('hex'),response,fetchFault=false,storageFault=false,closedChannel=false,noCredential=false}={}){
 let listener,reply,fetches=0,options,endpoint,replies=0,cancelled=false,secret=token;
 const sandbox={URL,AbortSignal,TextDecoder,Uint8Array,Date,Set,Number,chrome:{runtime:{onMessage:{addListener:f=>listener=f}},storage:{local:{get:async()=>{if(storageFault)throw Error('Synthetic storage error');return noCredential?{}:{token};}}}},fetch:async(url,init)=>{fetches++;endpoint=url;options=init;if(fetchFault)throw Error('Synthetic network failure');return typeof response==='function'?response(()=>cancelled=true):response||new Response(JSON.stringify(valid()),{headers:{'content-type':'application/json'}});}};
 vm.createContext(sandbox);vm.runInContext(contractSource,sandbox);
 const source=fs.readFileSync('extension/src/sw/service-worker.js','utf8').replace(/^import '\.\.\/shared\/contract\.js';\n/,'');
 vm.runInContext(source,sandbox);
 const retained=listener(message,sender,result=>{replies++;if(closedChannel)throw Error('Synthetic closed channel');reply=result;});
 if(retained)for(let i=0;i<1000&&!replies;i++)await new Promise(resolve=>setTimeout(resolve,1));
 if(message.type==='evaluate')assert(replies===1,'Expected exactly one terminal response');
 if(options){assert(endpoint==='http://127.0.0.1:8787/v1/evaluate','Changed endpoint');assert(options.redirect==='error'&&options.cache==='no-store'&&options.credentials==='omit','Unsafe fetch flags');assert(options.headers.authorization==='Bearer '+secret,'Wrong local credential');}
 return {reply,fetches,retained,cancelled};
}
async function verify(){
 const cases=[];
 async function check(name,settings,status,fetches){const result=await request(settings);assert(result.reply?.status===status,name+' incorrect state');if(fetches!==undefined)assert(result.fetches===fetches,name+' unexpectedly contacted a service');cases.push({name,status,pass:true});return result;}
 await check('valid_unsigned',{ },'ok',1);
 await check('wrong_origin',{sender:{url:'https://hostile.test/'}},'unsupported',0);
 await check('bad_sender',{sender:{url:'not a URL'}},'unsupported',0);
 await check('missing_token',{noCredential:true},'unavailable',0);
 await check('absent_credential',{token:null},'unavailable',0);
 await check('short_credential',{token:'short'},'unavailable',0);
 await check('placeholder_credential',{token:'change-me'},'unavailable',0);
 await check('storage_failure',{storageFault:true},'unavailable',0);
 await check('empty_text',{message:{type:'evaluate',text:''}},'unsupported',0);
 await check('unpaired_surrogate',{message:{type:'evaluate',text:'\ud800'}},'unsupported',0);
 await check('oversized_text',{message:{type:'evaluate',text:'x'.repeat(200001)}},'unsupported',0);
 await check('astral_codepoint_boundary',{message:{type:'evaluate',text:'🧪'.repeat(200000)}},'ok',1);
 for(const status of [401,422,500,504])await check('http_'+status,{response:new Response('{}',{status,headers:{'content-type':'application/json'}})},'unavailable',1);
 await check('network_or_timeout',{fetchFault:true},'unavailable',1);
 await check('non_json',{response:new Response('<html>wrong service</html>',{headers:{'content-type':'text/html'}})},'unavailable',1);
 await check('malformed_json',{response:new Response('private canary',{headers:{'content-type':'application/json'}})},'unavailable',1);
 await check('invalid_utf8',{response:new Response(new Uint8Array([0xff]),{headers:{'content-type':'application/json'}})},'unavailable',1);
 await check('declared_oversize',{response:new Response('{}',{headers:{'content-type':'application/json','content-length':'2097153'}})},'unavailable',1);
 const overflow=await check('chunked_oversize',{response:cancel=>new Response(new ReadableStream({pull(controller){controller.enqueue(new Uint8Array(1048576));},cancel(){cancel();}}),{headers:{'content-type':'application/json'}})},'unavailable',1);assert(overflow.cancelled,'Oversized stream not cancelled');
 for(const [name,mutate,status] of [
  ['future_version',a=>a.spec_version='0.2.0','unsupported'],['signed_unverified',a=>a.signature={alg:'ed25519',key_id:'test',sig:'fixture'},'unsupported'],['reserved_modality',a=>a.subject.modality='audio','unsupported'],
  ['missing_subject_hash',a=>delete a.subject.sha256,'unavailable'],['malformed_hash',a=>a.subject.sha256='wrong','unavailable'],['bad_uuid',a=>a.assertion_id='bad','unavailable'],['bad_date',a=>a.subject.captured_at='2026-02-31T00:00:00Z','unavailable'],['negative_length',a=>a.subject.char_len=-1,'unavailable'],['unknown_tag',a=>a.tags[0].code='BT','unavailable'],['disabled_tag',a=>a.tags[0].code='HP','unavailable'],['below_floor_asserted',a=>a.tags[0].confidence=.6,'unavailable'],['invalid_signal_id',a=>a.tags[0].signals[0].id='<img>','unavailable'],['invalid_span',a=>a.tags[0].signals[0].spans=[[0,101]],'unavailable'],['invalid_score',a=>a.tags[0].signals[0].score=1.2,'unavailable'],['missing_model',a=>a.evaluator.models=[],'unavailable'],['duplicate_tag',a=>a.tags.push(a.tags[0]),'unavailable']]){const a=valid();mutate(a);await check(name,{response:new Response(JSON.stringify(a),{headers:{'content-type':'application/json'}})},status,1);}
 const closed=await request({closedChannel:true});assert(closed.fetches===1,'Closed channel reissued a check');
 const unrelated=await request({message:{type:'other'}});assert(unrelated.retained===false&&unrelated.fetches===0,'Unrelated message processed');
 const paths=['extension/src/shared/contract.js','extension/src/sw/service-worker.js','extension/src/content/bridge.js','extension/manifest.json'];
 return {captured_at:new Date().toISOString(),pass:true,cases,case_count:cases.length,stream_overflow_cancelled:true,one_terminal_response:true,closed_channel_safe:true,unrelated_messages_ignored:true,redirects_refused:true,browser_cache_disabled:true,credential_destination:'fixed_authenticated_loopback_only',real_web_stream_response_types:true,synthetic_chrome_storage_and_fetch:true,live_vendor_compatibility:false,installed_extension_refresh_verified:false,source_sha256:Object.fromEntries(paths.map(p=>[p,crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex')]))};
}
module.exports={verify,request,valid};
if(require.main===module)verify().then(result=>{writeReport(process.env.AITRUST_CONSUMER_REPORT||'output/verification/extension-consumer.json',result);console.log(JSON.stringify(result));}).catch(error=>{console.error(error.message);process.exitCode=1;});
