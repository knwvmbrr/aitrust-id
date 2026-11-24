'use strict';
// Execute the complete account UI with inert DOM/fetch boundaries; no server or browser.
const assert = require('node:assert/strict');
const {test} = require('node:test');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const {randomUUID} = require('node:crypto');
const source = fs.readFileSync(path.join(__dirname, '../site/account/app.js'), 'utf8');

class Element {
  constructor() { this.children=[]; this.hidden=false; this.checked=false; this.files=[]; this.listeners=new Map(); this.textContent=''; this._value=''; }
  get value() { return this._value; }
  set value(value) { this._value=value; if(value==='') this.files=[]; }
  addEventListener(type, callback) { if(!this.listeners.has(type)) this.listeners.set(type, []); this.listeners.get(type).push(callback); }
  setAttribute() {}
  replaceChildren(...children) { this.children=children; }
  append(...children) { this.children.push(...children); }
  fire(type) { for(const callback of this.listeners.get(type)||[]) callback({preventDefault(){}}); }
}
function privateItem(owner) {
  return {tag:'PS',state:'FINDING',received_at:1,source_label:'Imported summary',explanation:owner+' private record',event_id:owner+'-event'};
}
async function fixture() {
  const nodes=new Map(), calls=[];
  const state={owner:'a',historyFailure:false,sessionFailure:false,marker:'a',next:'old-cursor'};
  const get=id=>{ if(!nodes.has(id)) nodes.set(id,new Element()); return nodes.get(id); };
  const document={getElementById:get,querySelectorAll:()=>[...nodes.values()],createElement:()=>new Element(),documentElement:{dataset:{}}};
  const context=vm.createContext({document,window:{matchMedia:()=>({matches:false})},localStorage:{getItem:()=>null},setTimeout,clearTimeout,AbortController,Date,TextDecoder,crypto:{randomUUID},
    fetch:async(url, options)=>{
      assert.equal(typeof url,'string'); assert(url.startsWith('/v1/account/'));
      assert(calls.length<64, 'bounded inert requests'); calls.push({url,owner:state.owner,method:options.method,binding:options.headers['X-CSRF-Token']});
      let value, ok=true;
      if(url==='/v1/account/session') {
        if(state.sessionFailure) {value={reason:'storage_unavailable'};ok=false;}
        else value={authenticated:true,account:{id:state.owner,username:state.owner},history_enabled:true,csrf_token:'0'.repeat(64)};
      } else if(url==='/v1/account/entitlements') value={state:'ACTIVE',valid_until:2_000_000_000};
      else if(url.startsWith('/v1/account/history')) {
        if(state.historyFailure) {value={reason:'storage_unavailable'};ok=false;}
        else {
          const all=state.items || [privateItem(state.marker)];
          const filter=new URL(url,'https://review.invalid').searchParams.get('state');
          const matching=filter?all.filter(item=>item.state===filter):all;
          value={items:matching,next:state.next,total_entries:all.length,matching_entries:matching.length};
        }
      } else assert.fail('unexpected endpoint');
      return {ok,headers:{get:()=> 'application/json'},json:async()=>value};
    }});
  const settle=async()=>{for(let attempt=0;attempt<32;attempt++){await new Promise(resolve=>setImmediate(resolve));if(vm.runInContext('busy',context)===false)return;}assert.fail('UI action did not settle');};
  vm.runInContext(source,context,{timeout:1000}); await settle();
  assert.equal(get('history-list').children.length,1);
  return {state,get,calls,context,settle,refresh:async()=>{get('refresh').fire('click');await settle();}};
}
function rendered(element) { return element.textContent+' '+element.children.map(rendered).join(' '); }

test('new principal history failure cannot render the previous owner record',async()=>{
  const f=await fixture(); assert(rendered(f.get('history-list')).includes('a private record'));
  f.state.owner='b'; f.state.historyFailure=true; await f.refresh();
  assert.equal(f.get('welcome').textContent,'Hi, b.');
  assert.equal(f.get('history-list').children.length,0);
  assert.equal(f.get('more').hidden,true);
  assert.equal(f.get('empty').hidden,true);
  assert.equal(f.get('history-error').hidden,false);
  assert.equal(f.get('history-retry').hidden,false);
  assert(!rendered(f.get('history-list')).includes('a private record'));
  assert(f.get('notice').textContent.includes('storage'));
});

