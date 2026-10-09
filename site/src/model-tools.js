import {allTags} from './catalog.js';

// Optional browser capability. These read only the same public records as the UI.
export function registerPublicTagTools(doc=document) {
  const context=doc.modelContext;
  if(typeof context?.registerTool!=='function')return ()=>{};
  const lifecycle=new AbortController();
  const validate=(input,allowed)=>{
    if(!input||typeof input!=='object'||Array.isArray(input)||Object.keys(input).some(key=>!allowed.includes(key)))throw new Error('Invalid tool input');
  };
  const tools=[{
    name:'list_ai_trust_id_tags',title:'List AI TRUST ID tags',
    description:'Read the public tag catalogue and development status. This does not evaluate content, certify tags, or submit a report.',
    inputSchema:{type:'object',properties:{audience:{type:'string',enum:['person','enterprise']}},additionalProperties:false},
    annotations:{readOnlyHint:true,untrustedContentHint:false},
    execute(input){validate(input,['audience']);if(input.audience!==undefined&&!['person','enterprise'].includes(input.audience))throw new Error('Unknown audience');return allTags.filter(tag=>!input.audience||tag.audience===input.audience).map(({id,code,name,audience,status,proposed})=>({id,code,name,audience,status,proposed,releaseValidated:false}));},
  },{
    name:'get_ai_trust_id_tag_details',title:'Read AI TRUST ID tag details',
    description:'Read one public tag or organization offering, including its claim, evidence, limitations and release requirements. This does not run a detector or issue a tag.',
    inputSchema:{type:'object',properties:{id:{type:'string',enum:allTags.map(tag=>tag.id)}},required:['id'],additionalProperties:false},
    annotations:{readOnlyHint:true,untrustedContentHint:false},
    execute(input){validate(input,['id']);const tag=allTags.find(tag=>tag.id===input.id);if(!tag)throw new Error('Unknown tag');return structuredClone({...tag,releaseValidated:false});},
  }];
  for(const tool of tools){try{Promise.resolve(context.registerTool(tool,{signal:lifecycle.signal})).catch(()=>{});}catch{/* Optional support must not break the visible catalogue. */}}
  return ()=>lifecycle.abort();
}
