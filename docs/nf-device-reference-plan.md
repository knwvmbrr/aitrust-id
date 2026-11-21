# NF selected-reference device preview — architecture before implementation

Base `2aa67779352fa11c303867f52799172ec73ee07c`. This is an optional software preview under T-NF/F-020a, not an NF tag, semantic support verifier, original closure or independent accuracy study.

## Complete bounded job

A person explicitly pastes one claim and one selected reference passage, chooses exact words or word overlap, and runs that one check locally. Short results distinguish a completed no-match from Unavailable. Full method/identity/position details are opt-in. No automatic extraction, search, account, send, persistence or new endpoint.

Reuse unchanged `protocol.corpus.query` and `protocol.corpus_support.observe` (ASCII cosine1.0.0, fixed0.75 threshold/max10), plus frozen Unicode15NFC. The new adapter creates an explicit one-document corpus projection of the complete selected passage and returns the canonical original record. Both original UTF8 bytes and normalized text are hash/length-bound separately; source positions refer only to the selected passage. Limits: each input2000 raw/NFC codepoints,8000 UTF8 bytes, bounded output256KiB. No truncation. Multiline claims are permitted by the canonical cosine unit rule, not silently collapsed.

## Independence and failure design

Each explicit invocation owns a new Worker, its load/check deadlines and termination. Fixed literal/cosine bundle selection happens before private text is sent. Literal source/payload/validator does not import the cosine method or validator; cosine assets are loaded only when explicitly selected. Missing/corrupt optional assets, unsupported characters, deadline, malformed or mismatched records yield only that selected check's Unavailable. Editing either input, changing selection, clear, cancel and unmount invalidate generation and terminate work. Existing CLI and other tag sources remain unchanged.

Builder captures/rechecks exact source/license/normalizer files without importing captured Python, stages bounded outputs, publishes hash-addressed payloads before active manifest, and uses the established reviewed no-follow/descriptor-owned builder pattern. Publication is staged replacement, not a filesystem transaction or crash-atomic guarantee. Every selected source and complete original record is closed-type validated before render; JS independently replays exact literal or capped cosine rows, including counts and span identities. Hashes prove source identity, not authenticity or truth.

## Risks and required proof

Word resemblance can be high for a contradiction: 'Water is safe.' vs 'Water is not safe.' gives cosine0.866025403784. UI must say similar words can disagree and never use 'supported', 'verified', confidence, true/false or a combined verdict. Literal can support Unicode when cosine is unavailable; no-finding is not a truth result. Reference freshness/accuracy remain unestablished. Private details may reveal matched words, hashes and spans; keep them hidden until chosen and never log/export automatically.

Before integration: focused adapter/builder/strict validator and client lifecycle controls; full canonical native/browser record parity in sequential Chromium/WebKit; both input tampering; omitted/forged numeric rows; malformed/oversize/unknown source; negation; optional payload/validator failure then literal, real PS and MT recovery; input edit/clear/cancel/unmount and stale results; requests/storage/console privacy;320px/200percent light/dark and44px controls. Distinct reviewer. PM alone owns shared mount/preparation/package/CI/fingerprints, protected checks and actual live publication. Physical-phone, human accessibility and independent NF release remain separate open gates.
