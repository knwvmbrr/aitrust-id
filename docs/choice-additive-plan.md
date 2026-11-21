# Distinguish additive “not only A but also B” wording

## Named job and outcome

F-019b/T-MT retains its complete original contextual, error, integration and human
acceptance. This bounded increment gives an actual caller of the existing private
choice CLI and independent MT workflow one additional literal construction:
`not only A but also B`. It reports the two explicitly selected items and exact
paired marker locations as **additive mentions, not exclusive alternatives**.
It never nominates a false-dilemma signal for this form and never issues an MT tag.

## Architecture before implementation

Use the existing corpus-v1/context-v1 packet and frozen NFC selections. Recognize
only whole literal English `not only` immediately before the first selection and
whole `but also` between the two selections; bounded whitespace/comma separators
follow the existing grammar. Require both complete markers. Do not automatically
select clauses, resolve negation scope, infer quotation/endorsement, or judge
whether the caller-nominated passage is relevant or feasible.

Version the research profile from1.2.0 to1.3.0. Existing either/or, only/or,
neither/nor and between/and record fields retain their meanings and values apart
from the declared profile/source identity. New additive rows use
`construction: not_only_but_also`, empty `binary_marker_spans`, two
`additive_marker_spans`, a distinct additive meaning and `proposed_signal: null`.
Their literal `not` location is recorded without interpreting its scope.

The existing CLI separately counts supported additive patterns and keeps the
binary-pattern count zero for additive-only text. Its brief result does not call
the items exclusive choices. The independent MT choice worker projects the two
selected spans and the two additive marker spans; its validator accepts the new
version/construction and its brief distinguishes additive-only and mixed records.
Worker limits, private I/O, explicit exports, no-overwrite behaviour, source
identity, optional-failure isolation and the other MT methods remain unchanged.
The phone preview currently consumes urgency/authority, not choice; no new browser
capability or live tag mapping is introduced by this CLI increment.

Owned implementation: tools/choice_framing.py, tools/mt_workflow.py,
scripts/check-choice-framing.py, scripts/mt-evidence-worker.py, the optional finite
additive example in scripts/prepare-choice-demo.py; affected choice/MT
tests and a new additive test module; this plan, the existing choice guide and
new source-bound evidence/changelog. No scope/state/catalogue/package/workflow
or production publication changes.

## Risks and precise refusal boundaries

“Not only” is additive wording, not a manipulation indicator. Quoted lessons,
menus, legitimate safety text and negated examples can use it. Return literal
spans and all existing uncertainty flags; do not assert intent, exhaustiveness,
truth, independent corroboration or a safe outcome. Reject mixed/incomplete
connectors, embedded-word markers and Unicode case confusables. An unsupported
selection is NO_SUPPORTED_PATTERN, never semantic approval. Invalid/stale packet
bindings and unsafe files remain UNAVAILABLE before output.

## Affected verification after implementation

Exercise actual private CLI and current independent choice consumer with harmless
additive text and each legacy form. Check exact NFC/emoji offsets, additive-only
and mixed counting, explicit private detail output, no overwrite, no subject/path
console echo, invalid bindings, missing/broken choice worker with usable urgency
and recovery. Use finite invented fixtures and current source hashes; preserve
any failed baseline/control records. Run only affected controls, with existing
worker deadlines unchanged. These are authored engineering observations, not
independent accuracy, human acceptance or full original requirement closure.

## Review correction before parser refactor

Distinct review reproduced a construction-only forged worker row: the existing
shape validator accepted an either/or row relabeled as additive and the new brief
then described additive wording. Preserve that failed receipt. Factor the exact
canonical recognizer into one bounded helper inside choice_framing.py, shared by
producer and selected-choice consumer validation. Replay the actual frame and
choice spans; require the exact construction and paired marker spans before a
brief is eligible. Keep the same 2000-character frame, 256-character item and
ordered selection limits. This is one recognizer, not a second grammar.

Only the selected choice validation path lazily loads this helper. A missing or
broken choice parser/worker remains unavailable without invalidating authority
or urgency. No new worker, timeout, corpus format or reference-truth inference is
introduced. Canonical output semantics stay1.3.0; changed source hashes identify
the corrected implementation. Replay only the original forgery, altered markers,
genuine additive and existing four-form positives, then capture new actual CLI
proof. Earlier successful executions remain historical to their exact source.