test('a session fetch failure hides and clears the previously authenticated private view',async()=>{
  const f=await fixture(); f.state.sessionFailure=true; await f.refresh();
  assert.equal(f.get('signed-in').hidden,true);
  assert.equal(f.get('auth').hidden,true);
  assert.equal(f.get('history-list').children.length,0);
  assert.equal(f.get('welcome').textContent,'');
  assert.equal(f.get('access').textContent,'');
  assert.equal(f.get('save-summary').disabled,true);
});

test('refresh discards prior import, cursor, preview, consent and confirmation secrets',async()=>{
  const f=await fixture();
  const summary={format:'ai-trust-id-share-summary/v1',tag:'PS',state:'FINDING',method_sha256:'ee1cc1e11b68de9c6971714232b505b97e4a9f32e216d544217fbebf04779631',stage:'development_preview',independently_validated:false,training_label:null,text_included:false,subject_identifier_included:false,evidence_positions_included:false,detail_reference:'https://aitrustid.com/tags/ps/'};
  const bytes=Buffer.from(JSON.stringify(summary));
  f.get('summary-file').files=[{size:bytes.length,arrayBuffer:async()=>bytes}];
  f.get('summary-file')._value='inert-summary.json';f.get('summary-file').fire('change');await f.settle();
  assert.equal(f.get('save-summary').disabled,false);
  f.get('confirm-password').value='public synthetic confirmation';
  assert.equal(f.get('more').hidden,false);
  f.state.sessionFailure=true;await f.refresh();
  assert.equal(f.get('summary-file').value,'');assert.equal(f.get('summary-file').files.length,0);
  assert.equal(f.get('confirm-password').value,'');assert.equal(f.get('history-enabled').checked,false);
  assert.equal(f.get('more').hidden,true);assert.equal(f.get('save-summary').disabled,true);
  assert(!f.get('import-preview').textContent.includes('Take a closer look'));
  assert.equal(vm.runInContext('pendingRecord === null && next === null && session === null && entitlement === null',f.context),true);
});

test('successful same-owner refresh renders fresh results and pagination once',async()=>{
  const f=await fixture();f.state.marker='a refreshed';f.state.next=null;await f.refresh();
  assert.equal(f.get('signed-in').hidden,false);assert.equal(f.get('welcome').textContent,'Hi, a.');
  assert.equal(f.get('history-list').children.length,1);
  assert(rendered(f.get('history-list')).includes('a refreshed private record'));
  assert(!rendered(f.get('history-list')).includes('a private record'));
  assert.equal(f.get('more').hidden,true);assert.equal(f.get('empty').hidden,true);
});

test('state filter starts a fresh page and keeps complete-history export separate',async()=>{
  const f=await fixture();f.state.items=[privateItem('finding'),{...privateItem('clear'),state:'NO_FINDING'}];f.state.next=null;
  f.get('history-filter').value='NO_FINDING';f.get('history-filter').fire('change');await f.settle();
  assert.equal(f.get('history-list').children.length,1);
  assert(rendered(f.get('history-list')).includes('clear private record'));
  assert(!rendered(f.get('history-list')).includes('a private record'));
  assert(f.calls.at(-1).url.includes('state=NO_FINDING'));
  assert(!f.calls.at(-1).url.includes('after='));
  assert.equal(f.get('history-count').textContent,'1 of 1 matching summaries · 2 saved overall');
  f.get('history-filter').value='UNAVAILABLE';f.get('history-filter').fire('change');await f.settle();
  assert.equal(f.get('history-list').children.length,0);
  assert(f.get('empty').textContent.includes('All results'));
});

test('failed filtered history clears stale rows and the visible retry recovers',async()=>{
  const f=await fixture();f.state.historyFailure=true;
  f.get('history-filter').value='FINDING';f.get('history-filter').fire('change');await f.settle();
  assert.equal(f.get('history-list').children.length,0);assert.equal(f.get('more').hidden,true);
  assert.equal(f.get('history-error').hidden,false);assert.equal(f.get('history-retry').hidden,false);
  assert.equal(f.get('history-count').textContent,'History unavailable');
  f.state.historyFailure=false;f.state.next=null;f.get('history-retry').fire('click');await f.settle();
  assert.equal(f.get('history-error').hidden,true);assert.equal(f.get('history-retry').hidden,true);
  assert.equal(f.get('history-list').children.length,1);
});

test('authenticated browser reads carry the current session binding',async()=>{
  const f=await fixture();
  for(const call of f.calls.filter(item=>item.url!=='/v1/account/session')) assert.equal(call.binding,'0'.repeat(64));
});
