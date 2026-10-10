# Accessibility

Accessibility is a release gate here, not a backlog item. A trust label that only some people
can read is not a trust label.

## Commitments

1. **Never color alone.** Labels are monochrome and distinguished by letter, shape, and text.
   This is the design requirement; conformance depends on executed checks and manual review.
2. **Every label has a descriptive accessible name.** PS is announced as a command-risk
   finding; the visible tile remains code-only. Heuristic scores must not be announced
   as calibrated probability. Unsupported HP is not an operating capability.
3. **Keyboard complete.** Every badge and evidence panel is reachable and operable by keyboard
   with a visible focus indicator. Escape returns focus to the badge that opened the panel.
4. **We do not hijack the page.** Badges are appended after the response and announced with
   `aria-live="polite"`, never `assertive`. A blind user reading a model's answer is not
   interrupted mid-sentence by our label.
5. **Contrast.** Text meets WCAG AA at minimum, AAA where practical. `forced-colors` (Windows
   High Contrast) is supported and tested, not merely unbroken.
6. **Motion.** `prefers-reduced-motion` removes all non-essential animation.
7. **Zoom and reflow.** Usable at 200% zoom and at 320 CSS px width, per SC 1.4.10.

## Testing gate

The executable `npm run verify:axe-gate` checks the actual badge/panel fixture
and proves that an injected serious/critical accessibility defect fails. The
configured CI job calls the same gate; hosted execution is currently blocked by
an account restriction. **The gate fails on any serious or critical axe violation.** The separate `npm run verify:release-a11y` gate requires source-bound engineering receipts and actual NVDA and VoiceOver reviews of both website and extension before a validated product release. Missing or stale evidence fails. [Review instructions](docs/accessibility-release-gate.md) describe the inputs and limits. A development catalogue is not a validated product release.

## Reporting

Accessibility bugs are filed as `type:a11y` and treated as defects at the same severity as a
security bug, not as enhancements.
