import {loadManifest,choiceClient} from './mt-choice-client.mjs';
import {explainChoice} from './mt-choice-result.mjs';
const $=id=>document.getElementById(id);
let client,record,sequence=0,busy=false;
const fields=['subject','first','second','reference','whole-frame'];
function hideResult(){record=null;$('result').hidden=true;$('details')?.remove();$('details-warning').hidden=true;$('details-toggle').textContent='Show exact record';$('details-toggle').setAttribute('aria-expanded','false');}
function controls(){ $('check').disabled=!client||busy;$('cancel').hidden=!busy; }
function cancel(message='Ready. Check is always your choice.'){sequence++;client?.stop();busy=false;hideResult();$('unavailable').hidden=true;$('status').textContent=message;controls();}
for(const id of fields)$(id).addEventListener('input',()=>cancel());
$('clear').addEventListener('click',()=>{cancel('Cleared. No previous result is retained.');for(const id of fields){if(id==='whole-frame')$(id).checked=false;else $(id).value='';}$('example').value='';$('subject').focus();});
$('cancel').addEventListener('click',()=>cancel('Cancelled. No valid observation completed.'));
const examples={additive:'Not only tea but also coffee.',either:'Either tea or coffee.',only:'Only tea or coffee.',neither:'Neither tea nor coffee.',between:'Between tea and coffee.'};
$('example').addEventListener('change',()=>{cancel();const value=examples[$('example').value];if(!value)return;$('subject').value=value;$('first').value='tea';$('second').value='coffee';$('reference').value='Water is also listed.';$('whole-frame').checked=false;$('subject').focus();});
$('practice').addEventListener('submit',async event=>{
 event.preventDefault();if(!client||busy)return;
 hideResult();$('unavailable').hidden=true;const token=++sequence;busy=true;controls();
 try{
  const value=await client.check({subject:$('subject').value,first:$('first').value,second:$('second').value,reference:$('reference').value,whole_frame:$('whole-frame').checked});
  if(token!==sequence)return;record=value;const brief=explainChoice(value);
  $('result-title').textContent=brief.title;$('result-message').textContent=brief.message;
  $('result-counts').textContent=`Additive frames: ${value.counts.additive_frames}. Other paired frames: ${value.counts.other_paired_frames}. This is wording evidence, not a tag or a safety clearance.`;
  $('result').hidden=false;$('status').textContent='Finished on this device. Exact evidence stays closed until you choose to view it.';
 }catch{
  if(token!==sequence)return;hideResult();$('status').textContent='Unavailable: no valid observation completed.';
  $('unavailable').textContent='The check could not finish. Confirm the whole-frame declaration, input limits and two unique ordered items, or clear and try again. No safe or zero-finding result is implied.';$('unavailable').hidden=false;if(!$('whole-frame').checked)$('whole-frame').focus();
 }finally{if(token===sequence){busy=false;controls();}}
});
$('details-toggle').addEventListener('click',()=>{
 if(!record)return;const open=!$('details');
 if(open){const detail=document.createElement('pre');detail.id='details';detail.setAttribute('aria-label','Private selected wording evidence');detail.textContent=JSON.stringify(record,null,2);$('result').append(detail);}else $('details').remove();
 $('details-warning').hidden=!open;$('details-toggle').textContent=open?'Hide exact record':'Show exact record';$('details-toggle').setAttribute('aria-expanded',String(open));
});
window.addEventListener('pagehide',()=>{cancel('Stopped.');for(const id of fields){if(id==='whole-frame')$(id).checked=false;else $(id).value='';}});
loadManifest().then(manifest=>{client=choiceClient(manifest,{onStatus:message=>{$('status').textContent=message;}});$('method-source').href='./'+manifest.bundle;$('method-source').hidden=false;$('status').textContent='Ready. No worker or analysis starts until you choose Check.';controls();}).catch(()=>{$('status').textContent='Practice files unavailable. No analysis started.';$('unavailable').textContent='This optional practice could not load. The separate CLI and other personal tools remain available.';$('unavailable').hidden=false;});
