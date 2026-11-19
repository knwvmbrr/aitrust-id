import manifest from './mt-device-manifest.json' with {type:'json'};
const fail=()=>{throw Error('MT observation unavailable');};
const hash=value=>typeof value==='string'&&/^[a-f0-9]{64}$/.test(value);
const count=value=>Number.isSafeInteger(value)&&value>=0&&value<=8000;
const equal=(a,b)=>JSON.stringify(Object.entries(a).sort())===JSON.stringify(Object.entries(b).sort());
export function validMTRecord(record,kind){
 if(!record||record.format!=='mt-device-phrase-explorer/1.0.0'||record.check!==kind||record.method!==manifest.methods[kind]||!['OBSERVATIONS','NO_SUPPORTED_PATTERN'].includes(record.state)||!hash(record.subject_sha256)||record.normalization_id!==manifest.normalization_id||record.offset_unit!=='NFC_unicode_codepoint')fail();
 const keys=['format','check','method','state','counts','original','subject_sha256','normalization_id','offset_unit','source_sha256','tags','intent_established','truth_established','independent_accuracy_evidence','subject_text_included'];
 if(Object.keys(record).sort().join()!==keys.sort().join()||record.tags?.length!==0||!Array.isArray(record.tags)||['intent_established','truth_established','independent_accuracy_evidence','subject_text_included'].some(k=>record[k]!==false))fail();
 const expected=Object.fromEntries(Object.entries(manifest.sources).filter(([path])=>!['LICENSE','NOTICE','eval/vectors/unicode/LICENSE.txt'].includes(path)));
 if(!equal(record.source_sha256,expected))fail();
 const original=record.original;
 if(!original||original.method!==record.method||original.state!==record.state||original.subject_sha256!==record.subject_sha256||original.normalization_id!==manifest.normalization_id||!Array.isArray(original.tags)||original.tags.length||original.intent_established!==false||original.truth_established!==false||original.independent_accuracy_evidence!==false||original.network_used!==false)fail();
 const counts=record.counts;
 if(!counts||!Object.values(counts).every(count))fail();
 if(kind==='urgency'){
  if(original.method_sha256!==manifest.sources['tools/language_observations.py']||!Array.isArray(original.findings)||!Array.isArray(original.measurements?.paired_units)||!equal(counts,{finding_groups:original.findings.length,paired_units:original.measurements.paired_units.length})||(record.state==='OBSERVATIONS')!==Boolean(original.findings.length)||original.quoted_or_recommended_context_classified!==false||original.score_is_probability!==false)fail();
 }else if(kind==='authority'){
  const names=['outside_supported_quotes_without_marker','outside_supported_quotes_with_marker','quoted_phrase_count','supported_quote_count'];
  if(!equal(counts,Object.fromEntries(names.map(n=>[n,original[n]])))||(record.state==='OBSERVATIONS')!==Boolean(counts.outside_supported_quotes_without_marker)||original.quote_endorsement_interpreted!==false||original.semantic_attribution_interpreted!==false||original.negation_interpreted!==false)fail();
 }else fail();
 return record;
}
export function explainMT(record){
 validMTRecord(record,record.check);
 if(record.check==='urgency')return record.state==='OBSERVATIONS'?
  {title:'Instruction + time wording found',body:'A request and a time phrase appear together. This could be ordinary advice.'}:
  record.counts.paired_units?{title:'Some time wording, no overall match',body:'A local pair appears, but the full supported pattern did not match. Other pressure may still be present.'}:
  {title:'No supported urgency pattern found',body:'This check did not find its instruction-and-time pattern. Other pressure may still be present.'};
 if(record.counts.outside_supported_quotes_without_marker)return {title:'Authority wording found',body:'An expertise or consensus phrase has no nearby outside-quote source marker. A source may appear elsewhere.'};
 if(record.counts.quoted_phrase_count)return {title:'Authority wording appears in a quote',body:'Quoted phrases are kept separate. This does not tell us whether anyone endorses them.'};
 if(record.counts.outside_supported_quotes_with_marker)return {title:'Authority wording has a source marker',body:'A marker appears nearby. This check has not verified the source.'};
 return {title:'No supported authority wording found',body:'This check did not find one of its supported phrases. Other wording may still be present.'};
}
