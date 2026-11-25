const $ = id => document.getElementById(id);
const API = '/v1/account';
const METHOD = {name:'rules-only', revision:'context-v6', sha256:'ee1cc1e11b68de9c6971714232b505b97e4a9f32e216d544217fbebf04779631'};
const LABELS = {FINDING:'Take a closer look',NO_FINDING:'No PS pattern found',UNAVAILABLE:'Check unavailable',UNSUPPORTED:'Not supported'};
let session, entitlement, signup = true, busy = false, pendingRecord = null, next = null;

function announce(message) { $('notice').textContent = message; }
function date(value) { return new Date(value * 1000).toLocaleString(undefined,{dateStyle:'medium',timeStyle:'short'}); }
async function request(path, method='GET', data) {
  const controller = new AbortController(); const timer = setTimeout(() => controller.abort(), 10000);
  try {
    const headers = {'Accept':'application/json'};
    if(session?.csrf_token) headers['X-CSRF-Token']=session.csrf_token;
    if (method !== 'GET') { headers['Content-Type']='application/json'; headers['X-CSRF-Token']=session?.csrf_token || ''; }
    const response = await fetch(API+path,{method,headers,credentials:'same-origin',mode:'cors',redirect:'error',referrerPolicy:'no-referrer',cache:'no-store',signal:controller.signal,body:data===undefined?undefined:JSON.stringify(data)});
    const type = response.headers.get('content-type') || '';
    if (!type.includes('application/json')) throw new Error('The account service is unavailable. Your tag checks are separate.');
    const value = await response.json();
    if (!response.ok) {
      const reasons = {authentication_required:'Please sign in or check your username and password.',account_unavailable:'That account could not be created. Try another username.',rate_limited:'Please wait a little before trying again.',history_access_inactive:'History access is required to save a summary.',history_access_unavailable:'History access is temporarily unavailable. You can still export or delete saved history.',history_disabled:'Enable history before saving.',csrf_refused:'Your session changed. Reload before trying again.',history_full:'History is full. Export or delete older summaries before saving more.',history_conflict:'This summary could not be saved again with different details.',busy:'The account store is busy. Please try again shortly.',clock_unavailable:'The service clock needs attention. Your saved data is unchanged.',storage_unavailable:'Account storage is temporarily unavailable.',invalid_request:'Check the details and try again.'};
      throw new Error(reasons[value.reason] || 'That action could not be completed. Your saved data has not been declared deleted.');
    }
    return value;
  } catch (error) {
    if (error.name==='AbortError') throw new Error('The request timed out. Refresh to check what completed before trying again.');
    throw error;
  } finally { clearTimeout(timer); }
}
async function action(work) {
  if (busy) return;
  busy=true; $('main').setAttribute('aria-busy','true'); updateControls();
  try { await work(); } catch (error) { announce(error.message || 'The account service is unavailable.'); }
  finally { busy=false; $('main').setAttribute('aria-busy','false'); updateControls(); }
}
function updateControls() {
  document.querySelectorAll('main button, main input, main select').forEach(element=>{element.disabled=busy;});
  $('save-summary').disabled=busy || !pendingRecord || !session?.history_enabled || entitlement?.state!=='ACTIVE';
  $('import-section').hidden=!session?.authenticated || !session.history_enabled || entitlement?.state!=='ACTIVE';
}
function authMode() {
  $('account-title').textContent=signup?'Create an account':'Sign in';
  $('authenticate').textContent=signup?'Create account':'Sign in';
  $('mode').textContent=signup?'Sign in instead':'Create an account instead';
  $('password').autocomplete=signup?'new-password':'current-password';
}
function resetPrivateView() {
  session=null; entitlement=null; pendingRecord=null; next=null;
  $('signed-in').hidden=true; $('auth').hidden=true;
  $('history-list').replaceChildren(); $('more').hidden=true; $('empty').hidden=false;
  $('history-filter').value=''; $('history-count').textContent=''; $('history-error').hidden=true; $('history-error').textContent=''; $('history-retry').hidden=true;
  $('summary-file').value=''; $('confirm-password').value='';
  $('import-preview').textContent='The file stays on this device until you choose Save summary. Only the tag, result and public method details are sent; original viewing time is unknown.';
  $('welcome').textContent=''; $('access').textContent=''; $('history-enabled').checked=false;
  updateControls();
}
async function loadSession() {
  resetPrivateView();
  session=await request('/session');
  $('auth').hidden=session.authenticated; $('signed-in').hidden=!session.authenticated;
  if (session.authenticated) {
    $('welcome').textContent='Hi, '+session.account.username+'.';
    $('heading').textContent='Your tag history.';
    $('history-enabled').checked=session.history_enabled;
    try { entitlement=await request('/entitlements'); }
    catch { entitlement={state:'UNAVAILABLE'}; }
    $('access').textContent=entitlement.state==='ACTIVE'?'History access is active until '+date(entitlement.valid_until)+'.':entitlement.state==='INACTIVE'?'History access is not active. You can still read, export and delete saved history.':'Access status is unavailable. Reading, export and deletion stay separate.';
    await loadHistory();
  } else { $('heading').textContent='A place for your tag history.'; entitlement=null; }
  updateControls();
}
function item(record) {
  const li=document.createElement('li');
  const title=document.createElement('div');
  const tag=document.createElement('span'); tag.className='tag'; tag.textContent=record.tag;
  const label=document.createElement('span'); label.className='entry-title'; label.textContent=LABELS[record.state] || 'Result unavailable';
  title.append(tag,label);
  const when=document.createElement('span'); when.className='entry-time'; when.textContent='Saved '+date(record.received_at)+' · '+record.source_label;
  const note=document.createElement('p'); note.className='entry-note'; note.textContent=record.explanation;
  const remove=document.createElement('button'); remove.type='button'; remove.className='quiet'; remove.textContent='Delete summary';
  remove.addEventListener('click',()=>action(async()=>{await request('/history/'+encodeURIComponent(record.event_id),'DELETE'); await loadHistory(); announce('Summary deleted from active history.');}));
  const details=document.createElement('details'); details.className='method-details';
  const summary=document.createElement('summary'); summary.textContent='About this saved result';
  const source=document.createElement('p'); source.textContent=(record.adapter==='summary-import'?'Imported summary. Original viewing time and location are unknown.':'Client-declared record. Its viewing time and location are not independently verified.')+' The original text and individual evidence were not saved.';
  details.append(summary,source);
  if(record.method){
    const method=document.createElement('p'); method.textContent='Method: '+record.method.name+' · '+record.method.revision;
    const identity=document.createElement('code'); identity.textContent=record.method.sha256;
    const identityLabel=document.createElement('p'); identityLabel.textContent='Public method identifier: '; identityLabel.append(identity);
    details.append(method,identityLabel);
  }
  li.append(title,when,note,details,remove); return li;
}
async function loadHistory(append=false) {
  const selected=$('history-filter').value;
  $('history-error').hidden=true; $('history-retry').hidden=true;
  if(!append){$('history-list').replaceChildren(); next=null; $('more').hidden=true; $('empty').hidden=true; $('history-count').textContent='Loading your history…';}
  try {
    const value=await request('/history?limit=50'+(selected?'&state='+encodeURIComponent(selected):'')+(append&&next?'&after='+encodeURIComponent(next):''));
    for (const record of value.items) $('history-list').append(item(record));
    next=value.next; $('more').hidden=!next;
    const shown=$('history-list').children.length;
    $('history-count').textContent=shown+' of '+value.matching_entries+' matching summaries · '+value.total_entries+' saved overall';
    $('empty').hidden=shown>0;
    $('empty').textContent=selected?'No saved summaries match this result. Choose All results to see the rest.':'No saved summaries yet. You can keep checking for free.';
  } catch(error) {
    $('history-list').replaceChildren(); next=null; $('more').hidden=true; $('empty').hidden=true;
    $('history-count').textContent='History unavailable'; $('history-error').textContent=error.message || 'Your saved history could not be loaded.';
    $('history-error').hidden=false; $('history-retry').hidden=false; throw error;
  }
}
function parseSummary(value) {
  const keys=['format','tag','state','method_sha256','stage','independently_validated','training_label','text_included','subject_identifier_included','evidence_positions_included','detail_reference'];
  if (!value || typeof value!=='object' || Array.isArray(value) || Object.keys(value).length!==keys.length || !keys.every(k=>Object.hasOwn(value,k)) ||
      value.format!=='ai-trust-id-share-summary/v1' || value.tag!=='PS' || !['FINDING','NO_FINDING'].includes(value.state) ||
      value.method_sha256!==METHOD.sha256 || value.stage!=='development_preview' || value.independently_validated!==false ||
      value.training_label!==null || value.text_included!==false || value.subject_identifier_included!==false ||
      value.evidence_positions_included!==false || value.detail_reference!=='https://aitrustid.com/tags/ps/') {
    throw new Error('Choose a current PS summary, not a detailed record. No file data was sent.');
  }
  return {event_id:crypto.randomUUID(),displayed_at:Math.floor(Date.now()/1000),adapter:'summary-import',tag:'PS',state:value.state,method:{...METHOD}};
}
$('mode').addEventListener('click',()=>{if(busy)return; signup=!signup;authMode();});
$('auth-form').addEventListener('submit',event=>{event.preventDefault();action(async()=>{
  const password=$('password').value;
  await request(signup?'/signup':'/sessions','POST',{username:$('username').value,password});
  $('password').value='';await loadSession();$('heading').focus();announce(signup?'Your account is ready. History starts off.':'You’re signed in.');
});});
$('logout').addEventListener('click',()=>action(async()=>{await request('/session','DELETE');pendingRecord=null;$('summary-file').value='';await loadSession();announce('You’re signed out.');}));
$('preference-form').addEventListener('submit',event=>{event.preventDefault();action(async()=>{
  const enabled=$('history-enabled').checked;
  await request('/history','POST',enabled?{operation:'enable',acknowledge_metadata:true}:{operation:'disable'});
  await loadSession();announce(enabled?'History is enabled. Choose each summary you want to save.':'Saving is off. Existing history remains available to you.');
});});
$('summary-file').addEventListener('change',()=>action(async()=>{
  pendingRecord=null;const file=$('summary-file').files[0];if(!file)return;
  if(file.size>16384)throw new Error('This file is too large for a PS summary. Nothing was sent.');
  let value;
  try { value=JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(await file.arrayBuffer())); }
  catch { throw new Error('Choose a valid PS summary JSON file. Nothing was sent.'); }
  pendingRecord=parseSummary(value);
  $('import-preview').textContent='PS · '+LABELS[pendingRecord.state]+'. Save the result and public method only. Original viewing time is unknown; this records import time.';
}));
$('save-summary').addEventListener('click',()=>action(async()=>{
  if(!pendingRecord)return;await request('/history','POST',{operation:'append',record:pendingRecord});pendingRecord=null;$('summary-file').value='';await loadHistory();announce('Summary saved to your private history.');
}));
$('refresh').addEventListener('click',()=>action(async()=>{await loadSession();announce('History refreshed.');}));
$('more').addEventListener('click',()=>action(()=>loadHistory(true)));
$('history-filter').addEventListener('change',()=>action(()=>loadHistory()));
$('history-retry').addEventListener('click',()=>action(()=>loadHistory()));
$('export').addEventListener('click',()=>action(async()=>{
  const value=await request('/history/export');const url=URL.createObjectURL(new Blob([JSON.stringify(value,null,2)],{type:'application/json'}));
  const a=document.createElement('a');a.href=url;a.download='ai-trust-id-personal-history.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);announce('History export downloaded. Keep this private.');
}));
$('delete-history').addEventListener('click',()=>action(async()=>{
  if(!window.confirm('Delete all saved history from this account? Existing downloads and backups are separate.'))return;
  await request('/history','DELETE');await loadHistory();announce('Active history deleted. Existing downloads and backups are separate.');
}));
$('delete-account-form').addEventListener('submit',event=>{event.preventDefault();action(async()=>{
  if(!window.confirm('Delete your account and active history?'))return;
  const value=await request('','DELETE',{password:$('confirm-password').value});$('confirm-password').value='';pendingRecord=null;await loadSession();
  announce(value.cleanup_pending?'Active account data deleted. Access-ledger cleanup is pending.':'Account and active history deleted. Existing downloads and backups are separate.');
});});
let preference=null;try{preference=localStorage.getItem('aitrust-account-appearance');}catch{}
$('theme').checked=preference?preference==='dark':window.matchMedia('(prefers-color-scheme: dark)').matches;
function appearance(){document.documentElement.dataset.theme=$('theme').checked?'dark':'light';}
appearance();$('theme').addEventListener('change',()=>{appearance();try{localStorage.setItem('aitrust-account-appearance',$('theme').checked?'dark':'light');}catch{}});
authMode();action(async()=>{await loadSession();announce(session.authenticated?'Your private history is ready.':'Create an account or sign in. Free checking needs neither.');});
