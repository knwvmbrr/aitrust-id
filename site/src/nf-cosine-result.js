/* Optional canonical ASCII-cosine replay; literal never imports this module. */
import manifest from './nf-device-manifest.json' with {type:'json'};
import {need,inputContext,validateNF} from './nf-device-result.js';
const whitespace=cp=>cp>=9&&cp<=13||cp>=28&&cp<=32||[133,160,5760,8232,8233,8239,8287,12288].includes(cp)||cp>=8192&&cp<=8202;
function lines(text){
 const result=[];let offset=0;
 // Python str.splitlines: CRLF is one boundary; all supported boundaries retained.
 for(const unit of text.match(/[^\n\r\v\f\x1c-\x1e\x85\u2028\u2029]*(?:\r\n|[\n\r\v\f\x1c-\x1e\x85\u2028\u2029]|$)/gu)||[]){
  if(!unit)continue;let body=unit.replace(/[\r\n]+$/u,'');const p=Array.from(body);let left=0,right=p.length;
  while(left<right&&whitespace(p[left].codePointAt(0)))left++;while(right>left&&whitespace(p[right-1].codePointAt(0)))right--;
  if(right>left)result.push([offset+left,offset+right,p.slice(left,right).join('')]);offset+=Array.from(unit).length;
 }
 return result;
}
function vector(text){need(/^[\x00-\x7f]*$/.test(text));const tokens=text.match(/[A-Za-z0-9]+/g);need(tokens&&tokens.length<=512);const v=new Map();for(const t of tokens){const k=t.toLowerCase();v.set(k,(v.get(k)||0)+1);}return v;}
function cosine(a,b){let dot=0,aa=0,bb=0;for(const [k,v] of a){dot+=v*(b.get(k)||0);aa+=v*v;}for(const v of b.values())bb+=v*v;return Math.min(1,dot/Math.sqrt(aa*bb));}
// Python round(x,12) uses nearest-even on the actual binary64 value.
// Preserve exact canonical rows, including a representable decimal half tie.
export function round12(score){
 need(Number.isFinite(score)&&score>=0&&score<=1);if(score===0)return 0;
 const view=new DataView(new ArrayBuffer(8));view.setFloat64(0,score,false);
 const bits=view.getBigUint64(0,false),field=Number((bits>>52n)&2047n);
 const mantissa=(bits&((1n<<52n)-1n))+(field?1n<<52n:0n),exponent=(field?field-1023:-1022)-52;
 let numerator=mantissa*1000000000000n,denominator=1n;
 if(exponent>=0)numerator<<=BigInt(exponent);else denominator<<=BigInt(-exponent);
 let quotient=numerator/denominator;const twice=(numerator%denominator)*2n;
 if(twice>denominator||(twice===denominator&&quotient%2n===1n))quotient++;
 return Number(quotient)/1000000000000;
}
export function cosineOriginal(c){
 const claims=lines(c.claim.normalized);need(claims.length>=1&&claims.length<=32);
 const query=claims.map(row=>[...row,vector(row[2])]),passages=[];let unsupported=0,total=0;
 for(const row of lines(c.passage.normalized)){need(++total<=4096);try{passages.push([...row,vector(row[2])]);}catch{unsupported++;}}
 need(passages.length);const findings=[];
 for(const [start,end,,v] of query){const matched=[];
  for(const [left,right,,w] of passages){const score=cosine(v,w);if(score>=.75)matched.push({id:'sig.corpus_support.v1',score:round12(score),spans:[[start,end]],reference:{document_id:'selected',document_sha256:c.passage.identity.raw_sha256,normalized_source_sha256:c.passage.identity.normalized_sha256,source_span:[left,right]},meaning:'lexical_similarity_only'});}
  matched.sort((a,b)=>b.score-a.score||a.reference.source_span[0]-b.reference.source_span[0]);findings.push(...matched.slice(0,10));
 }
 findings.sort((a,b)=>b.score-a.score||a.spans[0][0]-b.spans[0][0]||a.reference.source_span[0]-b.reference.source_span[0]);
 return {format:'local-corpus-support-observation/1.0.0',method:'corpus-support-ascii-cosine/1.0.0',method_sha256:manifest.checks.cosine.sources['protocol/corpus_support.py'],subject_sha256:c.claim.identity.normalized_sha256,subject_characters:c.claim.identity.normalized_characters,manifest_sha256:c.corpus,normalization_id:manifest.normalization_id,offset_unit:'NFC_unicode_codepoint',claim_unit:'nonempty_trimmed_input_line',reference_unit:'nonempty_trimmed_source_line',threshold:.75,maximum_findings:10,claim_units:claims.length,reference_passages:passages.length,unsupported_reference_passages:unsupported,reference_freshness:'unestablished',findings:findings.slice(0,10),state:findings.length?'SIMILAR_PASSAGE':'NO_SIMILAR_PASSAGE',score_is_probability:false,truth_established:false,entailment_checked:false,network_used:false,tags:[],independent_accuracy_evidence:false};
}
export function validCosineRecord(record,context){need(context.check==='cosine');return validateNF(record,context,cosineOriginal(inputContext(context)));}
