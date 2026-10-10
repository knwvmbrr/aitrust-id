# Accessibility release gate

`npm run verify:release-a11y` is an executable refusal gate for a validated
product release. It supplements the statistical gate, never approves a tag's
accuracy, and does not block publication of the explicitly labelled development
catalogue. Current manual reviews are absent: running it today must fail.

Run `scripts/revalidate.py website`
and `scripts/revalidate.py extension` with separate `--output` JSON paths. Website revalidation first builds current source and starts its own temporary server, so an old preview cannot supply a passing check. These
run the existing browser and extension tests, then bind the complete source,
fixture, dependency and check inventory. Pass those paths with
`--website-receipt` and `--extension-receipt` to the release gate. A changed file,
added file, failed command or missing receipt blocks the gate.

Two assistive technologies, NVDA and VoiceOver, must each be exercised on the
website and the extension by actual people. A reviewer-approved public account
belongs under `docs/manual-accessibility/`, using synthetic content, with no
private conversations, credentials or identifying disability details. Obtain
permission for the reviewer's public label. Store a separate JSON review record:

- `kind`: `human_accessibility_review`; `engineering_fixture`: false;
  `human_performed`: true; `reviewer_public_label` and
  `reviewer_publication_consent`: true.
- `surface`: website or extension; `technology`: NVDA or VoiceOver;
  `environment`: operating system/browser/assistive-technology versions;
  `performed_at`: observed timezone-aware date; `fingerprint`: the current
  `revalidate --fingerprint` SHA-256; `account`: approved relative Markdown path.
- `tasks`: navigate, read_tag, open_details, close_restore_focus,
  errors_and_status and zoom_reflow, each with result `pass` after fixes.
  `unresolved_issues`: an empty array only when that review has no open defects.

Pass a JSON object with a `reviews` array using `--reviews`. The default release paths are `docs/manual-accessibility/reviews.json`, `eval/release/website-accessibility.json` and `eval/release/extension-accessibility.json`; none is seeded as a pass. No manual review is
seeded as a pass. AI-generated or automated fixture records are rejected. Unit
tests exercise hypothetical documents in temporary directories; they are not
real accessibility reviews and do not enter the published review directory.

These records are reviewer attestations. The gate cannot prove that a person
performed a task or prevent a malicious owner from fabricating documents. The
accountable maintainer verifies review provenance before release. Passing these
bounded tasks is still not a completed VPAT/ACR or full WCAG conformance.
