import { normalizeNFC, NORMALIZATION_ID } from '../../protocol/normalization.mjs';
// Explain only reviewed PS signals. No inference, execution, uploads or logging.
const reasons={
 'sig.piped_installer.v3':'Downloads code and passes it straight to a shell to run.',
 'sig.remote_command_substitution.v3':'Puts downloaded output into a command that runs it.',
 'sig.remote_process_substitution.v3':'Hands downloaded code to a shell to run.',
 'sig.remote_backtick_substitution.v2':'Inserts downloaded output into a command that runs it.',
 'sig.obfuscated_payload.v2':'Passes encoded content to eval or exec, which can run code.'
};
export function explainPS(record,text){
 if(typeof text!=='string'||record?.format!=='ai-trust-id-device-preview/v1'||!['FINDING','NO_FINDING'].includes(record.state)||!Array.isArray(record.candidates))throw Error('Invalid PS result');
 if(record.subject?.normalization!==NORMALIZATION_ID)throw Error('Normalization identity mismatch');
 const chars=Array.from(normalizeNFC(text));
 if(record.subject?.codepoint_count!==chars.length)throw Error('Input binding mismatch');
 const matches=[];
 for(const candidate of record.candidates){
  if(candidate.code!=='PS'||!Array.isArray(candidate.signals)||!candidate.signals.length)throw Error('Unsupported candidate');
  for(const signal of candidate.signals){
   if(!Object.hasOwn(reasons,signal.id)||!Array.isArray(signal.spans)||!signal.spans.length)throw Error('Unreviewed signal');
   for(const span of signal.spans){
    if(!Array.isArray(span)||span.length!==2||!span.every(Number.isSafeInteger)||span[0]<0||span[1]<=span[0]||span[1]>chars.length)throw Error('Invalid evidence positions');
    const length=span[1]-span[0];
    matches.push({id:signal.id,reason:reasons[signal.id],excerpt:chars.slice(span[0],Math.min(span[1],span[0]+320)).join(''),truncated:length>320});
   }
  }
 }
 if((record.state==='FINDING')!==Boolean(matches.length))throw Error('State/evidence mismatch');
 return {
  title:matches.length?'PS · Command-risk pattern found':'No supported pattern found',
  checked:'PS checked only download-and-run command patterns and supported encoded-code execution.',
  meaning:matches.length?'The matched parts below explain why PS flagged this answer. This is a pattern warning, not proof of a scam or malicious intent.':'PS found none of its supported command patterns. It did not check the answer for truth, scams, authorship or every possible danger.',
  next:matches.length?'Review this command before using it. Verify the source and ask someone you trust if anything is unclear.':'Do not treat this as “safe” or “verified.” Check any important claims or instructions separately.',
  matches:matches.slice(0,10),total_matches:matches.length
 };
}
