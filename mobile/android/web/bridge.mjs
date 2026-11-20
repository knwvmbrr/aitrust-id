// Only hash-verified APK assets. Selected text is data, never a program or URL.
const reasons = Object.freeze({
 'sig.piped_installer.v4':'Downloads code and passes it straight to a shell to run.',
 'sig.remote_command_substitution.v4':'Puts downloaded output into a command that runs it.',
 'sig.remote_process_substitution.v4':'Hands downloaded code to a shell to run.',
 'sig.remote_backtick_substitution.v3':'Inserts downloaded output into a command that runs it.',
 'sig.obfuscated_payload.v3':'Passes encoded content to eval or exec, which can run code.'
});
window.AndroidPS={state:'booting'};
try {
 const manifestResponse=await fetch('./device-manifest.json');
 if(!manifestResponse.ok)throw Error('Unavailable');
 const manifest=await manifestResponse.json();
 const {loadPyodide}=await import('./runtime/pyodide.mjs');
 const py=await loadPyodide({indexURL:new URL('./runtime/',location.href).href,stdout:()=>{},stderr:()=>{}});
 const response=await fetch('./method.py'); if(!response.ok)throw Error('Unavailable');
 py.runPython(new TextDecoder('utf-8',{fatal:true}).decode(await response.arrayBuffer()));
 const check=py.globals.get('check_device'), normalize=py.globals.get('normalize_nfc');
 window.AndroidPS={state:'ready',check(text){
  if(typeof text!=='string'||!text.trim()||Array.from(text).length>manifest.max_codepoints)throw Error('Unsupported input');
  const value=JSON.parse(check(text)), chars=Array.from(normalize(text));
  if(value.format!=='ai-trust-id-device-preview/v1'||!['FINDING','NO_FINDING'].includes(value.state)||
    value.subject?.normalization!==manifest.normalization_id||value.subject?.codepoint_count!==chars.length||
    value.models?.[0]?.sha256!==manifest.method_sha256||!Array.isArray(value.candidates))throw Error('Unsupported result');
  const matches=[];
  for(const candidate of value.candidates){
   if(candidate.code!=='PS'||!Array.isArray(candidate.signals)||!candidate.signals.length)throw Error('Unsupported candidate');
   for(const signal of candidate.signals){
    if(!Object.hasOwn(reasons,signal.id)||!Array.isArray(signal.spans)||!signal.spans.length)throw Error('Unsupported signal');
    for(const span of signal.spans){
     if(!Array.isArray(span)||span.length!==2||!span.every(Number.isSafeInteger)||span[0]<0||span[0]>=span[1]||span[1]>chars.length)throw Error('Unsupported span');
     if(matches.length<10)matches.push({reason:reasons[signal.id],excerpt:chars.slice(span[0],Math.min(span[1],span[0]+320)).join(''),truncated:span[1]-span[0]>320});
    }
   }
  }
  if((value.state==='FINDING')!==Boolean(value.candidates.length)||Boolean(matches.length)!==Boolean(value.candidates.length))throw Error('Inconsistent result');
  return {format:'ai-trust-id-android-summary/v1',state:value.state,method_sha256:manifest.method_sha256,normalization_id:manifest.normalization_id,matches,independently_validated:false,redaction_performed:false};
 }};
} catch {window.AndroidPS={state:'unavailable'};}
