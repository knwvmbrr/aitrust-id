# Open queue target: 187 → 100

The original 202 requirement IDs remain intact: **102 completed, 100 open**.
Starting from 15 complete and 187 open, this closes 87 functioning named jobs.
The timestamped [ledger](scope-progress.md) retains completion credit, evidence
and each remaining fix/owner. Packages and subtasks are not silently promoted.

This increment closes fourteen independently named component requirements:

| Records | Functioning outcome | Evidence boundary |
|---|---|---|
| F-026, F-027, F-028, F-029b, F-029c, F-082 | Opt-in offline editor measures coarse timing, revision churn, caret entropy, focus/edit intervals and paste events; suppresses unsuitable timing | No authorship, identity, attention or provenance tag inference. Actual engines, not physical phones or human reviewers. |
| F-017 | Literal repeated n-grams with exact normalized spans, configuration and source identity | Intentional repetition is allowed; no hallucination conclusion. |
| F-053 | Versioned HP/MT/FI development fixtures with file identities, provenance and non-emission controls | 36 synthetic scenarios, not independently labeled accuracy or a release holdout. |
| F-008 | Detached assertion signatures verified under an explicitly pinned key, with mandatory assertion-schema validation | No automatic gateway signing or badge trust change. F-036 remains open. |
| F-121, F-122, F-123 | Optional free receipt issuance binds exact artifact bytes to observed editing; verification runs offline | Signature integrity and artifact matching do not establish identity, human authorship or truth. |
| F-127 | Mandatory observation-forgery class on each receipt; unsupported/inflated values refused | Current class is honestly `unvalidated`, not a structural-security assertion. |
| F-131 | Explicit Ed25519/P-256 dispatch, expiry windows and unsupported-algorithm refusal | Revocation is unchecked; no independent timestamp, permanent safety or post-quantum claim. |

The [editor guide](composition-observations.md) and [receipt guide](offline-receipts.md)
provide executable instructions. The site build produces a directly downloadable
standalone editor and a plain-language offline-tools reference page. No account,
subscription, backend endpoint or training upload is added.

Executed controls: 57 Node tests and 48 selected Python tests, with source hashes
in [the component report](../runs/2026-10-10-offline-final-controls.json).
Actual Chromium and WebKit each execute typing, editing, suppression, summary/text
downloads and export-to-receipt issuance/verification. They also prove reset
cancels a pending export, CSP blocks network access, and no storage writes or
automated accessibility violations occur on the tested editor. See the
[integration report](../runs/2026-10-10-offline-final-editor-receipt.json).
The full Python suite passed 873 tests, including the 29 reviewed-boundary controls.
The suite was rerun after correcting the signal-registry test fixture
to include its newly declared reference-source dependencies.

A clean Linux install exposed conflicting PyYAML pins (gateway 6.0.3, evaluation
6.0.2). They are reconciled to the existing hash-locked gateway version. Actual
merged installation and `pip check` succeeded on the dedicated Linux test host;
the dependency verifier now rejects conflicting shared pins. Hosted GitHub
Actions execution remains unverified and is not credited as complete.

RFC-0002 and proposed PA/FA mappings remain unadopted. Independent timestamps,
revocation transparency/freshness, friendly key recovery, group receipts,
institutional conformance and independent tag validation remain open. The
existing PS preview's precision lower-bound gate is still unmet. Nothing in
this increment fabricates reviewers, operating legal entities or released tags.

The final current-source Python suite passed 873 tests. The fresh reviewed
route guard and rebuilt website checks passed. See
[final Python evidence](../runs/2026-10-10-target-100-final-python.json) and
[reviewed boundaries](../runs/2026-10-10-target-100-final-reviewed-boundaries.json).
Committed source `7f25f0558902f408eb25ee65efcafee341140c24` is public on GitHub
and deployed. All 175 artifacts matched across the preview, aitrustid.com and
www.aitrustid.com (525 comparisons). Live checks passed all 20 modals, nine
policy pages and the native editor download, which matches the tested artifact.
An initial page mismatch immediately after deployment was retained as a failed
attempt; the repeated complete comparison passed.

[Publication evidence](../runs/2026-10-10-target-100-deployment.json) distinguishes
the deployed source from this subsequent evidence-recording commit.
[Use the offline tools](https://aitrustid.com/reference/offline-tools/).
