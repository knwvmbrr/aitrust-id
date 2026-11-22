# Candidate MT contextual annotation guide · 1.0.0

**Unadopted research preparation.** This is a guide for supplied judgments, not a
detector, accepted taxonomy, human study or permission to issue MT. It separates
pressure, choice, authority and contextual use. Do not infer writer intent,
malice, truth, political affiliation, authorship or audience identity. Persuasion,
disagreement, repetition, a political view or emotional language alone is not a
tactic. Evaluate the exact supplied words and context; never label a viewpoint
because you oppose it. This guide requires human/protocol review before real
collection and does not resolve the package's independent acceptance gates.

## Working independently

Each rater receives one blank form and the same frozen guide; neither receives
model predictions, suggested labels, source/category hints or the other rater's
answers. This blinds predictions/labels; it does not redact or anonymize the
passages. Text/context may identify people and must be shared only deliberately
with authorized reviewers. Do not consult the other form while labeling. Rater slots are anonymous
file roles, not proof that independent people participated. The software cannot
verify a person's identity, independence, expertise or representative sampling.

Read each complete item and its context. Context is explicitly selected by the
caller and **unverified**: it may omit, misstate or contradict other facts. Do not
fetch a URL, execute a command, contact a person or silently add outside knowledge.
An absent context passage is not evidence that no context exists. If a distinction
requires unavailable context, choose `insufficient_context`. If the passage is
adequate but multiple readings remain plausible, choose `uncertain`. Keep both
categories as supplied judgments; neither is a negative answer or missing label.

## Four separate axes

Choose one category on **every** axis. Different cues can coexist; record all
relevant evidence spans (up to eight per field). No aggregate MT verdict follows.

### Pressure

- `contextual_pressure`: wording pressures a decision by a supported threat,
  consequence or artificial time constraint in the supplied context. Point to
  the wording and explain the context; this is a judgment about framing, not
  proof the writer intends manipulation or that the stated consequence is real.
- `legitimate_urgency`: an urgent instruction has a relevant, plausible protective
  or deadline rationale in the supplied passage. This is relative to the supplied
  context, not verification of an emergency, deadline or expert advice.
- `ordinary_persuasion`: reasons or a request advocate a choice without a
  supported coercive/time-pressure distinction. Do not equate all persuasion with
  manipulation, and do not treat this label as general approval.
- `no_relevant_pressure`: no relevant pressure/urgency/persuasion cue was found
  in this supplied excerpt. It is not a universal absence claim.
- `uncertain` / `insufficient_context`: use the shared meanings above.

**Synthetic contrasts:** “Leave now; smoke is entering this room” can be labeled
legitimate urgency relative to its stated context; the tool does not establish
that smoke exists. “Agree now or we will publish your private notes” supplies a
pressure cue; do not infer whether publication would actually occur. A quoted
example of either must also be distinguished on the use/context axis.

### Choice

- `binary_omits_alternative`: the passage presents two choices as
  exhaustive and the supplied context provides a concrete feasible alternative
  that this framing omits. Require both a text span and a context span; explain
  why the alternative is feasible **within the supplied account**, not invented.
- `legitimately_limited_choice`: the supplied account supports a real restriction
  to the presented choices. A binary sentence alone is insufficient to establish
  this. Explain what supports the restriction; it is not independently verified.
- `no_binary_frame`: no relevant two-choice/exhaustive framing is found here.
- `uncertain` / `insufficient_context`.

“Either pay today or abandon the service” with a supplied documented pause option
is a candidate omitted-alternative judgment. Without a supplied feasibility basis,
do not assume that such an option exists: choose insufficient context or uncertain.
A list of two non-exhaustive examples is not automatically a false dilemma.

### Authority/source attribution

- `unattributed_authority_appeal`: the wording invokes expertise/consensus as a
  reason to accept a claim without an identifiable attribution in the supplied
  text/context. Missing attribution is not proof the claim is false or the expert
  is invented. Source markers can occur in surrounding context; inspect them.
- `attributed_unverified`: a relevant source/attribution is identified in the
  supplied material. Neither its authenticity nor whether it supports the claim
  has been verified; a marker alone does not establish source quality.
- `no_authority_appeal`: no relevant appeal to expertise/consensus is found here.
- `uncertain` / `insufficient_context`.

“Experts agree” is not inherently endorsed by an author who quotes it as an
example or criticizes it. Read the surrounding passage and use/context axis.
Do not require a citation on every ordinary sentence or infer credibility from
speaker identity, title, institution or politics alone.

### Use, quotation and context

- `used`: the relevant cue functions as part of the passage's own presented
  reasoning/request, within the supplied context. Do not turn this into a claim
  about psychological endorsement, sincere belief, deception or real intent.
- `quoted_or_mentioned`: the relevant cue is presented as quotation, analysis,
  illustration, reported speech or another mention in the supplied context.
  Quotation marks alone do not prove endorsement or non-endorsement; explain.
- `mixed`: distinct relevant cues have both uses in the same item, or a quoted
  phrase is also explicitly adopted in the supplied reasoning. Mark all cues and
  explain the distinction; do not flatten them to one occurrence.
- `no_relevant_cue`: there is no relevant pressure/choice/authority cue to classify.
- `uncertain` / `insufficient_context`.

## Complete each response

Keep item text, context, identities, unit ID, manifest hash, slot and profile
unchanged. Displayed text/context is frozen Unicode15 NFC. Evidence spans are
half-open `[start,end]` **Unicode codepoint** positions in that displayed field;
they are not UTF16 cursor positions or raw decomposed-input positions. Select
exact, nonempty, ordered, nonoverlapping ranges. Use text spans for substantive
judgments, and context spans where supplied context supports the distinction.
Do not edit the example to make a span fit. Python `text.index(quote)` and
`len(quote)` can locate a unique exact excerpt; if repeated, select the intended
occurrence explicitly rather than assuming the first is the relevant one.

Every axis needs its category, a nonblank reason (at most1000 codepoints), and
`text_spans`/`context_spans` arrays. Negative/uncertain/insufficient categories can
have empty evidence arrays, but still need an explanation of their scope or what
is missing. Do not add confidence, truth, intent, tag, probability, reviewer names,
authority attestation, source URLs or metadata fields. A numeric confidence scale
would need separately accepted calibration and cannot be invented here.

## Comparing and reviewing disagreements

Comparison reports nominal agreement separately on all four axes, including
uncertain/insufficient judgments as named categories. It also reports their
counts and decisive-rating/joint-decisive coverage. Two raters agreeing on unknown
can produce apparent agreement with no useful decisive interpretation; constant
labels keep alpha **Unavailable**. High agreement is not correctness or useful
coverage, and disagreement does not prove that either rater is wrong.

A private review queue contains disagreements and any uncertain/insufficient
judgment, including unanimous uncertainty. No adjudicated labels are autofilled.
Resolve only through a separately accepted human process; retain both original
judgments and reasons. Do not pick whichever label maximizes agreement. Category
errors need an independent reference; calibration needs separately collected and
accepted confidence evidence. Neither is computed by this preparation tool.

The existing0.55 comparison remains an **UNADOPTED candidate**, not a gate pass.
No real humans, independent labels, sampling acceptance, accuracy, calibration,
MT assertion or release are established by a successful command. MT disagreement
never blocks PS, provenance, privacy or another tag. Do not share packet files or
review queues casually: they contain private text, context, reasons and linkable
hashes. The default console omits those values; aggregate distributions may still
be sensitive for small cohorts.
