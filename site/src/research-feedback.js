// Optional local metadata export. No intake, storage, fetch or content permission.
export const choices=Object.freeze({
 reported_result:['pattern_found','no_pattern_found','unavailable','not_checked'],
 failure_category:['none_observed','unexpected_finding','possible_missed_pattern','could_not_check','unclear_result'],
 feedback:['easy_to_understand','needs_clearer_explanation','hard_to_use','could_not_complete']
});
for(const values of Object.values(choices))Object.freeze(values);
const fields=['reported_result','failure_category','feedback'];
export function feedbackRecord(input){
 if(!input||Object.getPrototypeOf(input)!==Object.prototype||Object.keys(input).length!==fields.length||Object.keys(input).some(k=>!fields.includes(k)))throw Error('Choose the three listed answers only.');
 for(const field of fields)if(typeof input[field]!=='string'||!choices[field].includes(input[field]))throw Error('Choose an answer for each field.');
 return Object.freeze({schema_version:1,purpose:'PS_preview_usability_and_failure_review',tag:'PS',method_version:'context-v6',reported_result:input.reported_result,failure_category:input.failure_category,feedback:input.feedback,sharing:'local_file_not_submitted'});
}
export function initFeedback(doc){
 const form=doc.querySelector('[data-feedback-form]');if(!form)return;
 const preview=doc.querySelector('[data-feedback-preview]'),status=doc.querySelector('[data-feedback-status]'),download=doc.querySelector('[data-feedback-download]'),permission=form.elements.namedItem('download_choice');let serialized=null;
 function invalidate(){serialized=null;preview.textContent='Choose your answers, then preview the file.';permission.checked=false;download.disabled=true;status.textContent='Nothing has been sent or saved by this page.';}
 form.addEventListener('input',event=>{if(event.target===permission){download.disabled=!serialized||!permission.checked;return;}invalidate();});
 form.addEventListener('submit',event=>{event.preventDefault();try{const input=Object.fromEntries(fields.map(k=>[k,form.elements.namedItem(k).value]));serialized=JSON.stringify(feedbackRecord(input),null,2)+'\n';preview.textContent=serialized;download.disabled=!permission.checked;status.textContent='Preview ready. Review every field before downloading.';}catch{invalidate();status.textContent='Choose an answer for each field, then preview again.';}});
 form.addEventListener('reset',invalidate);
 download.addEventListener('click',()=>{if(!serialized||!permission.checked)return;const url=URL.createObjectURL(new Blob([serialized],{type:'application/json'}));const anchor=doc.createElement('a');anchor.href=url;anchor.download='AI-Trust-ID-PS-feedback.json';doc.body.append(anchor);anchor.click();anchor.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);status.textContent='Download requested. Nothing was submitted. Keep the file private until you choose where to share it.';});
 invalidate();form.hidden=false;
}
if(typeof document!=='undefined')initFeedback(document);
