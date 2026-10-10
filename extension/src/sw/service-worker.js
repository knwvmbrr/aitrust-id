import '../shared/contract.js';
const ENDPOINT='http://127.0.0.1:8787/v1/evaluate';
const MAX_RESPONSE_BYTES=2*1024*1024;
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
  if(msg?.type!=='evaluate')return false;
  let answered=false;const reply=result=>{if(answered)return;answered=true;try{respond(result);}catch{/* Closed extension channel; never log response text. */}};
  let url;try{url=new URL(sender.url);}catch{reply({status:'unsupported',reason:'Unsupported sender.'});return false;}
  if(url.origin!=='https://chatgpt.com'||!AITrustContract.scalarText(msg.text)){reply({status:'unsupported',reason:'Unsupported request.'});return false;}
  (async()=>{
    try{
      const {token}=await chrome.storage.local.get('token');
      if(typeof token!=='string'||token==='change-me'||token.length<16||token.length>4096){reply({status:'unavailable',reason:'Set the local token in extension options.'});return;}
      const response=await fetch(ENDPOINT,{method:'POST',headers:{'content-type':'application/json',authorization:`Bearer ${token}`},body:JSON.stringify({text:msg.text,origin_host:url.hostname,modality:'text'}),redirect:'error',cache:'no-store',credentials:'omit',signal:AbortSignal.timeout(15000)});
      if(!response.ok){reply({status:'unavailable',reason:response.status===401?'The local token is invalid.':'The local service could not complete the check.'});return;}
      const assertion=await boundedJSON(response),contract=AITrustContract.inspect(assertion);
      if(contract.status!=='accepted'){reply({status:contract.status==='unsupported'?'unsupported':'unavailable',reason:contract.reason});return;}
      reply({status:'ok',assertion});
    }catch{reply({status:'unavailable',reason:'The local service is unavailable or timed out.'});}
  })();return true;
});
