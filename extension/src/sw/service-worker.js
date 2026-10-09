const ENDPOINT='http://127.0.0.1:8787/v1/evaluate';
chrome.runtime.onMessage.addListener((msg,sender,respond)=>{
  if(msg?.type!=='evaluate')return false;
  let url;try{url=new URL(sender.url);}catch{respond({status:'unavailable',reason:'Unsupported sender.'});return false;}
  if(url.origin!=='https://chatgpt.com'||typeof msg.text!=='string'||!msg.text.length||msg.text.length>200000){respond({status:'unavailable',reason:'Unsupported request.'});return false;}
  (async()=>{
    try{
      const {token}=await chrome.storage.local.get('token');
      if(!token){respond({status:'unavailable',reason:'Set the local token in extension options.'});return;}
      const response=await fetch(ENDPOINT,{method:'POST',headers:{'content-type':'application/json',authorization:`Bearer ${token}`},body:JSON.stringify({text:msg.text,origin_host:url.hostname,modality:'text'}),signal:AbortSignal.timeout(15000)});
      if(!response.ok){respond({status:'unavailable',reason:response.status===401?'The local token is invalid.':'The local service could not complete the check.'});return;}
      respond({status:'ok',assertion:await response.json()});
    }catch{respond({status:'unavailable',reason:'The local service is unavailable or timed out.'});}
  })();return true;
});
