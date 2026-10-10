const input=document.querySelector('#token'),status=document.querySelector('#status'),consent=document.querySelector('#checks-enabled'),saved=document.querySelector('#saved-token');
let ready=false,revision=0;
function validToken(value){return typeof value==='string'&&value!=='change-me'&&value.length>=16&&value.length<=4096&&/^[\x21-\x7e]+$/.test(value);}
async function refresh(){
 const current=++revision;consent.disabled=true;
 try{const value=await chrome.storage.local.get(['token','checks_enabled']);if(current!==revision)return;
  consent.checked=value.checks_enabled===true;saved.textContent=validToken(value.token)?'A local token is saved.':'No local token is saved.';ready=true;consent.disabled=false;
 }catch{if(current===revision){ready=false;consent.checked=false;status.textContent='Settings could not be read. Checks remain unavailable.';}}
}
chrome.storage.onChanged.addListener((changes,area)=>{if(area==='local'&&(changes.token||changes.checks_enabled))refresh();});
document.querySelector('form').addEventListener('submit',async event=>{
 event.preventDefault();if(!validToken(input.value)){input.setAttribute('aria-invalid','true');status.textContent='Enter a generated token with 16–4096 visible ASCII characters.';return;}
 try{await chrome.storage.local.set({token:input.value});input.value='';input.removeAttribute('aria-invalid');status.textContent='Token saved locally. The check setting stays as you chose it.';await refresh();}catch{status.textContent='Token could not be saved.';}
});
consent.addEventListener('change',async()=>{
 if(!ready)return;const enabled=consent.checked;consent.disabled=true;
 try{await chrome.storage.local.set({checks_enabled:enabled});status.textContent=enabled?'ChatGPT checks enabled. Only assistant responses are checked through your local service.':'Checks paused. Pending checks are cancelled and tags are removed.';await refresh();}
 catch{consent.checked=false;ready=false;status.textContent='The setting could not be saved. Reload settings to check the current state.';}
});
document.querySelector('#clear').addEventListener('click',async()=>{
 try{await chrome.storage.local.remove(['token','checks_enabled']);input.value='';status.textContent='Local token and consent removed. Checks are paused. Server credentials and ChatGPT conversations are unchanged.';await refresh();}catch{status.textContent='Settings could not be reset. Reload settings to check the current state.';}
});
refresh();
