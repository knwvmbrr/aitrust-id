# Reference claim coverage result

Codex NF/FI evidence lane, 2026-11-18. Base revision
`7b5ab10df9c91a4134d0d655c315b13df890e422`.

The automatic reference checker now accounts for every supported nonempty input
line. Its private output records each line's normalized span, the indices of its
model observations and an explicit evaluated or unevaluated state. The public
summary gives counts. The coverage map has its own version and source hash.

An invented two-line subject matched two reference passages. With the global
maximum set to one, the base revision produced one model row and no coverage
map. The coverage postcondition failed. The current code makes the same one
controlled backend call and records one evaluated line and one unevaluated line.
It does not infer which omission reason applied or run an additional comparison.

The actual private CLI also ran with two unrelated invented lines. It returned
coverage for both, with zero evaluated lines, two unevaluated lines and no model
invocation. Its explicit details file had mode 0600. Reusing the output folder
refused without changing the file. A corrupted reference refused before creating
new details. The summary exposed no text, hashes, spans or private paths.

The summary validates the map against the exact captured subject and observation
rows before export. It rejects rebound identities, omitted units, changed spans,
duplicate or incorrect indices, unexpected fields and JSON type substitutions.
A historical record without a map remains readable with coverage unavailable.
Summaries lacking the original subject also keep coverage unavailable. A known
coverage map requires its recorded producer version to reproduce it.

## Execution evidence

- 228 focused controls passed in 1.84 seconds, covering the new map and existing
  automatic, caller-selected, worker-output, private-file and review-window paths.
- Three actual current-source CLI controls passed without loading a model.
- The old-source and new-source controlled mapping calls each evaluated one pair.
- The first candidate test run had 224 passes and one failure because a new legacy
  summary fixture omitted the existing `network_control` field. The fixture was
  corrected. The failure is retained in the execution record.

The controlled backend scores test mapping behavior. This increment performs no
real model inference or independent accuracy study. Coverage counts input lines
with an output from one model. A line can contain multiple semantic claims, and
unretrieved evidence can remain outside the selected pairs.

NF and FI still need accepted support/contradiction semantics, representative
independent labels, calibration, source authenticity/freshness handling and human
acceptance. This change closes no original parent requirement. The standing
scope stays in the integration owner's ledger.

[Execution record](../runs/2026-11-18-reference-claim-coverage.json) ·
[User guide](nli-references.md) · [Architecture plan](reference-claim-coverage-plan.md).
