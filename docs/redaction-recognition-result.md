# PII recognition increment — executed 2026-10-11

Codex implemented and tested the complete-IPv6 correction and the independent PII development chart. The dedicated staging stack was rebuilt and all three known staging containers recreated with unchanged gateway/evaluator images and privileges. Production was untouched.

The actual engine processed 42 fixed synthetic examples. In 38 English examples, all 34 expected identifiers were fully masked, with exact type/span counts TP 34, FP 17 and FN 0. Most extra candidates overlap an intended redaction. Two examples actually lost six ordinary characters. Four coverage challenges contain two fully masked, one partially masked and one untouched identifier. These errors remain visible.

Actual current pipeline evidence: 32 HTTP controls, 13 replay controls and 253 authenticated timing requests across 12 profiles. The source-bound service, replay, masking and timing records are preserved separately under runs/. No participant data was used. The report is self-identified source evidence, not remote attestation.

All 1867 current Python checks pass with one upstream TestClient deprecation warning. Focused Node controls passed 53 checks. All five current capability receipts pass; the refreshed route review binds 504 selected files. The website checks catalogue, performance, independent footer workflows, automated accessibility, mobile payloads, feedback preview, offline downloads and security headers against the actual build. These are automated engineering checks, not physical-phone, human accessibility or independently labeled recognition acceptance.

Failures were retained: stale route and browser replay identities, build/changelog sequencing, outdated main-disclosure counting and reading a closed no-script disclosure. Each was diagnosed and corrected; no failed report was overwritten or relabeled passed.

F-023 and T-PII advance from 60% to 80%. The full ledger remains 114 complete and 88 open of 202. The target of 50 open is not met. Independent representative recognition/masking acceptance, remaining extra masking/challenge errors and human operation are still required. No tag taxonomy, release gate, payment, intake or collection endpoint changed.

Source and website publication follow protected review and exact served-artifact verification. This report records completed engineering; it does not claim publication before that verification.

Protected review found a compact-label gap in the first correction. The revised matcher accepts only explicit non-hexadecimal IP/IPv6/addr/address/host field labels, preserving internal address colons and refusing embedded malformed suffixes. Actual rebuilt engine checks fully mask all six additional compact-address examples, but three also lose 12 extra characters. Both fixed development cohorts and their errors are published separately. The revised chain again passes 32 HTTP, 13 replay and 253 timing controls; 175 focused Python and 53 focused Node checks pass. The rejected generic label matcher and original source-bound receipts remain historical evidence. No full requirement is closed by this correction.

Publication verified: protected PR 37 merged as 104b5e347c37a0d5bad464515391087dfdee6947. All 244 artifacts match decoded served bytes on preview, apex and www (732 matches), with the four declared security headers on each index. The primary checkout was fast-forwarded and all 12 unrelated untracked files preserved. See runs/2026-10-11-pii-labels-publication.json and the protected-merge record.
