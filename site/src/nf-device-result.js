import manifest from './nf-device-manifest.json' with {type:'json'};
import {normalizeNFC,NORMALIZATION_ID} from '../../protocol/normalization.mjs';
const contexts=new WeakMap(),valid=new WeakSet();
const common=['tools/nf_device.py','protocol/corpus.py','protocol/normalization.py','protocol/unicode15-data.json'];
export const need=value=>{if(!value)throw Error('Reference comparison unavailable');};
export const digest=async raw=>Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',raw)),n=>n.toString(16).padStart(2,'0')).join('');
export const encoded=text=>new TextEncoder().encode(text);
export function canonical(value){
 if(Array.isArray(value))return '['+value.map(canonical).join(',')+']';
 if(value&&typeof value==='object')return '{'+Object.keys(value).sort().map(k=>JSON.stringify(k)+':'+canonical(value[k])).join(',')+'}';
 return JSON.stringify(value);
}
function closed(value){
 const seen=new Set();let nodes=0,characters=0;
 function visit(v){
  need(++nodes<=5000);
  if(typeof v==='string'){characters+=v.length;need(v.length<=8000&&characters<=150000);return;}
  if(v===null||typeof v==='boolean')return;
  if(typeof v==='number'){need(Number.isFinite(v));return;}
  need(v&&typeof v==='object'&&!seen.has(v));seen.add(v);
  if(Array.isArray(v)){
   need(v.length<=256&&Reflect.ownKeys(v).length===v.length+1);
   for(let i=0;i<v.length;i++){const d=Object.getOwnPropertyDescriptor(v,String(i));need(d&&Object.hasOwn(d,'value')&&d.enumerable);visit(d.value);}
  }else{
   need([Object.prototype,null].includes(Object.getPrototypeOf(v)));
   const keys=Reflect.ownKeys(v);need(keys.length<=40);
   for(const k of keys){need(typeof k==='string'&&k.length<=120);const d=Object.getOwnPropertyDescriptor(v,k);need(d&&Object.hasOwn(d,'value')&&d.enumerable);visit(d.value);}
  }
 }
 visit(value);
}
export function validNFInput(text){
 need(typeof text==='string'&&text.trim()&&!text.includes('\0')&&Array.from(text).length<=manifest.max_codepoints&&encoded(text).length<=manifest.max_bytes);
 need(!Array.from(text).some(c=>{const n=c.codePointAt(0);return n>=0xd800&&n<=0xdfff;}));
 const n=normalizeNFC(text);need(Array.from(n).length<=manifest.max_codepoints&&NORMALIZATION_ID===manifest.normalization_id);
}
async function identity(text){
 validNFInput(text);const normalized=normalizeNFC(text),raw=encoded(text);
 return {text,normalized,points:Array.from(normalized),identity:{raw_sha256:await digest(raw),raw_bytes:raw.length,raw_characters:Array.from(text).length,normalized_sha256:await digest(encoded(normalized)),normalized_characters:Array.from(normalized).length}};
}
export async function nfInputs(claim,passage,check){
 need(check==='literal'||check==='cosine');const [a,b]=await Promise.all([identity(claim),identity(passage)]);
 const content={format:'local-reference-corpus/v1',documents:[{id:'selected',sha256:b.identity.raw_sha256,text:passage}]};
 const context=Object.freeze({check});contexts.set(context,{claim:a,passage:b,corpus:await digest(encoded(canonical(content)))});return context;
}
export function inputContext(context){const c=contexts.get(context);need(c);return c;}
export function literalOriginal(c){
 const matches=[];let start=0;
 // Use codepoint arrays rather than UTF16 indices for exact canonical spans.
 const a=c.claim.points,b=c.passage.points;
 while(matches.length<10&&start<=b.length-a.length){
  let found=-1;for(let i=start;i<=b.length-a.length;i++){if(a.every((ch,j)=>b[i+j]===ch)){found=i;break;}}
  if(found<0)break;
  matches.push({document_id:'selected',document_sha256:c.passage.identity.raw_sha256,normalized_source_sha256:c.passage.identity.normalized_sha256,source_span:[found,found+a.length],query_span:[0,a.length],normalization_id:manifest.normalization_id,offset_unit:'NFC_unicode_codepoint',passage:c.claim.normalized});start=found+a.length;
 }
 return {format:'local-reference-match/v1',manifest_sha256:c.corpus,state:matches.length?'REFERENCE_MATCH':'NO_REFERENCE_MATCH',query_sha256:c.claim.identity.normalized_sha256,matches,match_limit:10,tag_assertion:false,independently_validated:false,meaning:'Literal reference match only; no truth or contradiction verdict.'};
}
export function validateNF(record,context,original){
 const c=inputContext(context),check=context.check;closed(record);
 const names=check==='literal'?common:[...common,'protocol/corpus_support.py'];
 const expected={format:'nf-selected-reference-device/1.0.0',check,method:manifest.checks[check].method,claim:c.claim.identity,passage:c.passage.identity,normalization_id:manifest.normalization_id,offset_unit:'NFC_unicode_codepoint',selection:'complete_explicit_claim_and_passage',corpus_manifest_sha256:c.corpus,original,source_sha256:Object.fromEntries(names.map(p=>[p,manifest.checks[check].sources[p]])),tags:[],tag_asserted:false,truth_established:false,source_support_established:false,independent_accuracy_evidence:false,reference_freshness:'unestablished',network_used:false};
 need(canonical(record)===canonical(expected)&&encoded(JSON.stringify(record)).length<=262144);
 const freeze=v=>{if(v&&typeof v==='object'){Object.values(v).forEach(freeze);Object.freeze(v);}};freeze(record);valid.add(record);return record;
}
export function validLiteralRecord(record,context){need(context.check==='literal');return validateNF(record,context,literalOriginal(inputContext(context)));}
export function explainNF(record){
 need(valid.has(record));
 if(record.check==='literal')return record.original.matches.length?{title:'Exact words found',body:'Your selected words appear in this passage. That does not make the claim true.',count:record.original.matches.length}:{title:'No exact words found',body:'The passage may use different words. This is not a falsehood finding.',count:0};
 const count=record.original.findings.length;
 return count?{title:'Similar wording found',body:'Similar words can disagree. This check does not tell whether the passage supports the claim.',count}:{title:'No similar wording found',body:'This word-overlap method may miss a useful passage. It does not judge truth.',count:0};
}
