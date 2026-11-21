import manifest from './mt-mobile-device-manifest.json' with {type:'json'};
import {normalizeNFC,NORMALIZATION_ID} from '../../protocol/normalization.mjs';
import {validateAuthorityDetails} from './mt-device-result.js';
const contexts=new WeakMap(),validated=new WeakSet();
const fail=()=>{throw Error('Double-quote observation unavailable');};
const INNER=['tools/authority_mobile_quotation.py','scripts/authority-mobile-quotation.py','tools/authority_quotation.py','scripts/authority-quotation.py','tools/language_observations.py','protocol/normalization.py','protocol/unicode15-data.json','protocol/corpus.py','tools/blind_review_io.py'];
const OUTER=['tools/mt_mobile_device.py',...INNER];
function object(v,keys){if(!v||typeof v!=='object'||Array.isArray(v)||![Object.prototype,null].includes(Object.getPrototypeOf(v)))fail();const own=Reflect.ownKeys(v);if(own.length!==keys.length||own.some(k=>typeof k!=='string'||!keys.includes(k)))fail();for(const k of own){const d=Object.getOwnPropertyDescriptor(v,k);if(!Object.hasOwn(d,'value')||!d.enumerable)fail();}}
const digest=async b=>Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',b)),v=>v.toString(16).padStart(2,'0')).join('');
function quotation(points){
 if(points.some(c=>['«','»','`'].includes(c)))fail();const ascii=points.includes('"'),curly=points.some(c=>c==='“'||c==='”');if(ascii&&curly)fail();
 const quotes=[];let opening=null;
 for(let i=0;i<points.length;i++){
  const c=points[i];if(!['"','“','”'].includes(c))continue;if(points[i-1]==='\\')fail();
  if(c==='"'){if(opening===null)opening=i;else{quotes.push([opening,i+1]);opening=null;}}
  else if(c==='“'){if(opening!==null)fail();opening=i;}
  else{if(opening===null)fail();quotes.push([opening,i+1]);opening=null;}
  if(quotes.length>64)fail();
 }
 if(opening!==null)fail();return {quotes,style:curly?'CURLY':ascii?'ASCII':'NONE'};
}
export async function mtMobileSubject(text){
 if(typeof text!=='string'||!text.trim()||text.includes('\0')||Array.from(text).length>8000||Array.from(text).some(c=>{const n=c.codePointAt(0);return n>=0xd800&&n<=0xdfff;}))fail();
 const raw=new TextEncoder().encode(text),normalized=normalizeNFC(text),points=Array.from(normalized);if(raw.length>32000||points.length>8000||NORMALIZATION_ID!==manifest.normalization_id)fail();
 const [rawHash,hash]=await Promise.all([digest(raw),digest(new TextEncoder().encode(normalized))]);
 const context=Object.freeze({raw_sha256:rawHash,raw_characters:Array.from(text).length,raw_bytes:raw.length,subject_sha256:hash,subject_characters:points.length});contexts.set(context,{points,...quotation(points)});return context;
}
export function validMTMobileRecord(record,context){
 const selected=contexts.get(context);if(!selected)fail();
 object(record,['format','check','method','state','counts','original','raw_sha256','raw_characters','raw_bytes','subject_sha256','subject_characters','normalization_id','offset_unit','source_sha256','tags','tag_asserted','intent_established','truth_established','independent_accuracy_evidence','subject_text_included']);
 if(record.format!=='mt-device-mobile-authority/1.0.0'||record.check!=='authority-curly'||record.method!==manifest.method||!['OBSERVATIONS','NO_SUPPORTED_PATTERN'].includes(record.state)||record.normalization_id!==manifest.normalization_id||record.offset_unit!=='NFC_unicode_codepoint')fail();
 for(const k of Object.keys(context))if(record[k]!==context[k])fail();for(const k of ['tag_asserted','intent_established','truth_established','independent_accuracy_evidence','subject_text_included'])if(record[k]!==false)fail();
 if(!Array.isArray(record.tags)||Reflect.ownKeys(record.tags).length!==1||record.tags.length)fail();
 object(record.source_sha256,OUTER);for(const name of OUTER)if(record.source_sha256[name]!==manifest.sources[name])fail();
 const o=record.original;
 validateAuthorityDetails(o,record.counts,selected.points,{format:'mobile-authority-quotation-observation/v1',sources:Object.fromEntries(INNER.map(name=>[name,manifest.sources[name]])),quoteSpans:selected.quotes,parameters:{language:'en',quote_grammar:'one_style_ASCII_lexical_pairs_or_balanced_curly_double_quotes',citation_scope:'same_literal_unit_and_supported_quote_context',max_quotes:64,max_phrases:128,max_units:512,max_markers:256,quote_style:selected.style,ascii_nesting_inferred:false,single_quotes_interpreted:false}});
 if(o.method!==record.method||o.state!==record.state||o.subject_sha256!==context.subject_sha256||o.normalization_id!==record.normalization_id||o.offset_unit!==record.offset_unit)fail();
 for(const k of ['intent_established','truth_established','independent_accuracy_evidence','network_used'])if(o[k]!==false)fail();if(!Array.isArray(o.tags)||Reflect.ownKeys(o.tags).length!==1||o.tags.length)fail();
 if(new TextEncoder().encode(JSON.stringify(record)).length>manifest.max_record_bytes)fail();
 const stack=[record];while(stack.length){const v=stack.pop();if(v&&typeof v==='object'&&!Object.isFrozen(v)){stack.push(...Object.values(v));Object.freeze(v);}}
 validated.add(record);return record;
}
export function explainMTMobile(record){
 if(!validated.has(record))fail();const c=record.counts,found=c.quoted_phrase_count+c.outside_supported_quotes_with_marker+c.outside_supported_quotes_without_marker;
 return {title:found?'Authority phrase locations found':'No supported authority phrase found',body:`${c.quoted_phrase_count} quoted · ${c.outside_supported_quotes_with_marker} outside with a source marker · ${c.outside_supported_quotes_without_marker} outside without one. A marker is not a checked source.`};
}
