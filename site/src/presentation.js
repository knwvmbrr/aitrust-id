import {releasePolicy} from './policies.js';
// Plain-language introductions complement the full catalogue; they never change a tag's claim.
const descriptions = {
  PS: ['Flags commands that download code and run it, or execute supported encoded code.', 'This warns about a command pattern. It does not prove a scam. An untagged answer may still be unsafe.'],
  PII_REDACTED: ['Removes detected personal information before the local checker reads your text.', 'It can miss sensitive information. A PII tag does not mean the text is completely private.'],
  NF: ['Will compare a claim with reference material you provide and show supporting passages.', 'Agreement with a reference is not proof that the reference is correct.'],
  FI: ['Will highlight claims that conflict with your reference material and show the disagreement.', 'Missing support alone cannot establish fabrication or dishonesty.'],
  HP: ['Will highlight possible unsupported or inconsistent claims for you to review.', 'Precise wording or an unusual answer alone is not evidence of a hallucination.'],
  MT: ['Will highlight wording that may pressure a reader, with the relevant context.', 'Persuasion or urgency can be legitimate. This tag would not judge someone’s intent.'],
  IV: ['Will record what an independent person checked, along with their evidence and review scope.', 'A reviewer’s signature does not guarantee that every claim is true.'],
  FA: ['Will show positive provenance evidence supporting an AI-generation claim.', 'Missing human evidence or a writing style cannot establish AI origin.'],
  PA: ['Will show evidence of AI contribution and subsequent editing within an observed workflow.', 'It would describe recorded contributions—not judge a person’s identity or integrity.'],
  UNK: ['Will make insufficient evidence clear, rather than invent a verdict.', 'An uncertain result is different from an unavailable or unsupported check.'],
  PII_OUTBOUND: ['Will warn about detected personal information before you send a message to a supported AI service.', 'Detection can miss information. You would stay in control of whether to edit or send.'],
  UC: ['A proposed clearer name for the command-risk findings currently shown as PS.', 'This code is not adopted or issued. Existing PS records keep their meaning.'],
  SC: ['Will research possible scam indicators and explain the context behind each warning.', 'Ordinary requests and news reports can resemble scam patterns. This would not accuse a person of fraud.'],
  BT: ['Will research positive evidence of automation and explain exactly what was observed.', 'Templates, repetition, timing, or missing human activity alone are not proof of a bot.'],
  fleet: ['Will let a team deploy and manage tag tools across its devices.', 'Team policy must preserve each tag’s evidence standard.'],
  host: ['Will connect tag records to supported artifacts on managed devices.', 'Capture needs consent, limited access, and a clearly reviewed boundary.'],
  audit: ['Will keep a versioned record of team findings, reviews, and corrections.', 'Keeping response content requires a separate privacy and retention agreement.'],
  sso: ['Will connect team access to your organization’s identity system.', 'A signed-in user is not proof that a content claim is true.'],
  support: ['Will provide a clear owner for deployment help and maintenance.', 'Support plans and response-time commitments are not available yet.'],
  proprietary: ['Will support organization-specific policies with clear evidence and limits.', 'A private policy must not weaken or misrepresent the public standard.'],
};

export function presentation(tag) {
  const text = descriptions[tag.id];
  if (!text) throw new Error('Missing plain-language introduction: ' + tag.id);
  const working = tag.id === 'PS' || tag.id === 'PII_REDACTED';
  return {
    summary: text[0],
    limit: text[1],
    working,
    stage: tag.id === 'PS' ? 'On-device preview' : working ? 'Local preview' : tag.proposed ? 'Research proposal' : 'Planned',
    validationTitle: working ? 'Validation in progress' : 'Validation required before release',
    releasePolicy,
    validation: working
      ? 'The local workflow has passed development checks. Independent accuracy testing and human accessibility review are still pending.'
      : 'This capability is not available yet. It needs a working method and independent testing before release.',
    access: tag.audience === 'person' ? 'Free for personal use' : 'Proposed paid team offering',
  };
}
