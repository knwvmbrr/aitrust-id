# Accessibility action failure diagnostics

2026-11-20 · Codex accessibility debugging lane.

The prior integrated build failed with a 30-second
`locator.scrollIntoViewIfNeeded` stability timeout after the light catalogue
surface. Its report did not identify the active tag or control. Narrow actual
build replays, delayed scope loading and an active-frame control did not reproduce
that timeout. These diagnostic results are preserved. The underlying cause is
**UNESTABLISHED**; this change does not claim a product bug was fixed or closed.

Only failure observability changed. After an existing scroll/focus/inspection
operation throws, the probe attaches the known surface/theme, action, live
locator selector and a bounded post-error snapshot: control label/tag,
connection/visibility and rectangle. Input, textarea and select identities use
labels, not entered values. A missing/closed target is reported unavailable.
The original exception is rethrown and its message remains intact.

There is no additional pre-action await or successful-path DOM read. Existing
focus, indicator, occlusion, target, disclosure and spacing criteria remain the
same, as do their action timeouts. The main report preserves the failure context
when present. The snapshot describes the element observed **after** the error;
it cannot establish the original element's identity if a live indexed locator
retargeted during the failed operation.

Authored controls verified a moving-control timeout and a focus failure. They
captured the expected surface/action/label while preserving the error, and a
synthetic textarea canary was absent from its diagnostic. Those controls validate
the diagnostic, not the cause of the earlier real-site timeout.

One full actual accessibility run on the PM's frozen built assets passed:
62 surfaces, 916 focus checks, 890 target checks and 158 disclosures at 320x760 in
light/dark modes. Source and served JS/CSS/JSON/header hashes were checked before
and after. That is a current passing execution, not proof that an intermittent
failure cannot recur, full publication-byte equivalence to the source HEAD,
human screen-reader acceptance, physical-phone testing or WCAG conformance.
No product source, scope percentage or requirement closure changed. The PM owns
source binding/integration and the original unresolved timeout record.

Evidence: `runs/2026-11-20-a11y-failure-diagnostic-controls.json`,
`runs/2026-11-20-a11y-full-diagnostic-run.json`,
`runs/2026-11-20-a11y-full-diagnostic-source-proof.json`, and
`runs/2026-11-20-a11y-diagnostic-result.json`.
