// Local review-file parsing. No network, predictions, storage or certification.
export const REVIEW_BYTE_LIMIT=10_000_000;
export function parseReviewFile(text){
 try{
  if(typeof text!=='string'||text.length>REVIEW_BYTE_LIMIT||new TextEncoder().encode(text).length>REVIEW_BYTE_LIMIT)throw Error();
  let position=0,nodes=0;const numeric=/-?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?/y;
  const space=()=>{while(position<text.length&&/[\t\n\r ]/.test(text[position]))position++;};
  function scalar(value){for(const char of value){const code=char.codePointAt(0);if(code===0||(code>=0xd800&&code<=0xdfff))throw Error();}return value;}
  function string(){
   if(text[position]!=='"')throw Error();
   const start=position++;
   while(position<text.length){const char=text[position++];if(char==='"')return scalar(JSON.parse(text.slice(start,position)));if(char==='\\'){if(position>=text.length)throw Error();position++;}else if(char.charCodeAt(0)<32)throw Error();}
   throw Error();
  }
  function value(depth){
   if(depth>64||++nodes>20_000)throw Error();space();const char=text[position];
   if(char==='"')return string();
   if(char==='{'){
    position++;space();const object=Object.create(null),keys=new Set();
    if(text[position]==='}'){position++;return object;}
    while(true){space();const key=string();if(keys.has(key))throw Error();keys.add(key);space();if(text[position++]!==':')throw Error();object[key]=value(depth+1);space();const next=text[position++];if(next==='}')return object;if(next!==',')throw Error();}
   }
   if(char==='['){position++;space();const array=[];if(text[position]===']'){position++;return array;}while(true){array.push(value(depth+1));space();const next=text[position++];if(next===']')return array;if(next!==',')throw Error();}}
   for(const [token,result] of [['null',null],['true',true],['false',false]])if(text.startsWith(token,position)){position+=token.length;return result;}
   numeric.lastIndex=position;const number=numeric.exec(text);if(!number)throw Error();position+=number[0].length;const result=Number(number[0]);if(!Number.isFinite(result))throw Error();return result;
  }
  const result=value(0);space();if(position!==text.length)throw Error();return result;
 }catch{throw Error('Invalid review file');}
}

const headerKeys=['format','reviewer_slot','dataset_sha256','method_sha256','gates_sha256','protocol_sha256','items'];
const itemKeys=['id','text','category','source','label','reason'];
const scalarText=(text,limit,required=true)=>{
 if(typeof text!=='string'||(required&&!text.trim())||Array.from(text).length>limit)throw Error('Invalid review file');
 for(const char of text){const code=char.codePointAt(0);if(code===0||(code>=0xd800&&code<=0xdfff))throw Error('Invalid review file');}
};
export function validateReview(value){
 if(!value||Object.keys(value).sort().join()!==headerKeys.slice().sort().join()||value.format!=='ai-trust-id-blind-ps-labels/v1'||![1,2].includes(value.reviewer_slot))throw Error('Invalid review file');
 for(const key of headerKeys.filter(k=>k.endsWith('sha256')))if(typeof value[key]!=='string'||!/^[a-f0-9]{64}$/.test(value[key]))throw Error('Invalid review file');
 if(!Array.isArray(value.items)||!value.items.length||value.items.length>1000)throw Error('Invalid review file');
 const ids=new Set();for(const row of value.items){
  if(!row||Object.keys(row).sort().join()!==itemKeys.slice().sort().join())throw Error('Invalid review file');
  for(const [key,limit] of [['id',100],['text',200000],['category',1000],['source',1000]])scalarText(row[key],limit);
  scalarText(row.reason,2000,false);
  if(ids.has(row.id)||![null,'positive','negative','ambiguous'].includes(row.label))throw Error('Invalid review file');
  ids.add(row.id);
 }return value;
}

export function readReviewBytes(bytes){
 try{
  if(!(bytes instanceof ArrayBuffer||ArrayBuffer.isView(bytes))||bytes.byteLength>REVIEW_BYTE_LIMIT)throw Error();
  return validateReview(parseReviewFile(new TextDecoder('utf-8',{fatal:true}).decode(bytes)));
 }catch{throw Error('Invalid review file');}
}
