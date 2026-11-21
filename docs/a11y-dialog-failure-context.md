# Dialog measurement failure context

2026-11-20 · Codex / web_camo · F-139 / F-142 · diagnostic engineering only.

The PM's preserved `runs/2026-11-20-android-diagnostic-final-website.json` attempt failed with a bare dialog `locator.evaluate` timeout. The last completed result was MT/dark. That leaves at least two possibilities: the forced-colors tail of MT, which runs after its result is appended, or a subsequent IV transition. The old report could not distinguish those operations. Its underlying accessibility report had SHA-256 `619746977c4bb95e9b150ec6c51cc69717cd23bbf7e7d292280f64c357f18180`.

A finite focused replay ran MT/dark→IV twice on the same frozen actual build, including the unchanged disclosure, expansion, target, focus, text-spacing and forced-colors operations. All four checks passed and their initial visible dialog IDs matched the expected tag trigger's `aria-controls`. This does not reproduce or explain the historical timeout. There is no justified product/router fix in this increment.

The verifier now records plain JavaScript operation-stage assignments before existing awaits. Existing site operations, predicates, thresholds and timeouts are unchanged. If an operation actually fails, a separate bounded observation records the allowlisted route, expected trigger-controlled dialog ID, current dialog IDs, connection/visibility/state and count. It excludes DOM labels/text, input values, full URLs, unknown hash fragments and unknown context fields. Observation failure produces Unavailable and does not replace or suppress the original exception.

The authored privacy control runs in a separate synthetic browser context before the normal site loops. It injects an actual failure and private-looking labels/input/hash/context values, confirms those values are excluded and distinguishes expected from other dialog identity. Separate closed/missing/hung-page checks verify unavailable behavior and the one-second observation deadline. This control does not click, navigate or add waits to successful actual-site measurements.

Evidence:

- `runs/2026-11-20-a11y-mt-iv-focused-before.json`: four unchanged actual-build checks, with original-source and served-index stability.
- `runs/2026-11-20-a11y-dialog-failure-context-controls.json`: final source-hashed authored failure/privacy/deadline controls.

No full-site rerun, product source edit, timeout increase, readiness workaround, accessibility conformance, physical-phone/human acceptance, independent tag accuracy or original scope closure is claimed. Historical cause remains **UNESTABLISHED**. A subsequent real failure report can now identify its exact stage without collecting private content.
