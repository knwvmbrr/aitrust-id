# Accessibility

Accessibility is a release gate here, not a backlog item. A trust label that only some people
can read is not a trust label.

## Commitments

1. **Never color alone.** Labels are monochrome and distinguished by letter, shape, and text.
   This satisfies WCAG 2.2 SC 1.4.1 by construction rather than by remediation.
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
an account restriction. **The gate fails on any serious or critical axe violation.** Manual NVDA and VoiceOver passes are required before any
release tagged `minor` or larger, and the results are recorded in the release notes.

## Reporting

Accessibility bugs are filed as `type:a11y` and treated as defects at the same severity as a
security bug, not as enhancements.
