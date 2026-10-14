# Independent tag operation — current result

Codex · 2026-10-14. The target is **45 open full requirements**. This increment
starts and remains at **124 complete / 78 open**, preserving all 202 records.
Stronger operation and tests are not invented scope closures or tag releases.

## Implemented and exercised

- The complete local service has three reserved slots; privacy-only work has one.
  Saturation cannot borrow the other's capacity. Success, failures, disconnects
  and cancellation return the selected slot.
- Privacy readiness and `doctor --privacy` do not require PS. The container probe
  stays ready while the privacy route is usable. The default complete-pipeline
  readiness contract still withholds readiness for a failed dependency.
- `check-ps.py` runs the exact frozen PS method in a separate process without
  gateway, redactor, token or third-party Python imports. It performs no redaction.
  All 86 current authored regressions match: 31 finding / 55 no-finding cases.
- `check-tags.py` runs explicitly selected PS/privacy checks independently, emits
  brief results as they finish and preserves separate evidence records. A failed
  checker import, crash or timeout does not discard its sibling's valid result.
  Partial results have exit 3, never a successful check of every requested tag.
- Every tag package now requires standalone operation and its own failure,
  saturation and recovery acceptance. Unbuilt packages remain unavailable.

## Actual Linux evidence

The new owned Podman installation passed ten clean-setup controls, 26 complete
service checks, 15 replay checks, 16 privacy checks and eight isolation checks.
The evaluator was actually paused with the full queue occupied; privacy and its
owner doctor still worked. The redactor was actually stopped; privacy withheld
its result while standalone PS still found the supported pattern. All owned
services recovered with their identities and configuration preserved.

Four actual multi-tag scenarios passed: both findings; privacy unavailable;
PS worker crash; PS worker timeout. The faulted checker source was restored.
PS and privacy subject hashes differed as expected; their spans were not merged.
Fresh timing covers 12 profiles and 253 requests to the current full pipeline.
This measures speed on declared Linux hardware, not independent accuracy.

The original staging services were restored unchanged. Tests touched newly owned
synthetic setups, without changing PostgreSQL, Caddy, backup or production
configuration. No local Docker was started and no real content was collected.

## Retained failures and remaining limits

Three private driver errors are recorded: an omitted import path, an unbound state
variable and an interpreter lacking the required assertion format checker. The
final reusable verifier checks schema readiness and ownership before mutation;
its actual Linux execution passed. An early standalone validator listed obsolete
signal suffixes; current suffixes were corrected before its successful regression
and failure checks. These errors are not erased or counted as successful runs.

Independent PS/PII accuracy, real humans, physical phones and the 12 planned or
proposed personal tags remain open. Queue isolation cannot guarantee survival of
an entire compromised or exhausted host. Required service redaction is never
bypassed. The legacy combined assertion remains a complete-pipeline contract;
independent multi-tag use preserves separate records instead of pretending a
partial combined assertion was valid.

Current browser and full-suite receipts will be listed in state after execution.
[Architecture](tag-failure-isolation-plan.md) · [Usage](open-validation-path.md)
· [Actual Linux isolation](../runs/2026-10-14-tag-isolation-real-linux.json)
· [Actual multi-tag checks](../runs/2026-10-14-tag-isolation-batch-linux.json)
· [Standalone method parity](../runs/2026-10-14-standalone-ps-regressions.json).
