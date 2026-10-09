// Allowlist public method identity and result state. Never spread an input-derived record.
export function shareSummary(record,manifest){
 if(!['FINDING','NO_FINDING'].includes(record?.state)||!/^[a-f0-9]{64}$/.test(manifest?.method_sha256||''))throw Error('Invalid summary source');
 return {
  format:'ai-trust-id-share-summary/v1',tag:'PS',state:record.state,
  method_sha256:manifest.method_sha256,
  stage:'development_preview',independently_validated:false,training_label:null,
  text_included:false,subject_identifier_included:false,evidence_positions_included:false,
  detail_reference:'https://aitrustid.com/tags/ps/'
 };
}
