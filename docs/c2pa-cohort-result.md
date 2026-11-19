# C2PA selected cohort — result

Codex's C2PA evidence engineering lane completed this bounded increment on
2026-11-19 from `4ae7a14d1738211969bbc9faca041c3afbf03b40` in an isolated branch.

The functioning [offline checker](../scripts/verify-c2pa-cohort.py) covers **10
pinned packages, 14 distinct wheels, 20 selected platform/package slots and 70
retained upstream texts**. All **309 shipped Python-file instances** match their
selected source-distribution paths. Both native C2PA wheel libraries match the
selected upstream release ZIP members, including the existing runtime pins.
No archived package was installed, imported or executed.

Source notices absent from wheel notice selections remain identified as such:
C2PA's Apache/MIT texts, requests' NOTICE and charset-normalizer's data/NOTICE.
Original notice and metadata bytes are retained with artifact/member identities.
Existing native and nested-runtime inventories are unchanged.

Verification: **47 focused tests passed**. Four actual CLI controls passed:
checkout-only verification without replay credit, full private-cache artifact
and source replay, clearance refusal, and refusal of a changed actual wheel.
The [immutable receipt](../runs/2026-11-19-c2pa-cohort-evidence.json) binds exact
sources and preserves the initial collection/test corrections. Archive controls
cover full RECORD consistency, traversal/NUL/duplicate names, links/devices,
encryption, per-member/count/expanded limits, extended-metadata decompression,
missing/altered identities, notice/native omissions and permission promotion.

See [operation and precise boundaries](c2pa-cohort-review.md) and the
[architecture plan](c2pa-cohort-plan.md). Global scope/state/selectors remain unchanged. An attributed standard changelog
entry records this isolated engineering change without changing scope completion.

Still open: resolved Rust/native dependency and notice coverage, incorporated
OpenSSL/libffi and other components, source offers and release packaging,
unselected Python/platform alternatives, publisher authentication and
reproducible native builds. Cargo.lock returned 404 at the release source commit;
the full source archive exceeded the retrieval bound and was not retained.
Matching source/artifact bytes do not settle these obligations. No X-02/F-057
full closure, permission clearance, production activation, tag accuracy or
release approval is claimed.
