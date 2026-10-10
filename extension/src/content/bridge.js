// Bind a result to response identity, captured text, page, and request revision.
(() => {
  const adapter=globalThis.AITrustAdapter,ui=globalThis.AITrust,contract=globalThis.AITrustContract;
  if(!adapter||!ui||!contract)return;
  const states=new WeakMap(),tracked=new Set();let scanTimer,enabled=false,consentRevision=0;
  async function check(host,state){
    if(!enabled)return;
    clearTimeout(state.timer);state.timer=null;
    const identity=adapter.responseId(host),text=adapter.text(host),page=location.href;
    if(!identity){ui.update(host,'UNSUPPORTED',null,'A stable assistant response identity is unavailable.');return;}
    if(!text)return;
    if(!contract.scalarText(text)){ui.update(host,'UNSUPPORTED',null,'Response exceeds the supported size or contains invalid text.');return;}
    if(adapter.streaming(host)){ui.update(host,'PENDING',null,'Waiting for this response to finish.');return;}
    const request=++state.request;state.evaluated=text;
    ui.update(host,'PENDING');
    const current=()=>enabled&&host.isConnected&&request===state.request&&location.href===page&&adapter.responseId(host)===identity&&adapter.text(host)===text&&adapter.responses().includes(host)&&!adapter.streaming(host);
    try{
      const result=await chrome.runtime.sendMessage({type:'evaluate',text,origin_host:location.hostname});
      if(!current())return;
      if(!result||result.status!=='ok'){ui.update(host,result?.status==='unsupported'?'UNSUPPORTED':'UNAVAILABLE',null,result?.reason||'Check the local service and token settings.');return;}
      const inspected=contract.inspect(result.assertion);
      if(inspected.status!=='accepted'){ui.update(host,inspected.status==='unsupported'?'UNSUPPORTED':'UNAVAILABLE',null,inspected.reason);return;}
      const a=result.assertion;
      ui.update(host,inspected.result_state,a,'',text);
    }catch{if(current())ui.update(host,'UNAVAILABLE',null,'Check the local service and token settings.');}
  }
  function scan(){
    if(!enabled){ui.captureStatus('Checks are paused. Open settings to enable assistant-response checks on ChatGPT.',()=>chrome.runtime.sendMessage({type:'open_settings'}),'Open settings');return;}
    const hosts=adapter.responses();
    for(const host of tracked){
      if(!hosts.includes(host)){
        const state=states.get(host);state.request++;clearTimeout(state.timer);
        ui.unmount(host);states.delete(host);tracked.delete(host);
      }
    }
    ui.captureStatus(hosts.length?'':'No supported assistant response is available to check. Nothing on this page has been evaluated.');
    for(const host of hosts){
      let state=states.get(host);
      if(!state){state={request:0,text:'',identity:null,page:null,evaluated:null,timer:null,streaming:false};states.set(host,state);tracked.add(host);ui.mount(host,()=>check(host,state));}
      const text=adapter.text(host),identity=adapter.responseId(host),page=location.href,streaming=adapter.streaming(host);
      if(text!==state.text||identity!==state.identity||page!==state.page||streaming!==state.streaming){
        Object.assign(state,{text,identity,page,streaming,evaluated:null});state.request++;clearTimeout(state.timer);state.timer=null;ui.update(host,'PENDING');
      }
      if(!identity){ui.update(host,'UNSUPPORTED',null,'A stable assistant response identity is unavailable.');continue;}
      if(streaming){ui.update(host,'PENDING',null,'Waiting for this response to finish.');continue;}
      if(text&&state.evaluated!==text&&state.timer===null){state.timer=setTimeout(()=>{state.timer=null;check(host,state);},600);}
    }
  }
  function queue(){clearTimeout(scanTimer);scanTimer=setTimeout(scan,50);}
  const observer=new MutationObserver(records=>{
    if(records.every(r=>{const e=r.target.nodeType===1?r.target:r.target.parentElement;return e?.closest('.aitrust-mount');}))return;
    queue();
  });
  observer.observe(document.body,{childList:true,subtree:true,characterData:true,attributes:true,attributeFilter:['data-testid','aria-label','data-talvt-turn-state','data-chatgpt-selection-message-id','data-message-id','data-dil-source-message-id','data-dil-message-id','data-markdown-text-style','data-message-author-role','hidden','aria-hidden']});
  function applyConsent(value){
    enabled=value===true;clearTimeout(scanTimer);
    for(const host of tracked){const state=states.get(host);state.request++;clearTimeout(state.timer);ui.unmount(host);states.delete(host);}tracked.clear();ui.captureStatus('');scan();
  }
  chrome.storage.onChanged.addListener((changes,area)=>{
    if(area!=='local')return;
    if(changes.checks_enabled){consentRevision++;applyConsent(changes.checks_enabled.newValue);}
    else if(changes.token){consentRevision++;applyConsent(enabled);}
  });
  const initialRevision=consentRevision;
  chrome.storage.local.get('checks_enabled').then(value=>{if(initialRevision===consentRevision)applyConsent(value.checks_enabled);}).catch(()=>{if(initialRevision===consentRevision)applyConsent(false);});
  addEventListener('popstate',queue);addEventListener('hashchange',queue);scan();
})();
