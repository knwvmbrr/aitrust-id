# Stable identity for one unordered recognizer capability field

This plan is recorded before feature code. ROOT approved the exact seven-file
implementation from proposal `1111f5141941ffdad430dc073f2b2646bb813e6874602b80adcaced28c893ccc`
under review `e23f610a5c113186d6352f29ea60135486d5693d382674985bc6033b325b6546`.
No new model run, source deployment or task closure is approved by this plan.

## Observed problem and primary evidence

The genuine existing gateway/redactor/replay run passed eight bounded controls
with five real redactor calls and two sequential model starts. Its same-process
record reproduced, but a fresh same-source process returned Unavailable because
the full recognizer-configuration digest differed. Raw receipt
`cb47fb7f02e9f321c6daaa2b6898b3092761541bb0c724b56fc452fa63f5105c` and different
actual review `3a1d7fef46f8aee2afb7384cc906a2af5d2f3c36218143a5d1ce80d50235609e`
remain unchanged. The harness did not sort, seed or force a match.

A read-only inspection retrieved exactly four installed public Python files,
31,545 bytes total, from the exact existing image. No Presidio/model import or
service mutation occurred. The package version stores SpacyRecognizer at the flat
`predefined_recognizers/spacy_recognizer.py` path; an earlier missing nested-path
read is preserved, and metadata-only diagnosis identified the actual path.
The successful primary-source receipt is
`22051a8e9324f978576b26d0f01eaffc1ac0479d134bafb55ae5b95a2cf9126f`.

- `SpacyNlpEngine.get_supported_entities` returns a list made from a set of
  entity-mapping values. That capability order varies across interpreter processes.
- The registry passes this list directly to SpacyRecognizer. EntityRecognizer's
  serializer returns it unchanged. Its exact installed method matches the source
  captured during the genuine run.
- SpacyRecognizer iterates ordered NLP artifacts and uses supported_entities only
  for membership filtering. The actual two diagnostics differ only in this one
  nine-value capability-list permutation; all other records and method definitions
  match.

## Narrow correction

In `services/anonymizer/replay_metadata.py`, copy each existing serialized record
into a new dictionary. For the concrete pinned
`presidio_analyzer.predefined_recognizers.spacy_recognizer.SpacyRecognizer` class
only, represent `supported_entities` as a new sorted list. Require an ordinary
nonempty list of at most 128 unique ordinary strings matching
`[A-Z][A-Z0-9_]{0,79}`. Duplicate, missing, invalid, oversized or non-string values
refuse; they are never silently deduplicated.

Never mutate the analyzer, recognizer or original capability list. Preserve all
other fields and ordering, including patterns, contexts, deny lists, NLP artifacts,
registry order and the existing name/language sort. Other recognizer classes do
not acquire an unproved set-order exception merely by using a matching display
name. This is identity serialization, not a detector change.

The wire envelope stays the same. The builder's source SHA changes automatically,
so old assertions remain unchanged and the current replay validator returns
Unavailable for historical/different method sources. No old proof is rebound.

## Exact owned files

- `services/anonymizer/replay_metadata.py`
- `tests/test_redactor_capability_identity.py`
- `docs/pii-capability-identity-plan.md`
- `docs/pii-capability-identity-result.md`
- `runs/2026-11-25-pii-capability-identity-source.json`
- `runs/changes/2026-11-25-pii-capability-identity-source.json`
- `CHANGELOG.md`

## Verification and release gates

Use the already installed verification environment for focused permutation,
membership-change, ordered-field, invalid-input, no-mutation and class-selector
controls, plus the existing old-source replay refusal control. Inert test records
are not actual model evidence. No broad recognition cohort is rerun for this
identity-only change.

A different source review precedes a separately approved two-source overlay of the
actual app and changed identity builder. That later genuine run must establish
stable fresh-process identity and replay with unchanged source/model/cleanup
limits. The old app-only harness cannot qualify the new builder. ROOT owns task
closure and scope accounting; full PII acceptance remains 80%, independent
recognition/human acceptance remain open, and the 66-open original count is not
changed by this plan.
