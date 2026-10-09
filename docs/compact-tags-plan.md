# Compact in-use tags — implementation plan

The extension renders a small row of code-only buttons below each captured response.
It does not insert a bordered warning card, persistent prose, or permanent action
buttons into the conversation. Issued PS and PII records remain individually
selectable. Pending, unavailable, unsupported and no-finding states use compact
status markers with accessible names; none implies a safety certification.

Selecting a tag opens a brief explanation in a native HTML dialog in the browser top layer.
This keeps detail out of document flow. Native dialog focus containment, Escape,
backdrop dismissal, a close button and return-to-trigger behavior make it operable
without hover. Recheck moves inside the dialog. Evidence remains inserted as text;
subject/source hashes, scores, offsets and redaction metadata are preserved in a
structured local download. Claim limits remain in the brief; full definitions and
testing information stay in the website catalogue. No response text is exported.
A changed response closes stale evidence before refreshing its compact controls.

Risks: hidden failures, false all-clear wording, loss of evidence, stale open
records, keyboard traps, closed-shadow accessibility and mobile overflow. Verify
compact resting geometry, no layout shift on dialog opening, each tag selection,
status explanations, native keyboard dismissal, stale-result behavior, injection,
320px reflow, and the installed extension on the existing live conversation.
No evaluator, gateway, tag-policy or website catalogue behavior changes are needed.

Multiple-tag refinement: keep the row in normal flow beneath the complete output,
including output ending in inline text. Wrap at narrow widths; never position tags
over text or code. Render every distinct supplied tag, rather than reserving two
button slots. Verify an isolated many-tag renderer fixture, per-code detail
selection, unchanged output text/geometry, and narrow-width wrapping. This does
not enable additional detector codes in the production contract.
