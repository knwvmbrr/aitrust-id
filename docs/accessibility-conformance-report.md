# Accessibility evaluation record

Date: 2026-10-09. Reviewer/implementation: Codex. Claude's fixture-based draft is
preserved privately; its intermediate provenance panel is not the product UI.
This is a bounded automated test record, **not a completed VPAT/ACR or a claim of
full WCAG conformance**. It describes the existing website and PS device checker,
not an implemented provenance detector, operating certification program or every
embedding page used by the extension.

## Reproduce

```sh
npm run build:site
python3 -m http.server 5174 --bind 127.0.0.1 --directory site/dist
# In another terminal:
npm run verify:a11y-probes
npm run verify:site
npm run verify:site-a11y
```

The new probes check actual catalogue and tag dialogs, the eight independent
footer workflows, and PS input/result screens in light and dark at 320 CSS px.
They exercise keyboard disclosure with reduced motion, control focus indicators
and obstruction, text-spacing overrides, touch target size/spacing, and
forced-color reflow. Existing verify:site covers axe, keyboard trapping, Escape,
focus restoration, 200% text enlargement and other product flows.

The probe self-test first runs a clean control, then injects adjacent small
controls, missing focus rings, a covering overlay, clipped text, horizontal
overflow and a disclosure that stops expanding with reduced motion. An injected
defect must fail its intended check. Raw control measurements and tested surfaces
are recorded in runs/2026-10-09-accessibility-site-local.json and the corresponding
public record when publication is verified. Pending runs are not reported as passes.

## Executed engineering evidence

The final local run passed 62 surfaces, 772 focus-control checks, 780 target
measurements and 156 disclosure checks across both themes. All six injected
probe defects were rejected. PS input now associates empty/oversize errors with
the answer field, restores focus, clears the error on editing and announces busy
state. The fresh local run verifies both themes. Public checks are recorded separately
after deployment. No human review or formal conformance is inferred.

## Criteria and limits

- [W3C target size guidance](https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html)
  includes spacing and inline-text exceptions. The checker measures associated
  clickable labels for checkbox/radio targets; it does not falsely require every
  inline prose link to have a 24-pixel text height.
- [W3C text spacing guidance](https://www.w3.org/WAI/WCAG22/Understanding/text-spacing.html)
  supplies the override values. Checks allow scrolling content but reject hidden
  clipping. A tiny box alone is not a blanket exemption for clipped visible text.
- [W3C focus-obstruction guidance](https://www.w3.org/WAI/WCAG22/Understanding/focus-not-obscured-minimum.html)
  informs focus hit-testing. It is a sampled geometric probe, not a complete
  demonstration for every scroll, zoom, browser, overlay or assistive technology.

Automated success does not prove human screen-reader usability, actual-phone
operation, every possible color/contrast state, or all WCAG success criteria.
NVDA/JAWS/VoiceOver/TalkBack, real-device install/use/offline/update/removal and
outside-user review remain unverified. Complete conformance and procurement
claims require a separately completed review. All scope percentages keep those
requirements; no completion is inferred from these tests alone.
