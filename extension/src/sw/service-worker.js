import '../shared/contract.js';
const ENDPOINT='http://127.0.0.1:8787/v1/evaluate';
const MAX_RESPONSE_BYTES=2*1024*1024;
const active=new Set();let generation=0;
chrome.storage.onChanged.addListener((changes,area)=>{
 if(area==='local'&&(changes.checks_enabled||changes.token)){generation++;for(const controller of active)controller.abort();}
});
async function boundedJSON(response){
  if(!/^application\/json(?:\s*;\s*charset=utf-8)?\s*$/i.test(response.headers.get('content-type')||''))throw Error('Unsupported response content type');
  const declared=response.headers.get('content-length');if(declared!==null&&(!/^\d+$/.test(declared)||Number(declared)>MAX_RESPONSE_BYTES))throw Error('Oversized response');
  if(!response.body)throw Error('Missing response stream');
  const reader=response.body.getReader(),parts=[];let total=0;
  try{while(true){const {value,done}=await reader.read();if(done)break;total+=value.byteLength;if(total>MAX_RESPONSE_BYTES)throw Error('Oversized response');parts.push(value);}}
  catch(error){try{await reader.cancel();}catch{}throw error;}
  finally{reader.releaseLock();}
  const bytes=new Uint8Array(total);let offset=0;for(const part of parts){bytes.set(part,offset);offset+=part.byteLength;}
  return JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(bytes));
}
chrome.runtime.onMessage.addListener((msg,sender,respond)=>{
  if(msg?.type==='open_settings'){
    let origin;try{origin=new URL(sender.url).origin;}catch{return false;}
    if(origin!=='https://chatgpt.com')return false;
    chrome.runtime.openOptionsPage().then(()=>respond({status:'ok'})).catch(()=>respond({status:'unavailable'}));return true;
  }
  if(msg?.type!=='evaluate')return false;
  let answered=false;const reply=result=>{if(answered)return;answered=true;try{respond(result);}catch{/* Closed extension channel; never log response text. */}};
  let url;try{url=new URL(sender.url);}catch{reply({status:'unsupported',reason:'Unsupported sender.'});return false;}
  if(url.origin!=='https://chatgpt.com'||!AITrustContract.scalarText(msg.text)){reply({status:'unsupported',reason:'Unsupported request.'});return false;}
  const revision=generation;
  (async()=>{
    let controller,timer;
    try{
      const {token,checks_enabled}=await chrome.storage.local.get(['token','checks_enabled']);
      if(revision!==generation||checks_enabled!==true){reply({status:'unavailable',reason:'Checks are paused. Enable ChatGPT checks in extension settings.'});return;}
      if(typeof token!=='string'||token==='change-me'||token.length<16||token.length>4096||!(/^[\x21-\x7e]+$/).test(token)){reply({status:'unavailable',reason:'Set the local token in extension options.'});return;}
      controller=new AbortController();active.add(controller);timer=setTimeout(()=>controller.abort(),15000);
      const response=await fetch(ENDPOINT,{method:'POST',headers:{'content-type':'application/json',authorization:`Bearer ${token}`},body:JSON.stringify({text:msg.text,origin_host:url.hostname,modality:'text'}),redirect:'error',cache:'no-store',credentials:'omit',signal:controller.signal});
      if(!response.ok){reply({status:'unavailable',reason:response.status===401?'The local token is invalid.':'The local service could not complete the check.'});return;}
      const assertion=await boundedJSON(response),contract=AITrustContract.inspect(assertion);
      if(contract.status!=='accepted'){reply({status:contract.status==='unsupported'?'unsupported':'unavailable',reason:contract.reason});return;}
      if(controller.signal.aborted||revision!==generation){reply({status:'unavailable',reason:'Settings changed. Run a new check after enabling checks.'});return;}
      reply({status:'ok',assertion});
    }catch{reply({status:'unavailable',reason:controller?.signal.aborted?'The check was cancelled or timed out.':'The local service is unavailable or timed out.'});}
    finally{clearTimeout(timer);if(controller)active.delete(controller);}
  })();return true;
});
