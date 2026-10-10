// Compact, code-only tags. Brief explanations with explicit local record export.
// Dynamic evidence is always inserted as text in the isolated content-script world.
(() => {
  const roots = new WeakMap();
  const words = {
    PENDING: 'Checking this response locally…',
    NO_FINDING: 'No supported command pattern found. This is not a safety clearance.',
    UNCERTAIN: 'The available evidence was insufficient for a finding.',
    UNSUPPORTED: 'This response cannot be checked by the current implementation.',
    UNAVAILABLE: 'A valid local evaluation could not be obtained.',
    FINDING: 'Command risk pattern detected. Read the evidence before acting.'
  };
  const markers = {PENDING:'…',NO_FINDING:'ID',UNCERTAIN:'?',UNSUPPORTED:'—',UNAVAILABLE:'!'};
  const displayCode=code=>code==='PII_REDACTED'?'PII':code;
  function record(item,code) {
    const a=item.assertion;if(!a)return null;
    const pick=(value,keys)=>Object.fromEntries(keys.filter(key=>value?.[key]!==undefined).map(key=>[key,value[key]]));
    return {format:'ai-trust-id-result-export/v1',exported_at:new Date().toISOString(),
      result_state:item.state,selected_tag:code||null,assertion_id:a.assertion_id,
      subject:pick(a.subject,['modality','sha256','char_len','origin_host','captured_at','normalization']),
      evaluator:{...pick(a.evaluator,['calibration_id']),models:(a.evaluator.models||[]).map(model=>pick(model,['name','revision','sha256']))},
      tags:a.tags.filter(tag=>!code||tag.code===code).map(tag=>({...pick(tag,['code','confidence','floor']),signals:tag.signals.map(signal=>pick(signal,['id','score','spans']))})),
      redaction_summary:a.tags.filter(tag=>tag.code==='PII_REDACTED').flatMap(tag=>tag.signals.filter(signal=>signal.id==='presidio.entity.v1').map(signal=>({count:Number.isInteger(signal.detail?.count)?signal.detail.count:null,entities:(signal.detail?.entities||[]).filter(entity=>typeof entity==='string'&&/^[A-Z_]{1,64}$/.test(entity))}))),
      abstentions:a.abstentions.map(value=>pick(value,['code','reason','floor'])),
      training_label:null,review_status:'unreviewed_detector_output',delivery:'local_download_only'};
  }
  let live, capture, captureMessage='';
  function announce(text) {
    if (!live) {
      live=document.createElement('div');live.className='aitrust-mount';
      live.setAttribute('role','status');live.setAttribute('aria-live','polite');
      Object.assign(live.style,{position:'absolute',width:'1px',height:'1px',overflow:'hidden',clipPath:'inset(50%)'});
      document.body.append(live);
    }
    if(live.textContent!==text)live.textContent=text;
  }
  function captureStatus(message) {
    if(!message){if(capture)unmount(document.body);capture=null;captureMessage='';return;}
    if(!capture){
      capture=mount(document.body,()=>location.reload());
      Object.assign(capture.style,{position:'fixed',right:'max(12px, env(safe-area-inset-right))',bottom:'max(12px, env(safe-area-inset-bottom))',zIndex:'20'});
    }
    if(message!==captureMessage){captureMessage=message;update(document.body,'UNSUPPORTED',null,message);}
  }
  function evidence(item, code) {
    const {root,assertion,reason,state}=item;
    const container=root.querySelector('.evidence');container.replaceChildren();
    root.querySelector('h2').textContent=code?displayCode(code):'AI Trust ID';
    function paragraph(text){const p=document.createElement('p');p.className='brief';p.textContent=text;container.append(p);}
    item.selectedCode=code;
    root.querySelector('.export').hidden=!assertion;
    root.querySelector('.export-note').hidden=!assertion;
    if(code==='PS'){
      const encoded=assertion?.tags.filter(tag=>tag.code===code).some(tag=>tag.signals.some(signal=>signal.id==='sig.obfuscated_payload.v2'));
      paragraph(encoded?'This command runs encoded code. Inspect what it decodes to before running it.':'This command downloads code and runs it. Inspect the code before running it.');
      paragraph('A command-risk warning, not a scam verdict.');
    }else if(code==='PII_REDACTED'){
      paragraph('Detected entity values were redacted before evaluation.');
      paragraph('Public information can also be redacted. Other sensitive information may remain.');
    }else{
      paragraph(code?'A finding was recorded for this tag. Review its claim and limits in the site catalogue.':words[state]||words.UNAVAILABLE);
      if(reason)paragraph(reason);
    }
    const labels={'sig.piped_installer.v3':'Download piped to a shell','sig.remote_command_substitution.v3':'Downloaded output used in an execution command','sig.remote_process_substitution.v3':'Downloaded code handed to an interpreter','sig.remote_backtick_substitution.v2':'Downloaded output substituted into a command','sig.obfuscated_payload.v2':'Encoded content passed to eval or exec','presidio.entity.v1':'Detected entity redaction'};
    const signals=(assertion?.tags||[]).filter(tag=>tag.code===code).flatMap(tag=>tag.signals||[]);
    if(signals.length){
      const detail=document.createElement('details'),summary=document.createElement('summary');summary.textContent='Matched locations';detail.append(summary);
      const explanation=document.createElement('p');explanation.textContent='Character positions refer to the evaluated, redacted text. They can differ from this answer.';detail.append(explanation);
      const list=document.createElement('ul');let total=0,shown=0;
      for(const signal of signals){
        const spans=Array.isArray(signal.spans)?signal.spans:[];
        const valid=spans.filter(span=>Array.isArray(span)&&span.length===2&&span.every(Number.isSafeInteger)&&span[0]>=0&&span[1]>span[0]&&span[1]<=assertion.subject.char_len);
        const label=labels[signal.id]||'Other supporting observation';
        const rows=valid.length?valid:[null];total+=rows.length;
        for(const span of rows){if(shown>=20)continue;const li=document.createElement('li');li.textContent=label+(span?': characters '+span[0]+'–'+span[1]+' (end excluded).':': no character positions provided.');list.append(li);shown++;}
      }
      detail.append(list);
      if(total>shown){const more=document.createElement('p');more.textContent='Showing '+shown+' of '+total+' observations. Download the record for all positions.';detail.append(more);}
      container.append(detail);
    }
  }
  function open(item, button) {
    evidence(item,button.dataset.code||null);
    item.root.querySelectorAll('.tag').forEach(tag=>tag.setAttribute('aria-expanded',String(tag===button)));
    item.root.querySelector('.panel').showModal();
  }
  function mount(host, check) {
    const holder=document.createElement('span');holder.className='aitrust-mount';
    const root=holder.attachShadow({mode:'closed'});
    root.innerHTML=`<style>
      :host{all:initial;display:block;width:fit-content;max-width:100%;color:#171717;color-scheme:light dark}
      *{box-sizing:border-box} .wrap{display:flex;flex-wrap:wrap;align-items:center;gap:4px;max-width:100%;margin:4px 0;font:12px/1.4 system-ui,sans-serif}
      button{font:inherit;cursor:pointer;color:inherit} .tag{min-width:28px;min-height:24px;padding:2px 6px;border:1px solid #a3a3a3;border-radius:4px;background:#fff;font:600 11px/18px ui-monospace,monospace}
      .tag:hover{border-color:currentColor} button:focus-visible{outline:2px solid currentColor;outline-offset:3px}
      .sr-only{position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;clip-path:inset(50%);white-space:nowrap}
      .panel{width:min(24rem,calc(100vw - 32px));max-height:calc(100dvh - 32px);margin:auto;padding:16px;border:1px solid #a3a3a3;border-radius:8px;background:#fff;color:#171717;overflow:auto;overflow-wrap:anywhere;font:14px/1.5 system-ui,sans-serif}
      .panel::backdrop{background:rgb(0 0 0 / .25)} header{display:flex;align-items:center;justify-content:space-between;gap:12px}
      h2{margin:0;font:600 16px/1.5 ui-monospace,monospace;text-wrap:balance} p{margin:12px 0;text-wrap:pretty;font-variant-numeric:tabular-nums}
      summary{cursor:pointer;min-height:32px;padding:6px 0;font-weight:600}summary:focus-visible{outline:2px solid currentColor;outline-offset:3px}ul{padding-left:20px}li{margin:8px 0}.export-note{font-size:12px} .close,.check,.export{min-height:32px;padding:4px 10px;border:1px solid #a3a3a3;border-radius:4px;background:transparent} footer{display:flex;flex-wrap:wrap;gap:8px;margin-top:16px}
      [hidden]{display:none!important}
      @media(prefers-color-scheme:dark){:host{color:#e5e5e5}.tag,.panel{background:#171717;color:#e5e5e5;border-color:#737373}}
      @media(forced-colors:active){.tag,.panel,.close,.check,.export{background:Canvas;color:CanvasText;border-color:CanvasText}button:focus-visible{outline-color:Highlight}}
    </style><span class="wrap" role="group" aria-label="AI Trust ID tags"><span class="status sr-only"></span></span><dialog class="panel"><header><h2>AI Trust ID</h2><form method="dialog"><button class="close" autofocus>Close</button></form></header><div class="evidence"></div><p class="export-note" hidden>Records include fingerprints and positions that can link or reveal information. Review before sharing.</p><footer><button class="check" type="button">Recheck locally</button><button class="export" type="button" hidden>Download record</button></footer></dialog>`;
    const panel=root.querySelector('.panel'),title=root.querySelector('h2');
    panel.id='aitrust-record-'+crypto.randomUUID();title.id=panel.id+'-title';panel.setAttribute('aria-labelledby',title.id);
    const item={holder,root,state:'PENDING',assertion:null,reason:'',source:''};
    root.querySelector('.wrap').addEventListener('click',event=>{
      const button=event.target.closest('.tag');if(button)open(item,button);
    });
    panel.addEventListener('close',()=>root.querySelectorAll('.tag').forEach(button=>button.setAttribute('aria-expanded','false')));
    // Native dialog handles Escape, focus containment, and focus restoration.
    panel.addEventListener('click',event=>{
      if(event.target!==panel)return;
      const box=panel.getBoundingClientRect();
      if(event.clientX<box.left||event.clientX>box.right||event.clientY<box.top||event.clientY>box.bottom)panel.close();
    });
    root.querySelector('.check').addEventListener('click',check);
    root.querySelector('.export').addEventListener('click',()=>{
      const value=record(item,item.selectedCode);if(!value)return;
      const url=URL.createObjectURL(new Blob([JSON.stringify(value,null,2)],{type:'application/json'}));
      const link=document.createElement('a');link.className='aitrust-mount';link.href=url;link.download='ai-trust-id-'+(value.selected_tag||'result')+'.json';link.hidden=true;
      document.body.append(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);
    });
    host.append(holder);roots.set(host,item);update(host,'PENDING');return holder;
  }
  function update(host,state,assertion=null,reason='',source='') {
    const item=roots.get(host);if(!item)return;
    const {root}=item,panel=root.querySelector('.panel');if(panel.open)panel.close();
    Object.assign(item,{state,assertion,reason,source});
    const text=words[state]||words.UNAVAILABLE;
    root.querySelector('.status').textContent=text+(reason?' '+reason:'');
    root.querySelector('.wrap').setAttribute('aria-busy',String(state==='PENDING'));
    const tags=[...new Map((assertion?.tags||[]).map(tag=>[tag.code,tag])).values()];
    const codes=tags.length?tags.map(tag=>tag.code):[''];
    const wrap=root.querySelector('.wrap'),buttons=new Map([...wrap.querySelectorAll('.tag')].map(button=>[button.dataset.code,button]));
    for(const [code,button] of buttons)if(!codes.includes(code))button.remove();
    codes.forEach((code,index)=>{
      let button=buttons.get(code);
      if(!button){button=document.createElement('button');button.type='button';button.setAttribute('aria-haspopup','dialog');button.setAttribute('aria-controls',panel.id);button.setAttribute('aria-expanded','false');}
      button.className='tag '+(index===0?'details':'secondary');
      button.dataset.code=code;
      button.dataset.state=state;
      button.textContent=code?displayCode(code):(markers[state]||'!');
      const description=code?(code==='PS'?'PS: supported command-risk finding.':code==='PII_REDACTED'?'PII: detected entity values redacted.':displayCode(code)+': recorded finding.'):'AI Trust ID check status.';
      const label=description+' '+text+(reason?' '+reason:'')+' Open details.';
      button.setAttribute('aria-label',label);button.title=label;
      wrap.append(button);
    });
    announce('AI Trust ID. '+text);
  }
  function unmount(host) {
    const item=roots.get(host);if(!item)return;
    const panel=item.root.querySelector('.panel');if(panel.open)panel.close();
    item.holder.remove();roots.delete(host);
  }
  globalThis.AITrust={mount,update,unmount,captureStatus};
})();
