# Compare with your reference — on your device

Paste a **claim** and the **reference passage** you choose. Select one check, then
press **Compare passages**. No account, installed service, input upload or saving.
The first run fetches the existing on-device Python runtime and selected source
bundle. Keep the page open while it loads. This is an NF method preview, not an NF
tag or a factual verdict.

- **Exact words:** case-sensitive frozen Unicode15NFC matches, first10 nonoverlapping
  occurrences. Different words or no match do not mean falsehood. Canonically
  equivalent Unicode can match; original bytes remain separately identified.
- **Word overlap:** unchanged ASCII cosine1.0.0, threshold0.75/max10. One claim per
  nonblank input line, up to32. Reference lines with unsupported characters are
  counted and skipped; no usable reference lines makes this check Unavailable.
  A score is resemblance, never confidence or proof of support.

**Similar words can disagree.** `Water is safe.` and `Water is not safe.` produce
no exact-word match but similar-word resemblance0.866025403784. Negation, source
accuracy, freshness, context and semantic entailment are not decided here. Only
these selected inputs are checked; no source search or automatic claim selection.

Each input is limited to2000 raw and normalized Unicode codepoints and8000UTF8
bytes. Nothing is clipped. Unsupported or failed checks say Unavailable, not zero
findings. Exact words and Word overlap own separate payloads and validations: a
failed overlap check does not prevent a new exact-word check. Other tags use their
own routes. Each run uses a fresh worker (load45seconds, check6seconds), terminated
after completion/cancellation. Changing either input or selection, clearing,
cancelling or closing the preview removes the prior result. This clears page
state, not a claim of forensic memory erasure or browser clipboard deletion.

**Method and exact positions** opens details only when chosen. They contain
matching words, hashes and normalized character positions that may reveal or link
text. Nothing is exported automatically. Positions refer to your selected claim
and passage, not an external document. The projected corpus and raw original input
identities are separate. Checksums and replay establish record consistency, not
source authenticity, reviewer independence or true claims.

The pure device adapter calls unchanged `protocol.corpus.query` or
`protocol.corpus_support.observe` and preserves its full original result. Browser
validation checks both rawUTF8/frozenNFC identities and replays the bounded
canonical rows before display. The existing private CPython workflow, corpus
importer, CLI, tag mapping and source methods are unchanged.

Emulated Chromium/WebKit checks are engineering evidence. Real-phone, human
accessibility and independent semantic support/accuracy validation remain open.
Full T-NF/F-020a acceptance and all other original scope requirements are preserved.
