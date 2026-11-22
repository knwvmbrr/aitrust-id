# C2PA native graph handoff

Completed source-only engineering on November21/22,2026 in
`codex/c2pa-native-source-graph` from40d85dfabcd6a3d97b84977992d0523b0995c0d9.
The original F-057/X-02 criteria, old C2PA cohort and all tag routes are unchanged.

The functioning machine graph contains441 packages,1,131 resolved published-lock
edges and2,518 distinct retained source/license/declaration texts (8,639,460bytes).
All441 official archive checksums were retrieved and replayed; the private source
cache is approximately67MiB, with2GiB free reserve preserved. No code installation,
Cargo build, native execution, model download or Docker operation occurred.

The discovered published FFI Cargo.lock is distinct from the actual404 Git URL.
The source-bound parser checks its fixed SHA256, every qualified dependency edge,
source/notice identities and false approval flags. Both previously pinned native
libraries yield135 matching sanitized source-version labels, all present in that
lock. Labels are explicitly positive/non-exhaustive; the exact compiled closure,
features, system dependencies, build identity and distribution obligations remain
unresolved. No fabricated complete-native/reproducibility or legal clearance.

Sixteen initial notice-filename omissions were investigated. Actual AUTHORS
license terms in two crates and separate exact-commit upstream license texts for
11 others are retained with honest provenance. Three projects provide actual
README/Cargo license declarations but no root license text at the pinned commit;
no missing notice or permission is invented. Source supplements never pretend
to be shipped crate members.

[Actual five CLI controls](../runs/2026-11-22-c2pa-native-current-cli.json) passed:
checkout-only consistency, full441-archive and two-native-wheel label replay,
changed actual archive, unknown retained source and private malformed argument
refusals. All eight exact execution-source bindings remained stable. The initial
11 focused methods yielded10 passes and one fixture error expecting ValueError
instead of correct OSError; [the three affected corrected controls](../runs/2026-11-22-c2pa-native-focused-correction.json)
passed in1.441seconds. No unchanged broad suite was rerun.

[Different-agent review](../runs/2026-11-22-c2pa-native-distinct-review.json) checked
all current bindings and independently executed only the checkout verifier:
441/1,131/2,518 passed with no fresh-cache replay credit. It found no actionable
blocker in this bounded graph scope. No broad native build, all-platform or
original completion claim follows.

The distribution graph owner can import
`tools.c2pa_native_obligations.verify(root=Path(...))`; it validates retained files
sequentially without holding thousands of descriptors. Nodes and edges are in
`sbom/c2pa-native/manifest.json`; raw source texts, native label observations and
source-notice provenance are beside it. The owning graph consumer must preserve
all false clearance/complete-native flags and exact source bindings. This worker
did not edit a shared consumer, inventory, ledger, state, package or CI file.

See [operations, limits and primary sources](c2pa-native-obligations.md) and the
[preimplementation architecture](c2pa-native-obligations-plan.md).
