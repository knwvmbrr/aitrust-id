// Bounded consumer profile for the current authenticated, unsigned loopback route.
// Not a general schema engine, signature verifier or evidence of tag accuracy.
(()=>{
 const codes=new Set(['NF','FI','HP','MT','PS','IV','FA','PA','UNK','PII_REDACTED']);
 const production=new Set(['PS','PII_REDACTED']);
 const reasons=new Set(['below_floor','no_corpus','unsupported_modality','timeout','not_in_production_allowlist']);
 const object=v=>v!==null&&typeof v==='object'&&!Array.isArray(v);
 const text=(v,max=256)=>typeof v==='string'&&v.length<=max;
 const number=(v,min=0,max=1)=>typeof v==='number'&&Number.isFinite(v)&&v>=min&&v<=max;
 const integer=(v,min=0,max=200000)=>Number.isSafeInteger(v)&&v>=min&&v<=max;
 const array=(v,max)=>Array.isArray(v)&&v.length<=max;
 const hash=v=>typeof v==='string'&&/^[a-f0-9]{64}$/.test(v);
 function scalarText(value){if(typeof value!=='string'||!value.length||value.length>400000)return false;let count=0;for(const char of value){const cp=char.codePointAt(0);if(cp>=0xd800&&cp<=0xdfff||++count>200000)return false;}return true;}
 function timestamp(value){
  if(!text(value,64))return false;
  const m=value.match(/^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(?:\.\d+)?(Z|([+-])(\d{2}):(\d{2}))$/);
  if(!m)return false;const [year,month,day,hour,minute,second]=m.slice(1,7).map(Number);
  const leap=year%4===0&&(year%100!==0||year%400===0),days=[31,leap?29:28,31,30,31,30,31,31,30,31,30,31];
  return year>=1&&month>=1&&month<=12&&day>=1&&day<=days[month-1]&&hour<24&&minute<60&&second<60&&(!m[9]||Number(m[9])<24&&Number(m[10])<60)&&Number.isFinite(Date.parse(value));
 }
 function exact(v,names){return object(v)&&Object.keys(v).length===names.length&&names.every(k=>Object.hasOwn(v,k));}
 function redactorIdentity(v){
  if(!exact(v,['version','sha256','configuration'])||v.version!=='presidio-offline-en/v1'||!hash(v.sha256))return false;
  const c=v.configuration;
  if(!exact(c,['language','python','platform_machine','dependency_records','model_name','model_version','model_manifest_sha256','sources','dependencies','recognizer_configuration_sha256','recognizer_count','analysis_score_threshold','email_suffix_refresh','anonymization']))return false;
  if(c.language!=='en'||typeof c.python!=='string'||!/^[0-9]+\.[0-9]+\.[0-9]+$/.test(c.python)||!['x86_64','aarch64','arm64','AMD64'].includes(c.platform_machine)||c.model_name!=='en_core_web_sm'||c.model_version!=='3.8.0'||!hash(c.model_manifest_sha256)||!hash(c.recognizer_configuration_sha256)||!integer(c.recognizer_count,1,128)||c.analysis_score_threshold!==0||c.email_suffix_refresh!==false||c.anonymization!=='presidio-default-replace')return false;
  if(!exact(c.sources,['app','model_loader','requirements_lock','identity_contract','identity_builder'])||!Object.values(c.sources).every(hash)||!object(c.dependencies)||!object(c.dependency_records))return false;
  const names=Object.keys(c.dependencies);
  return names.length>=1&&names.length<=128&&names.length===Object.keys(c.dependency_records).length&&names.every(k=>/^[A-Za-z0-9_.-]{1,80}$/.test(k)&&typeof c.dependencies[k]==='string'&&/^[0-9][A-Za-z0-9_.+!=-]{0,79}$/.test(c.dependencies[k])&&hash(c.dependency_records[k]));
 }
 function preprocessing(v,models){
  if(!exact(v,['version','sha256','configuration'])||v.version!=='local-text-pipeline/v1'||!hash(v.sha256))return false;
  const c=v.configuration;
  if(!exact(c,['gateway_source_sha256','normalization_source_sha256','normalization_data_sha256','normalization_id','normalization_stages','asserted_rule_tag','rule_floor','procedural_tag','redactor']))return false;
  if(!['gateway_source_sha256','normalization_source_sha256','normalization_data_sha256'].every(k=>hash(c[k]))||c.normalization_id!=='NFC-Unicode-15.0.0/v1'||c.normalization_stages!=='before-redaction-and-before-evaluation'||c.asserted_rule_tag!=='PS'||c.rule_floor!==0.7||c.procedural_tag!=='PII_REDACTED'||!redactorIdentity(c.redactor))return false;
  return models.length>=2&&models.at(-2).name==='presidio-redaction'&&models.at(-2).sha256===c.redactor.sha256&&models.at(-2).revision===c.redactor.version&&models.at(-1).name==='gateway-pipeline'&&models.at(-1).sha256===v.sha256&&models.at(-1).revision===v.version;
 }
 function inspect(a){
  const invalid={status:'invalid',reason:'The local service returned an invalid record.'};
  if(!object(a)||!text(a.assertion_id,36)||!/^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/i.test(a.assertion_id)||!text(a.spec_version,32)||!/^\d+\.\d+\.\d+$/.test(a.spec_version)||Object.keys(a).some(k=>!['assertion_id','spec_version','subject','tags','abstentions','evaluator','signature'].includes(k)))return invalid;
  if(a.spec_version!=='0.1.0')return {status:'unsupported',reason:'This extension does not support that record version.'};
  if(a.signature!==undefined)return {status:'unsupported',reason:'Signed records require a configured verifier; this preview cannot verify them.'};
  const s=a.subject,e=a.evaluator;
  if(!object(s)||Object.keys(s).some(k=>!['sha256','char_len','origin_host','captured_at','modality'].includes(k))||!hash(s.sha256)||!integer(s.char_len)||!text(s.origin_host,253)||!timestamp(s.captured_at))return invalid;
  if(!['text','code','image','audio','video','document'].includes(s.modality))return invalid;
  if(s.modality!=='text')return {status:'unsupported',reason:'This extension currently checks text only.'};
  if(!object(e)||!text(e.calibration_id,256)||!number(e.latency_ms,0,Number.MAX_SAFE_INTEGER)||!array(e.models,16)||!e.models.length||!e.models.every(m=>object(m)&&text(m.name,256)&&hash(m.sha256)&&(m.revision===undefined||text(m.revision,256))))return invalid;
  // Structural metadata consistency only: the gateway/replay tool verifies its digest.
  if(e.preprocessing!==undefined&&!preprocessing(e.preprocessing,e.models))return invalid;
  if(!array(a.tags,2)||!array(a.abstentions,10))return invalid;
  const seen=new Set();
  for(const tag of a.tags){
   if(!object(tag)||!production.has(tag.code)||seen.has(tag.code)||tag.state!=='asserted'||!number(tag.confidence)||tag.floor!==undefined&&(!number(tag.floor)||tag.confidence<tag.floor)||!array(tag.signals,128)||!tag.signals.length)return invalid;
   seen.add(tag.code);
   for(const signal of tag.signals){
    if(!object(signal)||!text(signal.id,160)||!/^[a-z0-9_.]+\.v\d+$/.test(signal.id)||!number(signal.score)||signal.detail!==undefined&&!object(signal.detail))return invalid;
    if(signal.spans!==undefined&&(!array(signal.spans,4096)||!signal.spans.every(p=>array(p,2)&&p.length===2&&integer(p[0],0,s.char_len)&&integer(p[1],0,s.char_len)&&p[0]<p[1])))return invalid;
    if(signal.id==='presidio.entity.v1'&&signal.detail!==undefined){const d=signal.detail;if(!integer(d.count,1)||!array(d.entities,32)||!d.entities.length||!d.entities.every(v=>typeof v==='string'&&/^[A-Z_]{1,64}$/.test(v))||new Set(d.entities).size!==d.entities.length||d.entities.length>d.count)return invalid;}
   }
  }
  const withheld=new Set();
  for(const item of a.abstentions){
   if(!object(item)||!codes.has(item.code)||seen.has(item.code)&&item.code!=='PII_REDACTED'||withheld.has(item.code)||!number(item.confidence)||!reasons.has(item.reason))return invalid;
   withheld.add(item.code);
   // Only PS may assert from the evaluator. PII assertions belong to the redactor.
   if(item.reason==='not_in_production_allowlist'){if(item.floor!==null||item.code==='PS')return invalid;}
   else if(!number(item.floor)||item.reason==='below_floor'&&item.confidence>=item.floor)return invalid;
  }
  return {status:'accepted',result_state:a.tags.length?'FINDING':a.abstentions.length?'UNCERTAIN':'NO_FINDING'};
 }
 globalThis.AITrustContract={inspect,scalarText};
})();
