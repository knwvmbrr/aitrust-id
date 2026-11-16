# NF/FI evidence increment: compare the reference pair you choose

Codex NF/FI evidence lane · 2026-11-16 · `codex/selected-reference-pairs`.
Base: integration `85b885f`. No original scope or completion count changed.

## Functioning result

A person can now prepare a private, hash-bound selection of one claim line and
one reference line, then compare that exact pair through the existing pinned,
network-denied NLI worker. The new path does not require its chosen pair to clear
the automatic lexical retrieval threshold. It reports that retrieval was **not**
evaluated and invents no retrieval score.

The existing default automatic route, profile and thresholds are preserved. The
new selection module is loaded only when requested: a missing or syntactically
invalid optional module returns a fixed Unavailable on that selected route and
cannot stop the default retrieval route merely by being absent.

Selection binds original/NFC claim identity, corpus identity, raw/NFC reference
identity, physical line numbers and recomputed trimmed spans, plus a canonical
selection digest. Changed claims, corpora, spans or controls refuse before the
model. The console omits text, paths, source IDs, hashes and positions. Explicit
private details retain selection/model/evidence identity with the existing
permission and no-overwrite controls. No account, endpoint, model download,
collection or new tag code is added.

## Actual before and after

For the invented reference `The room is empty.` and claim
`There are people in the room.`:

- The unchanged default selector does not choose a pair at 0.75. No model output
  is fabricated for that unperformed comparison.
- Explicit selection of the two lines reaches the same already cached model.
  The final current-source CLI completes in **2.353 seconds**, returns the model's
  `contradiction` label and preserves all three scores and its actual identity.
- It still reports no truth, source freshness, independent corroboration, tag
  assertion or release approval. The known model error on an unrelated sky/books
  pair remains; this increment fixes chosen-pair reachability, not model accuracy.

The original selected-route candidate also completed an invented exact-match pair
with an `entailment` label. That observation belongs to its earlier source hash;
it is retained historically and is not represented as final-source execution.

## Verification and retained failure

- Initial candidate: **251 adjacent controls passed in 1.89 seconds**, plus eight
  actual standard-library/private-file CLI controls and two real, serial model
  calls. These receipts remain at their exact original source identities.
- Self-review identified avoidable startup coupling to the optional module. The
  first lazy-load candidate collided with an existing local variable: the module
  variable `selected` was overwritten by the validated worker-pair list. Four
  controls failed with an AttributeError; 162 passed. The failed source/XML hashes
  and root cause are retained. This was a candidate regression, not a platform or
  model failure.
- Renaming the module variable to `selected_contract` resolves that precise
  collision. **166 affected controls pass in 1.61 seconds**, including import
  refusal isolation, default behavior, strict bindings, worker-result validation,
  deadlines/cleanup, private exports and pre/post review-window guards.
- Three fresh real no-model CLI controls pass at final source. One separately
  scheduled final-source real model call passes with the original pinned-assets,
  runtime-identity, deny-network and resource controls. Exact source inventories
  remain unchanged across those executions. No retry or asset download occurred.
- Metadata/lock/notice profile verification also passes; those declarations are
  not license clearance or a substitute for the worker's real cache checks.

[Final aggregate evidence](../runs/2026-11-16-selected-reference-pair.json) ·
[Final-source real model](../runs/2026-11-16-selected-reference-isolated-model-macos.json) ·
[Final-source actual CLI](../runs/2026-11-16-selected-reference-isolated-cli-macos.json) ·
[Retained failed candidate](../runs/2026-11-16-selected-reference-isolation-refusal.json).

No broad suite, Linux inference, browser/native build or physical-device test was
performed in this lane. Controlled worker outputs in the focused tests are
explicitly injected test values; the actual-model receipt is separate. All
examples are invented engineering controls, not independent accuracy evidence.

## Scope contribution

| Original record | Before | After | Remaining outcome |
| --- | --- | --- | --- |
| F-020b corpus contradiction/NLI | 60% | 60% | Representative source selection, contextual/temporal errors, calibration, accepted signal/tag mapping and human acceptance |
| T-NF | 20% | 20% | Claim/source-support contract, authenticated/fresh evidence, independent error study and complete tag integration |
| T-FI | 20% | 20% | Distinct contradiction/resolution-failure semantics, independent error study and complete tag integration |

The original ledger remains **202 records: 132 complete, 70 open**. A useful
separate selected-pair subcomponent does not close its parent tags. A caller may
cherry-pick evidence; one chosen pair does not cover omitted claims or references.
A checksum is not source authenticity. Declared review windows are not freshness.
The method remains limited to the published ASCII selected-line profile and
existing model limits; unsupported/failed input is Unavailable, never a falsehood
verdict. Historical Linux receipts are not relabeled current by this change.

[Use the working route](selected-reference-comparison.md) ·
[Architecture and risks](selected-reference-pair-plan.md).


## Cross-review repair: cyclic output path

A separate engineering reviewer reproduced a private-path traceback when the output path was a self-referential symlink on supported Python3.12. The preparer now includes RuntimeError in its bounded refusal handling. Two focused private-output tests and a real CLI reproduction pass: exit2 with fixed Unavailable, no traceback/path echo, no overwrite, and unchanged inputs/symlink. The failed case is retained. The comparison CLI, selected-pair module, model/cache/network controls and deadlines are unchanged; earlier model evidence is preserved at its original source inventory, not rehashed to this preparer. No model rerun or parent requirement closure is claimed.
