import {normalizeNFC, NORMALIZATION_ID} from '../../protocol/normalization.mjs';
const sources=['tools/mt_choice_device.py','tools/choice_framing.py','tools/language_observations.py','protocol/corpus.py','protocol/normalization.py','protocol/unicode15-data.json'];
const contexts=new WeakMap(), accepted=new WeakSet();
const fail=()=>{throw Error('Selected wording is unavailable.');};
const eq=(a,b)=>JSON.stringify(a)===JSON.stringify(b);
export const digest=async bytes=>Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes)),v=>v.toString(16).padStart(2,'0')).join('');
const hash=text=>digest(new TextEncoder().encode(text));
function object(value,keys){
 if(!value||typeof value!=='object'||Array.isArray(value)||![Object.prototype,null].includes(Object.getPrototypeOf(value)))fail();
 const own=Reflect.ownKeys(value);if(own.length!==keys.length||own.some(k=>typeof k!=='string')||!eq(own.toSorted(),keys.toSorted()))fail();
 for(const key of own){const d=Object.getOwnPropertyDescriptor(value,key);if(!d||!Object.hasOwn(d,'value')||!d.enumerable)fail();}
}
function list(value,max){
 if(!Array.isArray(value)||Object.getPrototypeOf(value)!==Array.prototype||value.length>max||Reflect.ownKeys(value).length!==value.length+1)fail();
 for(let i=0;i<value.length;i++){const d=Object.getOwnPropertyDescriptor(value,String(i));if(!d||!Object.hasOwn(d,'value')||!d.enumerable)fail();}
 return value;
}
function text(value,limit,bytes){
 if(typeof value!=='string'||!value.trim()||value.includes('\0')||Array.from(value).length>limit||new TextEncoder().encode(value).length>bytes||Array.from(value).some(c=>{const n=c.codePointAt(0);return n>=0xd800&&n<=0xdfff;}))fail();
 const normalized=normalizeNFC(value);if(Array.from(normalized).length>limit)fail();return normalized;
}
function span(value,size){list(value,2);if(value.length!==2||!value.every(Number.isSafeInteger)||value[0]<0||value[0]>=value[1]||value[1]>size)fail();return value;}
function falseFields(value,keys){for(const key of keys)if(value[key]!==false)fail();}
function sourceMap(value,manifest){object(value,sources);for(const name of sources)if(value[name]!==manifest.sources[name])fail();}
function stable(value){if(Array.isArray(value))return '['+value.map(stable).join(',')+']';if(value&&typeof value==='object')return '{'+Object.keys(value).sort().map(k=>JSON.stringify(k)+':'+stable(value[k])).join(',')+'}';return JSON.stringify(value);}
function uniqueLocation(subject,item){const at=subject.indexOf(item);if(at<0||subject.indexOf(item,at+1)>=0)fail();return [Array.from(subject.slice(0,at)).length,Array.from(subject.slice(0,at+item.length)).length];}
export async function choiceContext(request,manifest){
 object(request,['subject','first','second','reference','whole_frame']);if(request.whole_frame!==true)fail();
 const normalized=text(request.subject,2000,8000),reference=text(request.reference,2000,8000);
 const first=text(request.first,256,1024),second=text(request.second,256,1024);
 const selected=[uniqueLocation(normalized,first),uniqueLocation(normalized,second)];
 if(selected[0][1]>selected[1][0]||first.trim().toLowerCase()===second.trim().toLowerCase())fail();
 const wire=JSON.stringify(request);if(new TextEncoder().encode(wire).length>24000||NORMALIZATION_ID!=='NFC-Unicode-15.0.0/v1'||manifest.method!=='caller-bound-choice-framing-observation/1.3.0')fail();
 const rawReferenceHash=await hash(request.reference);
 const content={format:'local-reference-corpus/v1',documents:[{id:'practice-reference',text:request.reference,sha256:rawReferenceHash}]};
 const value={wire,points:Array.from(normalized),selected,subject:normalized,reference,
  requestHash:await hash(wire),rawSubjectHash:await hash(request.subject),subjectHash:await hash(normalized),
  rawCharacters:Array.from(request.subject).length,rawBytes:new TextEncoder().encode(request.subject).length,
  rawReferenceHash,referenceHash:await hash(reference),referenceRawCharacters:Array.from(request.reference).length,
  referenceCharacters:Array.from(reference).length,itemHashes:{first:await hash(request.first),second:await hash(request.second)},
  corpusHash:await hash(stable(content))};
 const context=Object.freeze({request_sha256:value.requestHash});contexts.set(context,value);return {context,wire};
}
const pySpace=c=>/^[\u0009-\u000d\u001c-\u0020\u0085\u00a0\u1680\u2000-\u200a\u2028\u2029\u202f\u205f\u3000]$/u.test(c);
const word=c=>c!==undefined&&/^[\p{L}\p{N}_]$/u.test(c);
function separators(points,allowed,nonempty=false){if(nonempty&&!points.length)fail();if(points.some(c=>!pySpace(c)&&!allowed.includes(c)))fail();}
function phrase(points,words){const pieces=[];let token='';for(const c of points){if(pySpace(c)){if(token){pieces.push(token);token='';}}else token+=c;}if(token)pieces.push(token);if(!eq(pieces.map(s=>s.toLowerCase()),words)||!points.length||pySpace(points[0])||pySpace(points.at(-1)))fail();}
function negations(points){const spans=[];for(let at=0;at<points.length;at++){if(word(points[at-1]))continue;for(const token of ['not','neither','nor']){const end=at+token.length;if(end<=points.length&&!word(points[end])&&points.slice(at,end).join('').toLowerCase()===token){spans.push([at,end]);break;}}}return spans;}
function expectedMarkers(c){
 const [first,second]=c.selected,prefix=c.points.slice(0,first[0]),gap=c.points.slice(first[1],second[0]);
 function leading(words,required){
  let at=prefix.length;while(at&&pySpace(prefix[at-1]))at--;const end=at;
  if(required&&end===prefix.length)return null;
  for(let i=words.length-1;i>=0;i--){
   const letters=Array.from(words[i]);if(at<letters.length||prefix.slice(at-letters.length,at).join('').toLowerCase()!==words[i])return null;at-=letters.length;
   if(i){const before=at;while(at&&pySpace(prefix[at-1]))at--;if(at===before)return null;}
  }
  return word(prefix[at-1])?null:[at,end];
 }
 function connector(words,required){
  let start=0,end=gap.length;while(start<end&&(pySpace(gap[start])||gap[start]===','))start++;
  while(end>start&&(pySpace(gap[end-1])||[',',':'].includes(gap[end-1])))end--;
  if(required&&(!start||end===gap.length))return null;
  const parts=gap.slice(start,end).join('').split(/[\u0009-\u000d\u001c-\u0020\u0085\u00a0\u1680\u2000-\u200a\u2028\u2029\u202f\u205f\u3000]+/u);
  return eq(parts.map(v=>v.toLowerCase()),words)?[first[1]+start,first[1]+end]:null;
 }
 let a=leading(['not','only'],true),b=connector(['but','also'],true);
 if(a&&b)return {construction:'not_only_but_also',markers:[a,b]};
 for(const [construction,words] of [['either_or',['either','or']],['only_or',['only','or']],['neither_nor',['neither','nor']],['between_and',['between','and']]]){
  a=leading([words[0]],false);b=connector([words[1]],false);if(a&&b)return {construction,markers:[a,b]};
 }
 return null;
}
function freeze(value){const todo=[value];while(todo.length){const item=todo.pop();if(item&&typeof item==='object'&&!Object.isFrozen(item)){todo.push(...Object.values(item));Object.freeze(item);}}return value;}
export function validateChoice(record,context,manifest){
 const c=contexts.get(context);if(!c)fail();
 object(record,['format','method','state','request_sha256','raw_subject_sha256','raw_subject_characters','raw_subject_bytes','subject_sha256','subject_characters','reference','item_request_sha256','counts','normalization_id','span_units','selection','original','source_sha256','tags','intent_established','truth_established','independent_accuracy_evidence','additional_option_verified','subject_or_reference_text_included']);
 if(record.format!=='mt-selected-choice-device/1.0.0'||record.method!==manifest.method||!['OBSERVATIONS','NO_SUPPORTED_PATTERN'].includes(record.state)||record.request_sha256!==c.requestHash||record.raw_subject_sha256!==c.rawSubjectHash||record.subject_sha256!==c.subjectHash||record.raw_subject_characters!==c.rawCharacters||record.raw_subject_bytes!==c.rawBytes||record.subject_characters!==c.points.length||record.normalization_id!==NORMALIZATION_ID||record.span_units!=='NFC_unicode_codepoints'||record.selection!=='caller_declared_whole_frame_and_unique_literal_items')fail();
 object(record.reference,['raw_sha256','normalized_sha256','raw_characters','normalized_characters']);
 if(record.reference.raw_sha256!==c.rawReferenceHash||record.reference.normalized_sha256!==c.referenceHash||record.reference.raw_characters!==c.referenceRawCharacters||record.reference.normalized_characters!==c.referenceCharacters)fail();
 object(record.item_request_sha256,['first','second']);for(const name of ['first','second'])if(record.item_request_sha256[name]!==c.itemHashes[name])fail();
 falseFields(record,['intent_established','truth_established','independent_accuracy_evidence','additional_option_verified','subject_or_reference_text_included']);list(record.tags,0);sourceMap(record.source_sha256,manifest);
 const original=record.original;
 object(original,['profile','state','language','subject_sha256','manifest_sha256','method_sha256','runtime','normalization_id','span_units','selection','observations','unmatched_selected_frames','source_freshness','truth_established','independent_corroboration','tag_asserted','release_approved']);
 if(original.profile!==record.method||original.state!==record.state||original.language!=='en'||original.subject_sha256!==c.subjectHash||original.manifest_sha256!==c.corpusHash||original.method_sha256!==manifest.sources['tools/choice_framing.py']||original.normalization_id!==NORMALIZATION_ID||original.span_units!==record.span_units||original.selection!=='caller_selected_two_choices_and_additional_reference'||original.source_freshness!=='unestablished')fail();
 falseFields(original,['truth_established','independent_corroboration','tag_asserted','release_approved']);
 object(original.runtime,['implementation','python_version','unicode_runtime']);
 if(original.runtime.implementation!=='CPython'||original.runtime.python_version!==manifest.python_version||typeof original.runtime.unicode_runtime!=='string'||!/^\d{1,2}\.\d\.\d$/.test(original.runtime.unicode_runtime))fail();
 list(original.observations,1);list(original.unmatched_selected_frames,1);original.unmatched_selected_frames.forEach(s=>span(s,c.points.length));
 if(original.observations.length+original.unmatched_selected_frames.length!==1||(record.state==='OBSERVATIONS')!==Boolean(original.observations.length))fail();
 if(original.unmatched_selected_frames.length&&!eq(original.unmatched_selected_frames,[[0,c.points.length]]))fail();
 const expectedPair=expectedMarkers(c);if(Boolean(expectedPair)!==Boolean(original.observations.length))fail();
 let additive=0;
 for(const row of original.observations){
  if(!row||typeof row!=='object')fail();const descriptor=Object.getOwnPropertyDescriptor(row,'construction');if(!descriptor||!Object.hasOwn(descriptor,'value'))fail();
  const isAdditive=descriptor.value==='not_only_but_also';
  object(row,['proposed_signal','frame_span','choice_spans','binary_marker_spans','construction','negation_marker_spans','negation_scope_resolved','additional_reference','meaning','additional_option_verified','exhaustiveness_established','quoted_or_recommended_resolved','manipulation_established',...(isAdditive?['additive_marker_spans']:[])]);
  span(row.frame_span,c.points.length);list(row.choice_spans,2);if(row.choice_spans.length!==2)fail();row.choice_spans.forEach(s=>span(s,c.points.length));
  if(typeof row.construction!=='string'||!eq(row.frame_span,[0,c.points.length])||!eq(row.choice_spans,c.selected))fail();
  const pairs={either_or:['either','or'],only_or:['only','or'],neither_nor:['neither','nor'],between_and:['between','and'],not_only_but_also:['not only','but also']};
  if(!Object.hasOwn(pairs,row.construction))fail();
  const markers=isAdditive?row.additive_marker_spans:row.binary_marker_spans;list(markers,2);if(markers.length!==2)fail();markers.forEach(s=>span(s,c.points.length));
  if(isAdditive){list(row.binary_marker_spans,0);additive++;}
  if(row.construction!==expectedPair.construction||!eq(markers,expectedPair.markers))fail();
  const [a,b]=markers,[first,second]=c.selected;
  if(a[1]>first[0]||b[0]<first[1]||b[1]>second[0]||word(c.points[a[0]-1]))fail();
  for(let i=0;i<2;i++)phrase(c.points.slice(...markers[i]),pairs[row.construction][i].split(' '));
  separators(c.points.slice(a[1],first[0]),[],isAdditive);
  separators(c.points.slice(first[1],b[0]),[','],isAdditive);
  separators(c.points.slice(b[1],second[0]),[',',':'],isAdditive);
  list(row.negation_marker_spans,c.points.length);row.negation_marker_spans.forEach(s=>span(s,c.points.length));
  const expectedNegations=negations(c.points);if(!eq(row.negation_marker_spans,expectedNegations))fail();
  const proposed=(expectedNegations.length||isAdditive||row.construction==='between_and')?null:'sig.false_dilemma.v1';if(row.proposed_signal!==proposed)fail();
  falseFields(row,['negation_scope_resolved','additional_option_verified','exhaustiveness_established','quoted_or_recommended_resolved','manipulation_established']);
  if(row.meaning!==(isAdditive?'caller_selected_additive_mentions_not_exclusive_alternatives_with_caller_nominated_passage':'caller_selected_two_mentioned_choices_with_caller_nominated_additional_passage'))fail();
  object(row.additional_reference,['document_id','document_sha256','source_span','normalized_source_sha256']);
  span(row.additional_reference.source_span,c.referenceCharacters);
  if(row.additional_reference.document_id!=='practice-reference'||row.additional_reference.document_sha256!==c.rawReferenceHash||row.additional_reference.normalized_source_sha256!==c.referenceHash||!eq(row.additional_reference.source_span,[0,c.referenceCharacters]))fail();
 }
 object(record.counts,['matched_frames','additive_frames','other_paired_frames','unmatched_frames']);
 const expected={matched_frames:original.observations.length,additive_frames:additive,other_paired_frames:original.observations.length-additive,unmatched_frames:original.unmatched_selected_frames.length};
 for(const name of Object.keys(expected))if(record.counts[name]!==expected[name]||!Number.isSafeInteger(record.counts[name]))fail();
 accepted.add(record);return freeze(record);
}
export function explainChoice(record){
 if(!accepted.has(record))fail();
 if(record.counts.additive_frames)return {title:'Additive wording observed',message:'Your selected pair uses “not only … but also …”. This additively mentions two items; it does not establish exclusive alternatives or manipulation.'};
 if(record.counts.matched_frames)return {title:'Paired wording observed',message:'Supported paired markers surround the two items you declared. Your extra passage is nominated context, not a verified or feasible alternative.'};
 return {title:'No supported paired markers matched',message:'This finite grammar did not match your declared items. That does not establish safety, truth or absence of other framing.'};
}
