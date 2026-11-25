# PII capability identity: source handoff

The metadata builder now copies and sorts only the pinned SpacyRecognizer's
set-derived `supported_entities` field. It rejects invalid or duplicate values
and leaves the analyzer, original list, patterns, contexts and other recognizer
records unchanged. This changes configuration identity serialization, not what
the detector recognizes or masks.

Eleven focused controls pass, covering the observed nine-entity permutations,
real membership changes, ordered-field changes, invalid input, no mutation,
class selection and the unchanged wire envelope. The unchanged replay validator
also inspected the genuine earlier assertion against the new builder source and
returned `Unavailable: historical_or_different_pipeline_sources` before any HTTP
call. The old assertion remains untouched.

The earlier genuine live run passed eight controls with five real redactor calls
and two model starts, but did **not** reproduce across processes: the capability
order changed its identity. That record remains historical evidence of the defect,
not a passing execution of this new builder. No seed, analyzer mutation, generic
list sort or identity override is used to hide it.

A different source review and a fresh two-source overlay of the actual app and new
builder are still required before claiming stable restart/replay. The new source
has not rebuilt or replaced the installed service. PII remains at 80% full
acceptance; representative recognition, human acceptance and current source
admission are separate gates. This handoff closes no original requirement.

See the [pre-code plan](pii-capability-identity-plan.md) and
[source record](../runs/2026-11-25-pii-capability-identity-source.json).

## Actual two-source replay — 2026-11-25T07:45:36.853734+00:00

The subsequent source-reviewed run used the real gateway and redactor with the
current bracket-address app and corrected metadata builder. All eight controls
passed with five real redactor calls and two sequential fresh processes. The full
identity stayed equal, and the original assertion replayed as `Matched` after
restart. Each process verified all 29 model assets before loading.

The temporary container, both source overlays and owned SSH process were removed;
staging metadata and all source hashes stayed unchanged. A different reviewer
verified the actual result. The earlier failed restart and the source-only
records above remain historical evidence and were not rewritten.

This is an engineering replay fix. It does not change detector accuracy, deploy
the builder, validate the whole tag or close an original scope requirement. PII
remains at 80% full acceptance; the original queue remains 66 open.

[Actual source-bound record](../runs/2026-11-25-pii-bracket-address-live-replay.json).
