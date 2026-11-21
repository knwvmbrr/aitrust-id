# Advisory PS review-to-prediction join

The existing freeze/compare workflow protects a selected execution recipe and
reports human-label disagreement. It does not turn explicit adjudication into
per-item predictions. The existing evaluation harness accepts aggregate results
but does not attest reviewer independence. This tool fills only that local join.

Before implementation: validate complete JSON reviewer returns using the existing
v2 comparison and capture fixed private packet members. Bind explicit decisions
for every item to the exact manifest, execution recipe and both returned forms.
Preparation creates blank decisions, never labels. Execution preserves all source
files and rejects missing decisions, changed inputs and stale execution recipes.

Each supported item runs the unchanged evaluator `signals(Doc(...))` after frozen
NFC in a fresh bounded child. Input is data, never executed or fetched. Enforce
20,000 codepoints/80,000 UTF-8 bytes per item, 1,000 items, a 60-second cohort
budget, 10-second children and bounded output. Unknown/failed evaluation refuses
the complete export instead of becoming a negative label. Explicit adjudicated
ambiguity remains visible outside binary denominators.

Export a new owner-private folder with an existing-harness-shaped aggregate and
private item evidence. Every independence/sampling/release claim stays false;
dataset kind is advisory, no calibration pairs are fabricated. The current gate
must refuse this report for release. Console output contains fixed counts only.

Risks: packet hashes do not attest people or chronology; same-UID hostile users
can rewrite files. Capture and recheck bytes before export. Bound imports and
worker output; never accept child spans, scores or source identities unchecked.
Private export must not overwrite a prior folder or follow links. Diagnostics
must not expose text, reasons, source addresses, item IDs or paths. This is the
selected offline Python route, not a gateway, browser or whole-host attestation.

Owned files: new module, CLI, focused tests, this plan, usage guide and immutable
execution evidence. Existing freeze/compare, evaluator, harness, policy, UI,
scope and state remain unchanged. No dependency installation, collection,
network request, signature policy or human acceptance is supplied by this work.

Verification: synthetic completed forms only; positive/negative/ambiguous joined
records, disagreement without decision, input/source drift, malformed/private
I/O, bounded worker failure, original preservation and harness release refusal.
Actual CLI commands must exercise preparation and execution with the installed
reviewed interpreter. No independent labels or full original closure claimed.
