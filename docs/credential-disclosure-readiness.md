# Optional disclosure measurement readiness

2026-11-20 · Codex / web_camo · F-139, F-012.

The integrated website failure named only “Inspect Python code · preview” in the PS disclosure-expansion check. The native `open` attribute changes before the deferred React state and lazy form mount; measuring height immediately after Enter can therefore see an open disclosure with no child yet. The later focus pass had already measured the loaded form, so waiting only before control capture came too late for the earlier expansion assertion.

The existing disclosure probe now accepts an optional `afterExpand` readiness callback. The website verifier uses it only for the declared optional credential disclosure, awaiting its actual `[data-credential-explorer]` form before measuring expansion. The original open-state, greater-than-one-pixel height increase, close, visibility and other accessibility assertions remain unchanged. No product, loader, method, timeout, height threshold or collection behavior changed.

A small authored delayed-child regression runs in the existing verifier: an absent child reproduces premature failure; readiness waits for the actual child; the unchanged expansion assertion then passes; an actual fixed-height clipped disclosure still fails. Focused replay checks the actual PS disclosure in light and dark and confirms that its readiness hook was exercised. No full-site replay was performed by this lane.

The first reviewer receipt is preserved. Its added assertion incorrectly expected seven measured disclosures from the raw catalogue count; one summary is inside a closed ancestor, and the unchanged probe measures six visible disclosures. The first run's height assertions had passed. The corrected reviewer requires the actual optional readiness hook and zero failures, without changing probe visibility or height predicates.

Evidence: `runs/2026-11-20-credential-disclosure-readiness-first.json` and `runs/2026-11-20-credential-disclosure-readiness.json`. Both bind actual helper/product/served hashes. The original integrated failure remains with the PM as `runs/2026-11-20-credential-integrated-website-final.json`.

This is automated measurement engineering, not full WCAG conformance, human screen-reader acceptance, physical-phone proof, independent detector accuracy or a complete original tag/scope closure.
