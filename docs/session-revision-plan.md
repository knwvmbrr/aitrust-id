# Next independent component: selected revision context

Architecture before implementation, 2026-10-12. F-029a remains an unvalidated
structural hypothesis; missing captured text cannot establish human authorship,
AI authorship, outside knowledge or semantic non-derivability. Build an offline
owner-controlled comparison of explicitly selected, normalized text spans in a
new revision against the previous revision and an existing hash-bound local
corpus selected as captured context. Reuse corpus parsing, frozen normalization
and descriptor-based private-file access. No automatic capture, new endpoint,
model, inference or tag mapping. No new taxonomy or scope record.

For each selected span, record whether that exact normalized literal occurred
in the previous revision and its first exact location per context document.
Hash both revisions, the captured manifest and selected span contract. Case,
paraphrase, arithmetic and inference remain uninterpreted. Context completeness
and its declared origin are unauthenticated. Absence means only that the selected
literal was not located in the supplied captured texts. Results are private by
default; the console shows counts, never text, source IDs, spans or hashes.

Private inputs stay outside the checkout with owner-only permissions. Strict
closed JSON fields, exact integer spans, no overlap/duplicates, digest binding,
UTF-8 and byte/character/count limits. Unknown fields or altered selections
refuse. Optional details create a new private directory without overwriting.
Bound methods and normalization data; source changes require fresh checks.

Risks: overinterpreting literal absence, incomplete capture, normalization
offsets, malicious input depth, filesystem races and copied private evidence.
Tests must include paraphrases and derived arithmetic as counterexamples to a
knowledge claim, repeated material, composed Unicode, stale selection hashes,
unsupported private input and summary leakage. Human context validation and
any future PA/FA integration remain separate full-job gates.

Preparation also binds owner-selected NFC codepoint spans to the two drafts and
the supplied context, without requiring the owner to compute hashes manually.
The spans remain explicitly selected; preparation adds no inference or capture.
