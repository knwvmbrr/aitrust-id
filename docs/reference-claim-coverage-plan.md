# Reference NLI claim coverage

Codex NF/FI evidence lane, 2026-11-18. Base `7b5ab10df9c91a4134d0d655c315b13df890e422`.

## Job and observed gap

The automatic reference checker accepts up to 32 nonempty claim lines and
selects at most five reference/claim pairs across the whole subject. Its output
currently records evaluated pairs only. With two matching claims and maximum 1,
one claim has a model observation and the second has no coverage entry. The
actual no-match CLI likewise reports zero passages without accounting for each
supplied claim unit. This increment makes that omission inspectable.

## Architecture

Reuse the existing normalized line segmentation and the final observation rows.
Add a `reference-claim-coverage/1.0.0` object to automatic-route detailed output.
Every normalized nonempty trimmed line has its exact span, the indices of its
model observations and an explicit `observed_model_outputs` or `not_evaluated`
state. Validate that every observation maps to one actual claim and that each
index is accounted for exactly once. Include the coverage source identity.

The existing result profile remains compatible. Summary output adds coverage
availability and counts. The summary reconstructs the map from the captured subject before export.
Historical results without the supplemental object, and summaries without that
original subject, have unknown coverage. The caller-selected one-line route retains its existing scope.

## Risks and limits

A model output for one reference does not establish the claim, all references,
contextual adequacy, calibration or NF/FI release. The output must not guess
whether an omitted line missed the lexical threshold or lost to the global cap.
Blank lines do not become claims. Repeated text on different lines remains
separate through exact normalized spans. Counts must not expose text, source IDs,
positions, hashes or private paths on the console.

This is bookkeeping over the existing comparisons. Pair selection, model
execution, resource/deadline/network controls and privacy rules stay on the
current path. A malformed coverage record must refuse safely. No added retrieval
or model calls are needed to describe coverage.

## Verification

Retain the two actual before cases. Add focused controls for mixed coverage,
zero matches, repeated lines, multiple references for one claim, CRLF/blank lines,
coverage source and type integrity, unavailable historical coverage and the
private CLI. Run the affected reference, selection and review-window consumers
once after implementation. Use controlled scores to test evidence mapping and
label them as injected. A real CLI no-match result exercises coverage without
model assets. Actual model inference is outside this increment.
