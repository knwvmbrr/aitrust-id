/* Optional author receipts: reference conformance control, not coercion detection. */
(function(root){
 'use strict';
 const VERSION='author-choice/1.0.0';
 const profile=()=>({version:VERSION,receipt_required:false,ordinary_use_without_receipt:true,automatic_receipt:false,automatic_upload:false});
 function inspect(policy){
  if(!policy||typeof policy!=='object'||Array.isArray(policy)||Object.keys(policy).sort().join('|')!==Object.keys(profile()).sort().join('|'))throw Error('Unknown or missing author-choice policy field');
  if(policy.version!==VERSION||policy.receipt_required!==false||policy.ordinary_use_without_receipt!==true||policy.automatic_receipt!==false||policy.automatic_upload!==false)throw Error('Non-optional receipt policy refused');
  return Object.freeze({...policy});
 }
 function authorize(policy,action,authorChoice=false){
  inspect(policy);
  if(!['observe','use','export','issue','endorse'].includes(action)||typeof authorChoice!=='boolean')throw Error('Unsupported author-choice action');
  if(['export','issue','endorse'].includes(action)&&authorChoice!==true)return false;
  return true;
 }
 const api=Object.freeze({VERSION,profile,inspect,authorize});
 if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.AITrustAuthorChoice=api;
})(globalThis);
