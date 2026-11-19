# HP accessibility probe readiness correction

The failed full-site candidate reported that HP's **Source notices** link was
not focused, had no focus indicator and was obscured. The outer tag dialog was
visible, but the verifier waited for the lazy MT form only, not the HP form.
The unchanged accessibility probes obtain live indexed Playwright locators with
`.all()`. Inserting HP's controls can change the element represented by an index
between the focus action and its subsequent inspection.

The controlled regression holds the actual built HP child chunk. Before release,
the indexed target is **Testing and evidence** and receives focus. Releasing the
real child inserts HP's five controls; the same locator now resolves to **Source
notices**, which is not focused and has no indicator. This reproduces the target
identity error instead of retrying a cold load until it passes. The root's saved
full-site failure is preserved separately; the controlled proof does not claim
to reproduce every geometry/timing detail of that execution.

The verifier now explicitly waits for HP's actual form before enumerating its
controls, as it already did for MT. The delayed-load regression runs in the
normal full verifier, followed by the ordinary complete site checks. It runs
unchanged disclosure, target-size, focus, text-spacing and forced-color probes on
the ready HP modal in both themes. No product UI, CSS, tab order, focus assertion
or accessibility probe is relaxed or changed.

`verify-site-accessibility.cjs` exports its readiness helper and focused
`verifyHPReadinessControl(browser, base)` for a bounded local replay; importing
it starts no browser or full verification. Direct script execution still runs
the complete verifier. The focused replay used one Chromium browser with fresh
light/dark contexts, an owned random-port built-site server and the actual
compiled HP chunk. Both contexts passed 19 focus inspections with zero failures,
plus the unchanged layout/disclosure checks. This is not human screen-reader,
physical-phone, full WCAG or independent HP accuracy acceptance.

Evidence: `runs/2026-11-19-hp-a11y-readiness-candidate-1.json` and its summary
`runs/2026-11-19-hp-a11y-readiness-final.json`. No full site suite was rerun in
this isolated lane; the PM owns the fresh complete website revalidation.
