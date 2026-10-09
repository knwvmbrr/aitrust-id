# PII_REDACTED — detected redaction procedure

Status: next bounded tag under engineering review, not independently release validated.
Visible code: PII. Protocol code: PII_REDACTED. No taxonomy rename is proposed.

## Job and outcome

Report that the configured local redactor detected supported entity categories
and changed the text before the evaluator received it. Show categories/counts
without publishing their values. This is a procedural tag, not a privacy clearance.
It cannot establish that every sensitive detail was found or that all remaining
text is safe to disclose. Its 1.0 field is a procedural assertion, not calibrated
recognizer accuracy or probability of privacy.

## Architecture and failure containment

The existing local gateway receives original text, NFC-normalizes it, requests
redaction, and validates the category/count/change contract before evaluation.
Only the gateway can issue this tag; evaluator candidates cannot issue it.
Unknown categories, contradictory counts, duplicate categories and reported
detections without a changed subject are invalid upstream results. They stop
affected evaluation with UNAVAILABLE/502, without exporting raw entity strings.
The redactor category allowlist is tied to the inspected English assets; new
recognizer categories require a versioned contract and tests before acceptance.
No new endpoint, persistence or remote upload is introduced.

## Acceptance

- Synthetic email values disappear from evaluator input and assertion output.
- Unicode normalization precedes redaction and subject hashing.
- Valid categories/counts identify what the configured method did, without values.
- Invalid redaction metadata blocks evaluation and issuance.
- Local detector failure is UNAVAILABLE, never “private” or “safe.”
- Method/assets are reproducible; offsets refer to redactor output, not original text.
- The short control explains that sensitive information can remain.
- Independent multilingual/coverage/false-redaction review and human usability
  assessment remain required before any broader detection claim or release.

Ground truth for this procedural tag is the executed transformation and ordering.
Entity recognition quality needs its own independent corpus and error budget.
PS's precision thresholds cannot be copied into this tag as a substitute.

Engineering evidence: tests/test_redaction_contract.py and dated container/CLI
checks. Reviewer-generated examples are development regressions, not a holdout.
