# SynthID vendor-input delivery result

This lane implements the preaccepted F-155 vendor-input software contract, pending
root integration and protected publication. It does not close the original ledger,
issue a tag or verify a Google production watermark. The selected official
research input, personal text and public tag decisions remain separate.

## Functioning outcome

`check-tags.py --tag PS --vendor-input ... --vendor-runtime ...` now executes the
personal checker and an optional fixed SynthID reference worker. The legacy
invocation returns the same personal record as before; the new opt-in envelope
labels the token-ID subject UNBOUND from personal text. SDK/input/import/output
failures cannot redefine the personal tag or suppress its result.

The official source is Google DeepMind SynthID Text0.3.0 at
`6452fbb837d0ad4281ccddb94b0af75d219b1a14`, three unmodified required modules plus
Apache license and research limitations. All40 pinned cached wheel artifacts were
matched to exact official PyPI release hashes/URLs. No model weights or tokenizer
were loaded; no global install or public service changed.

The actual platform was macOS27.2 arm64, CPython3.12.14. A private offline runtime
was installed, used, then removed. Measured allocation856,494,080bytes was below
the accepted0.8GiB cap and left more than2GiB free at installation. After removal,
that runtime directory was absent, the vendor route returned UNAVAILABLE and the
actual PS check still found the supported public synthetic command. Its ordinary
legacy record matched the personal record in the combined result exactly.

## Exact execution and review

- [Current CLI evidence](../runs/2026-11-21-synthid-current-cli.json):15 actual
  cases, including6 whole canonical records compared with separate direct calls
  to the exact official SDK. Cases include genuine official tournament-generated
  synthetic IDs, unmarked IDs, insufficient short/EOS cases, maximum512-ID input,
  another declared public key, private console, personal/default/partial/finding
  exits and malformed/missing SDK input.
- [Install/removal evidence](../runs/2026-11-21-synthid-install-removal-current.json):
  actual install/use/removal,40 versions matching the lock, one selected actual
  SDK call with socket access disabled and zero requests, plus post-removal PS.
- [Focused correction accounting](../runs/2026-11-21-synthid-focused-correction.json):
  original13 focused methods passed after test-fixture correction; after the
  independently reproduced selector-constructor ownership flaw, the3 affected
  worker groups passed. The new14-method file was not broadly rerun merely for
  a count. Current15 CLI cases and6 parity records were regenerated after the fix.
- [Full-contract independent review](../runs/2026-11-21-f155-synthid-full-contract-independent-review.json) found no remaining software acceptance gap for root integration and protected publication. It preserves all tag, production-key and accuracy limits.
- The independent reviewer replayed the real selector-constructor failure and
  normal transport: both passed with no owned child remaining. The original
  defect and first fixture failures remain immutable historical records.
- A later test-only portability change uses resolved regular temporary parents
  and a genuinely SDK-free stdlib venv. Four affected groups passed; runtime and
  worker source bytes stayed unchanged. Guide-only wording distinguishes the
  actual macOS27.2 run from the supported wheel install profile and separates the
 12-second worker deadline from at most5seconds of cleanup. Earlier19-file
  execution snapshots retain their exact earlier test/guide hashes; they are not
  silently rebound to these two non-runtime changes.

## Full recorded contract map

F-155 baseline: actual official SynthID reference computation is delivered as an
explicit vendor input, not a generic unverified-envelope placeholder. The
accepted public research configuration and generated-token scope are declared.
Supported and failure outcomes have actual CLI evidence and exact source identity.
No threshold/tag was introduced; tag-specific decision gates were not invented
or silently waived. Raw p-values are conditional research statistics.

WP-INTEGRATIONS-A01: no blanket truth/origin inference or trusted WATERMARK is
created. A p-value does not decode/resolve a binding to a validated manifest.
A02: actual selected platform install/use/removal and independent outage/import/
worker failure controls are implemented; legacy personal checks survive.
A03: the guide publishes permissions, exact SDK/runtime/config compatibility,
input/hash privacy, resource and support boundaries. No agent-output identity or
benign-intent inference is made. This remains free local software, with no account,
payment, telemetry or compulsory data contribution.

Root must independently accept the full original closure and finish its actual
source registration, protected checks and supported-source publication. No
human/professional judgment, model accuracy, Google production-key access,
broader vendor/media coverage, FA/PA release or global dependency/legal clearance
is claimed. The full original202 criteria and all other tag gates are unchanged.

## Reuse and integration handoff

See [the operator guide](synthid-vendor-input.md). The focused command needs no SDK
installation: `python3 -B -m unittest tests.test_synthid_input -v`.
The actual optional SDK profile is separately installed from the exact offline
lock; the public synthetic fixture and practice generator provide a usable route.

PM source inventory additions: `tools/synthid_input.py`, the three new SynthID
scripts, `integrations/synthid-reference/**`, `tests/test_synthid_input.py`, and
`tests/fixtures/synthid-reference/**`; the existing modified source is
`scripts/check-tags.py`. No shared package, catalogue, route, scope, revalidation
or CI file was changed by this worker. Existing default tag-code enumeration is
unchanged. The optional SDK has been removed to return its disk reservation.
