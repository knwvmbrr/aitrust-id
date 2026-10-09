// Bind a result to response identity, captured text, page, and request revision.
(() => {
  const adapter=globalThis.AITrustAdapter,ui=globalThis.AITrust;
  if(!adapter||!ui)return;
  const states=new WeakMap(),tracked=new Set(),MAX=200000;let scanTimer;
  function valid(a){
    return a&&typeof a.assertion_id==='string'&&a.subject&&Number.isInteger(a.subject.char_len)&&Array.isArray(a.tags)&&Array.isArray(a.abstentions)&&a.evaluator&&typeof a.evaluator.calibration_id==='string'&&a.tags.every(t=>['PS','PII_REDACTED'].includes(t.code)&&Array.isArray(t.signals)&&t.signals.every(s=>typeof s.id==='string'&&Number.isFinite(s.score)&&(!s.spans||s.spans.every(p=>Array.isArray(p)&&p.length===2&&p.every(Number.isInteger)&&p[0]>=0&&p[1]>p[0]&&p[1]<=a.subject.char_len))));
  }
  async function check(host,state){
    const identity=adapter.responseId(host),text=adapter.text(host),page=location.href;
    if(!identity){ui.update(host,'UNSUPPORTED',null,'A stable assistant response identity is unavailable.');return;}
    if(!text)return;
    if(text.length>MAX){ui.update(host,'UNSUPPORTED',null,'Response exceeds the supported size.');return;}
    if(adapter.streaming(host)){ui.update(host,'PENDING',null,'Waiting for this response to finish.');return;}
    const request=++state.request;state.evaluated=text;
    ui.update(host,'PENDING');
    const current=()=>host.isConnected&&request===state.request&&location.href===page&&adapter.responseId(host)===identity&&adapter.text(host)===text&&adapter.responses().includes(host)&&!adapter.streaming(host);
    try{
      const result=await chrome.runtime.sendMessage({type:'evaluate',text,origin_host:location.hostname});
      if(!current())return;
      if(!result||result.status!=='ok'||!valid(result.assertion)){ui.update(host,'UNAVAILABLE',null,result?.reason||'Check the local service and token settings.');return;}
      const a=result.assertion;
      ui.update(host,a.tags.some(t=>t.code==='PS')?'FINDING':a.abstentions.length?'UNCERTAIN':'NO_FINDING',a,'',text);
    }catch{if(current())ui.update(host,'UNAVAILABLE',null,'Check the local service and token settings.');}
  }
  function scan(){
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
        Object.assign(state,{text,identity,page,streaming,evaluated:null});state.request++;clearTimeout(state.timer);ui.update(host,'PENDING');
      }
      if(!identity){ui.update(host,'UNSUPPORTED',null,'A stable assistant response identity is unavailable.');continue;}
      if(streaming){ui.update(host,'PENDING',null,'Waiting for this response to finish.');continue;}
      if(text&&state.evaluated!==text){clearTimeout(state.timer);state.timer=setTimeout(()=>check(host,state),600);}
    }
  }
  function queue(){clearTimeout(scanTimer);scanTimer=setTimeout(scan,50);}
  const observer=new MutationObserver(records=>{
    if(records.every(r=>{const e=r.target.nodeType===1?r.target:r.target.parentElement;return e?.closest('.aitrust-mount');}))return;
    queue();
  });
  observer.observe(document.body,{childList:true,subtree:true,characterData:true,attributes:true,attributeFilter:['data-testid','aria-label','data-talvt-turn-state','data-chatgpt-selection-message-id','data-message-id','data-dil-source-message-id','data-dil-message-id','data-markdown-text-style','data-message-author-role','hidden','aria-hidden']});
  addEventListener('popstate',queue);addEventListener('hashchange',queue);scan();
})();
