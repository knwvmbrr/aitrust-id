# Keep PAN candidate evidence inside its own span

The pinned Presidio 2.2.355 PAN Low pattern uses lookaheads that can find a
letter or four consecutive digits after the ten-character candidate ends.
Actual isolated recognizer execution returns IN_PAN for `ip_address` when a
four-digit IPv6 group follows, and for ten digits when a later word supplies
the letter. Neither candidate contains the evidence required by its pattern.

Replace only the PAN recognizer with a subclass that requires both existing
lookahead conditions inside each emitted PAN span. Retain upstream patterns,
scores, offsets, context, thresholds and all other entity categories. Preserve
high/medium PAN shapes and the existing low-confidence OCR/punctuation shapes;
do not whitelist field names or turn off the low-confidence recognizer.

Risks are losing uncertain identifiers, altering recognizer identity, and
reporting a diagnostic override as a deployed service. Test both lookahead
directions, boundaries, adjacent identifiers, scores and forwarded NLP inputs.
Run the real pinned recognizer, then unchanged fixed English and compact cohorts
through a source-current isolated engine. Preserve the earlier observations.
Obtain source-current service/replay and setup acceptance before selecting new
public evidence. Keep local Docker, production inputs and research collection
out of this increment. No endpoint, dependency, language or tag-release change.

This addresses a known development false positive. PII independent representative
recognition, out-of-coverage misses, human acceptance and privacy limits remain
open. N-013 and the independent PS checker do not depend on this correction.

## Executed results

The nine-case pinned-recognizer diagnostic preserves high, medium and low
positive shapes and removes three demonstrated candidates that borrowed their
evidence. Its initial adjacent-token expected offset was wrong; the failed
diagnostic is retained, with unchanged input/code and the corrected literal
offset in the subsequent run.

The complete source-current isolated Linux engine then processed the unchanged
42 English/challenge and six compact-address examples. The compact cohort still
masks all six expected addresses, with zero extra masked characters instead of
ten. English observations are byte-equivalent at the row/measurement level,
including two examples with six extra masked characters. The four out-of-coverage
challenges still include one partially masked and one untouched identifier.

The actual three-service route passed 26 controls and 15 private replay cases.
The clean Linux clone passed its ten setup/ownership/failure controls. Twelve
declared-host timing profiles were measured separately; no latency budget or
population accuracy is inferred. The original staging configuration was restored
and owned test resources removed. No Mac Docker or real user data was used.

[Engine](../runs/2026-11-09-pan-english-linux.json) ·
[Compact addresses](../runs/2026-11-09-pan-compact-linux.json) ·
[Service](../runs/2026-11-09-pan-service-linux.json) ·
[Replay](../runs/2026-11-09-pan-replay-linux.json) ·
[Clean setup](../runs/2026-11-09-pan-clean-setup-linux.json) ·
[Timing](../runs/2026-11-09-pan-pipeline-timing-linux.json)
