// Bundled public assets only. Native arguments carry input as data, never URLs/code.
const reasons={
 'sig.piped_installer.v4':'Downloads code and passes it straight to a shell to run.',
 'sig.remote_command_substitution.v4':'Puts downloaded output into a command that runs it.',
 'sig.remote_process_substitution.v4':'Hands downloaded code to a shell to run.',
 'sig.remote_backtick_substitution.v3':'Inserts downloaded output into a command that runs it.',
 'sig.obfuscated_payload.v3':'Passes encoded content to eval or exec, which can run code.'
};
const notify=state=>window.webkit.messageHandlers.lifecycle.postMessage({state});
const moduleLoader=String.raw`
import hashlib as _aitrust_hashlib, zipfile as _aitrust_zipfile
with _aitrust_zipfile.ZipFile('/tmp/aitrust-detector-source.zip') as _aitrust_archive:
    _aitrust_members = _aitrust_archive.infolist()
    if len(_aitrust_members) != 1 or _aitrust_archive.comment:
        raise ValueError('Module archive refused')
    _aitrust_member = _aitrust_members[0]
    if (_aitrust_member.filename != 'method.py' or _aitrust_member.header_offset != 0
            or _aitrust_member.flag_bits != 0 or _aitrust_member.extra
            or _aitrust_member.compress_type != _aitrust_zipfile.ZIP_STORED
            or not 0 < _aitrust_member.file_size <= 200_000
            or _aitrust_member.compress_size != _aitrust_member.file_size
            or (_aitrust_member.external_attr >> 16) != 0o100644):
        raise ValueError('Module member refused')
    _aitrust_source = _aitrust_archive.read(_aitrust_member)
if _aitrust_hashlib.sha256(_aitrust_source).hexdigest() != _aitrust_expected_source:
    raise ValueError('Module identity differs')
exec(compile(_aitrust_source.decode('utf-8', errors='strict'), 'aitrust-bundled-method.py', 'exec'), globals())
del _aitrust_source, _aitrust_archive, _aitrust_members, _aitrust_member, _aitrust_hashlib, _aitrust_zipfile
`;
try {
 const response=await fetch('./device-manifest.json');if(!response.ok)throw Error('Unavailable');
 const manifest=await response.json();
 const {loadPyodide}=await import('./runtime/pyodide.mjs');
 const py=await loadPyodide({indexURL:new URL('./runtime/',location.href).href,stdout:()=>{},stderr:()=>{}});
 if(!/^[a-f0-9]{64}$/.test(manifest.bundle_sha256))throw Error('Unavailable');
 const source=await fetch('./detector-source.zip');if(!source.ok)throw Error('Unavailable');
 const archive=new Uint8Array(await source.arrayBuffer());
 if(!archive.length||archive.length>200_256)throw Error('Unavailable');
 py.FS.writeFile('/tmp/aitrust-detector-source.zip',archive);
 py.globals.set('_aitrust_expected_source',manifest.bundle_sha256);
 try {py.runPython(moduleLoader);} finally {
  py.FS.unlink('/tmp/aitrust-detector-source.zip');
  py.globals.delete('_aitrust_expected_source');
 }
 const check=py.globals.get('check_device'),normalize=py.globals.get('normalize_nfc');
 window.checkAnswer=text=>{
  if(typeof text!=='string'||!text.trim()||Array.from(text).length>manifest.max_codepoints)throw Error('Invalid input');
  const value=JSON.parse(check(text)),chars=Array.from(normalize(text));
  if(value.format!=='ai-trust-id-device-preview/v1'||!['FINDING','NO_FINDING'].includes(value.state)||
     value.subject?.normalization!==manifest.normalization_id||value.subject?.codepoint_count!==chars.length||
     value.models?.[0]?.sha256!==manifest.method_sha256||!Array.isArray(value.candidates))throw Error('Invalid result');
  const matches=[];
  for(const candidate of value.candidates){
   if(candidate.code!=='PS'||!Array.isArray(candidate.signals)||!candidate.signals.length)throw Error('Unsupported result');
   for(const signal of candidate.signals){
    if(!Object.hasOwn(reasons,signal.id)||!Array.isArray(signal.spans)||!signal.spans.length)throw Error('Unsupported signal');
    for(const span of signal.spans){
     if(!Array.isArray(span)||span.length!==2||!span.every(Number.isSafeInteger)||span[0]<0||span[0]>=span[1]||span[1]>chars.length)throw Error('Invalid span');
     if(matches.length<10)matches.push({reason:reasons[signal.id],excerpt:chars.slice(span[0],Math.min(span[1],span[0]+320)).join(''),truncated:span[1]-span[0]>320});
    }
   }
  }
  if((value.state==='FINDING')!==Boolean(value.candidates.length))throw Error('Inconsistent result');
  return {format:'ai-trust-id-native-summary/v1',state:value.state,method_sha256:manifest.method_sha256,
   normalization_id:manifest.normalization_id,matches,independently_validated:false,redaction_performed:false};
 };
 notify('ready');
} catch {notify('unavailable');}
