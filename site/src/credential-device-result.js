import manifest from './credential-device-manifest.json' with {type:'json'};
import {normalizeNFC,NORMALIZATION_ID} from '../../protocol/normalization.mjs';
const fail=()=>{throw Error('Python-flow observation unavailable');};
const contexts=new WeakMap(),validated=new WeakSet();
const SOURCES=['tools/credential_device.py','tools/credential_flow.py','protocol/normalization.py','protocol/unicode15-data.json','protocol/corpus.py'];
function object(value,keys){
 if(!value||typeof value!=='object'||Array.isArray(value)||![Object.prototype,null].includes(Object.getPrototypeOf(value)))fail();
 const own=Reflect.ownKeys(value),expected=keys.toSorted();
 if(own.length!==expected.length||own.some(k=>typeof k!=='string')||own.toSorted().some((k,i)=>k!==expected[i]))fail();
 for(const key of own){const d=Object.getOwnPropertyDescriptor(value,key);if(!Object.hasOwn(d,'value')||!d.enumerable)fail();}
}
function list(value,max){
 if(!Array.isArray(value)||value.length>max||Reflect.ownKeys(value).length!==value.length+1)fail();
 for(let i=0;i<value.length;i++){const d=Object.getOwnPropertyDescriptor(value,String(i));if(!d||!Object.hasOwn(d,'value')||!d.enumerable)fail();}
 return value;
}
const count=(n,max)=>{if(!Number.isSafeInteger(n)||n<0||n>max)fail();};
const digest=async raw=>Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',raw)),n=>n.toString(16).padStart(2,'0')).join('');
function falseFields(value,names){for(const key of names)if(value[key]!==false)fail();}
function sameSources(value){object(value,SOURCES);for(const name of SOURCES)if(value[name]!==manifest.sources[name])fail();}
export async function credentialSubject(text){
 if(typeof text!=='string'||!text.trim()||text.includes('\0')||Array.from(text).length>8000||Array.from(text).some(c=>{const n=c.codePointAt(0);return n>=0xd800&&n<=0xdfff;}))fail();
 const normalized=normalizeNFC(text),points=Array.from(normalized),raw=new TextEncoder().encode(text);
 if(raw.length>32000||!points.length||points.length>8000||NORMALIZATION_ID!==manifest.normalization_id)fail();
 const [rawHash,normalHash]=await Promise.all([digest(raw),digest(new TextEncoder().encode(normalized))]);
 const context=Object.freeze({raw_sha256:rawHash,raw_characters:Array.from(text).length,raw_bytes:raw.length,subject_sha256:normalHash,subject_characters:points.length});
 contexts.set(context,points);return context;
}
function freeze(record){const stack=[record],seen=new Set();while(stack.length){const v=stack.pop();if(!v||typeof v!=='object'||seen.has(v))continue;seen.add(v);stack.push(...Object.values(v));Object.freeze(v);}return record;}
export function validCredentialRecord(record,context){
 const points=contexts.get(context);if(!points)fail();let budget=0;
 function span(s){list(s,2);if(s.length!==2||!s.every(Number.isSafeInteger)||s[0]<0||s[0]>=s[1]||s[1]>points.length||++budget>16384)fail();return s.join(',');}
 object(record,['format','method','state','counts','original','raw_sha256','raw_characters','raw_bytes','subject_sha256','subject_characters','normalization_id','offset_unit','source_sha256','tags','tag_asserted','safety_established','context_classified','independent_accuracy_evidence','subject_text_included']);
 if(record.format!=='credential-flow-device/1.0.0'||record.method!==manifest.method||!['STATIC_FLOW','NO_SUPPORTED_FLOW'].includes(record.state)||record.normalization_id!==manifest.normalization_id||record.offset_unit!=='NFC_unicode_codepoint')fail();
 for(const k of ['raw_sha256','raw_characters','raw_bytes','subject_sha256','subject_characters'])if(record[k]!==context[k])fail();
 falseFields(record,['tag_asserted','safety_established','context_classified','independent_accuracy_evidence','subject_text_included']);list(record.tags,0);sameSources(record.source_sha256);
 object(record.counts,['recognized_reads','static_flows']);for(const key of ['recognized_reads','static_flows'])count(record.counts[key],2000);
 const o=record.original;
 object(o,['format','method','method_sha256','subject_sha256','subject_characters','normalization_id','offset_unit','state','recognized_read_spans','findings','network_used','subject_executed','secret_contents_read','intent_established','live_credential_verified','use_mention_classified','independent_accuracy_evidence','tags']);
 if(o.format!=='credential-flow-observation/v1'||o.method!==manifest.method||o.method_sha256!==manifest.sources['tools/credential_flow.py']||o.subject_sha256!==context.subject_sha256||o.subject_characters!==context.subject_characters||o.normalization_id!==manifest.normalization_id||o.offset_unit!=='NFC_unicode_codepoint'||o.state!==record.state)fail();
 falseFields(o,['network_used','subject_executed','secret_contents_read','intent_established','live_credential_verified','use_mention_classified','independent_accuracy_evidence']);list(o.tags,0);
 list(o.recognized_read_spans,2000);const reads=new Set();for(const s of o.recognized_read_spans){const key=span(s);if(reads.has(key))fail();reads.add(key);}
 list(o.findings,2000);const sinks=new Set();
 for(const finding of o.findings){
  object(finding,['id','source_spans','sink_span','meaning']);
  if(finding.id!=='sig.credential_exfil.v1'||finding.meaning!=='supported_static_credential_read_to_http_argument')fail();
  const sink=span(finding.sink_span);if(sinks.has(sink))fail();sinks.add(sink);
  list(finding.source_spans,2000);if(!finding.source_spans.length)fail();let previous;
  for(const s of finding.source_spans){const key=span(s);if(!reads.has(key)||previous&&(previous[0]>s[0]||previous[0]===s[0]&&previous[1]>=s[1]))fail();previous=s;}
 }
 if(record.counts.recognized_reads!==reads.size||record.counts.static_flows!==o.findings.length||record.state!==(o.findings.length?'STATIC_FLOW':'NO_SUPPORTED_FLOW'))fail();
 validated.add(record);return freeze(record);
}
export function explainCredential(record){
 if(!validated.has(record))fail();const flows=record.counts.static_flows;
 return Object.freeze({title:flows?`${flows} static read-to-HTTP ${flows===1?'flow':'flows'} observed`:'No supported read-to-HTTP flow observed',
 body:flows?'Within supported Python syntax, a credential-named read feeds an HTTP call argument. This does not show that code ran, that credentials exist, or what anyone intended.':'No such flow was observed within this finite static profile. This is not a safety clearance and does not rule out other behavior.',
 reads:record.counts.recognized_reads,flows});
}
