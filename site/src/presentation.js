import {releasePolicy} from './policies.js';
// Friendly introductions are separate from each tag's complete claim contract.
// Examples describe a use case, never an evaluated result or a release promise.
const descriptions = {
  PS: ['Pause before running a command that downloads and runs code.', 'An AI answer gives you an install command. PS points out supported download-and-run patterns before you use it.', 'A warning is about the command, not proof of a scam. No warning does not mean it is safe.'],
  PII_REDACTED: ['Keep detected personal details out of the local checker.', 'An answer includes an email address. The local service can remove detected values before checking the rest of the text.', 'Some sensitive details can be missed. This tag does not mean all private information is gone.'],
  NF: ['See how an answer lines up with the references you choose.', 'Compare an answer with your handbook and see the passages that support its claims.', 'Planned. A match is only as reliable as the reference; it is not proof of truth.'],
  FI: ['See where an answer disagrees with your references.', 'Compare a claim with your handbook and read the passage that contradicts it.', 'Planned. A disagreement does not prove dishonesty, and the reference could be wrong.'],
  HP: ['Take a closer look at claims that may not hold up.', 'Review a specific claim alongside its supporting evidence, rather than judging how confident the answer sounds.', 'Planned. Confident wording, dates or repetition alone cannot show that a claim was invented.'],
  MT: ['Notice wording that may put pressure on you.', 'Look more closely at an “act now” message and the context around it.', 'Planned. Urgency can be legitimate; this tag would not judge someone’s intent.'],
  IV: ['See what an independent person actually checked.', 'Read a reviewer’s evidence, what they reviewed and what their review did not cover.', 'Planned. A signature records a review; it does not guarantee every claim is true.'],
  FA: ['See evidence that AI generated the content.', 'Inspect a recorded generation event or authenticated content credential tied to the item.', 'Planned. Writing style or missing human evidence cannot prove AI origin.'],
  PA: ['See recorded AI contributions and later edits.', 'Follow a consented record of an AI draft and the editing that happened afterward.', 'Planned. It describes observed contributions, not a person’s identity or integrity.'],
  UNK: ['Know when there is not enough evidence to decide.', 'A check finishes, but the available evidence does not support a conclusion.', 'Planned as a tag. Uncertainty is different from a check that failed or could not run.'],
  PII_OUTBOUND: ['Catch detected personal details before you send a message.', 'Notice an email address in a draft, then choose whether to edit it or send it.', 'Planned. Detection can miss details; the choice to edit or send stays yours.'],
  UC: ['A proposed clearer name for the command warnings in PS.', 'The same bounded command-risk observation could have its own code, without implying a scam.', 'Proposal only. UC is not issued; existing PS records keep their meaning.'],
  SC: ['Explore warnings about possible scam patterns.', 'Review a message asking for an urgent payment, with each possible indicator explained in context.', 'Research proposal. Ordinary requests can look similar; no scam detector is available yet.'],
  BT: ['Explore evidence that a workflow was automated.', 'Review positive, consented observations instead of guessing from someone’s writing style.', 'Research proposal. Repetition, timing, templates or missing human activity alone are not proof of a bot.'],
  fleet: ['Bring tag tools to your team’s devices.', 'An IT team rolls out the same checker without changing what its tags mean.', 'Planned. Managing devices must not weaken a tag’s evidence standard.'],
  host: ['Connect tags to more than a browser answer.', 'With permission, a future agent could bind a tag record to a supported file on a managed device.', 'Planned. No host agent exists; capture needs clear consent and limited access.'],
  audit: ['Keep a clear history of findings and corrections.', 'A team follows which method produced a finding and how a later review changed it.', 'Planned. Keeping a record does not make its finding more certain.'],
  sso: ['Give team members the access they need.', 'Map directory groups to separate permissions for configuration, viewing, review and export.', 'Planned. Signing in does not validate a finding or make author receipts compulsory.'],
  support: ['Get a clear owner for team help and maintenance.', 'A team knows where to ask for deployment help and who owns the agreed follow-up.', 'Planned. Paid support and response-time commitments are not available yet.'],
  proprietary: ['Add your team’s policies without changing the public meaning of a tag.', 'A team could require an extra review while keeping the tag’s evidence and limits visible.', 'Planned. Private rules must not weaken or misrepresent the public standard.'],
};

export function presentation(tag) {
  const text = descriptions[tag.id];
  if (!text) throw new Error('Missing plain-language introduction: ' + tag.id);
  const working = tag.id === 'PS' || tag.id === 'PII_REDACTED';
  return {
    summary: text[0], example: text[1], limit: text[2], working,
    stage: tag.id === 'PS' ? 'On-device preview' : working ? 'Local preview' : tag.proposed ? 'Research proposal' : 'Planned',
    validationTitle: working ? 'Validation in progress' : 'Validation required before release',
    releasePolicy,
    validation: working
      ? 'Development checks pass. Independent accuracy checks and human accessibility review are still ahead.'
      : 'Not available yet. This needs a working method and its own independent checks before release.',
    access: tag.audience === 'person' ? 'Free for personal use' : 'Proposed paid team offering',
  };
}
