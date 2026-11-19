# NF selected-source evidence architecture and risks

Before implementation, Codex, 2026-11-19; base
`3716233b9460efa57c1f0d01bfe30989395efcc4`.

## Existing mechanisms and actual gap

`protocol/corpus_support.py` already performs ASCII cosine passage retrieval;
`corpus.query` already finds exact literals. `session_revisions` compares selected
literals against whole captured documents. The NLI selected-pair workflow binds
whole ASCII physical lines and invokes a separately installed model. Reimplementing
retrieval, normalization, or literal matching would duplicate functioning code.

The remaining usable gap is explicit arbitrary NFC claim-to-reference passage
selection without a model, with separate exact-literal and lexical observations.
The caller selects claim and source spans, rather than an automatic line selector
quietly determining context. The workflow does not extract semantic claims or
decide whether the caller selected an honest or adequate context.

## Composition and identity

A new prepare/check CLI reads owner-private UTF-8 subject, corpus-v1 and a closed
pair-selection JSON file. Each of at most eight pairs selects a nonblank claim
span and a nonblank passage span in an attached document. Spans count frozen
Unicode-15 NFC code points. A private sidecar binds original subject bytes, NFC
subject, whole corpus bytes/manifest, original/NFC documents, selected spans and
literal digests, requested checks and exact method sources. Nothing changes
corpus-v1, existing routes, tags, global state or release selectors.

For each pair, construct an explicitly identified corpus-v1 projection of just
the selected normalized passage. Reuse `corpus.query` for exact literal matches
and `corpus_support.observe` for cosine observations. Projection hashes/virtual
offsets remain distinct from original document hashes; validate and rebase all
returned spans into the selected original claim/document boundaries. Never
present a projection hash as the original document's identity. No passage text
leaves the worker or appears in a saved result. Canonical exact matching is
case-sensitive/nonoverlapping and capped at ten matches; a reached cap does not
establish total count. Lexical parameters remain the original method's retrieval
controls, never confidence or an adopted NF gate.

Each explicitly selected check owns a separate bounded subprocess; one failed,
unsupported, saturated or timed-out cosine check cannot erase a valid exact
observation. Unsupported Unicode or multiline lexical input is Unavailable for
that check, not a falsehood finding. No result is prerequisite evidence for the
other check or another tag. Parent validates closed result schemas, identity,
span structure and canonical observations before any private export.

## Privacy, resources and failure

New NF-owned private I/O is adapted with attribution from the audited descriptor
primitive, without importing any FI tag module. Retain no-follow ancestor/file
descriptors, regular/single-link/private/size checks, drift detection, exclusive
0600 final publication, explicit post-link uncertainty, capture-owned raw output
descriptors and exactly-once close attempts. Ordinary pre-publication refusal
means no new final destination; private temporary cleanup can fail. Uncertain
publication means inspect the selected private destination before any retry.
Never promise filesystem rollback or retry a possibly reused descriptor number.

Workers receive only bounded pipe data, not code, paths, prompts in argv or the
whole source corpus. Reuse the existing process-group supervisor with fixed
launcher arguments and a cleared worker environment. Declare an eight-second
wall deadline per check, CPU and output/file-descriptor budgets, and Linux address
space budget. macOS uses its existing deny-network sandbox; Linux uses the
existing system-libseccomp mechanism adapted into the NF worker, with no package
install or model dependency. Required unsupported/failed sandbox setup refuses
that selected check. Exercise socket denial before examining synthetic input;
do not infer a kernel guarantee from source inspection or a mock.

The CLI prints counts and fixed states only. Private sidecars/results contain
linkable IDs, hashes and spans but no subject/source text; export is explicit and
never overwrites. Fixed import/parse/runtime/uncertainty diagnostics disclose no
paths, source IDs, argument values or native stderr. Sources are version identity,
not authenticity; reference freshness and truth remain unestablished. A selected
passage can omit negation, units or qualification; cosine can match opposites,
and an exact quotation can still be false. Shared foundations are prerequisites,
but an absent/broken FI module must not affect NF and a broken NF check must not
affect the existing independent quantitative checker.

## Component acceptance

Execute real selected Unicode/ASCII match and miss, misleading similarity,
rebinding/closed-schema/span/privacy/input/export/refusal controls, isolation,
deadline/output-limit and network-denial controls. Preserve all failed candidates
and immutable receipts. Actual CLI demonstrations run current sources with
synthetic inputs and no package/model downloads. Complete the library, worker,
CLI, guide, focused tests and attributed evidence before commit. Full T-NF remains
open for representative independent claim/passage labels, supported accuracy and
coverage, accepted semantic mapping, source authenticity/freshness and human
route acceptance. This is a complete literal evidence component, not an NF tag.
