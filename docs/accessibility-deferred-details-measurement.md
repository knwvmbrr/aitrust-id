# Deferred public details: accessibility measurement

Engineering change, 2026-11-20 · Codex / web_camo · F-139, F-142.

The website's accessibility verifier previously expanded native disclosures by assigning `open`, then enumerated controls using live indexed locators. Deferred public scope data can add Copy link and Download details after that enumeration. An actual PII_REDACTED control using the exact verifier ordering measured 26 controls initially and 28 on later passes. The first pass therefore omitted two controls.

A separate authored native-close control reproduced the reported 30-second `nth(26)` timeout: closing public details removed two earlier controls, so an indexed locator for Report an issue no longer resolved. This demonstrates a stale-ordinal failure class. It does **not** establish the exact scheduling cause of the original integrated failure; six exact-order attempts did not reproduce that timeout. The original failure and both experiments are preserved.

The verifier now waits for actual native toggle delivery and the real Download details control before taking measurements. It retains physical element identities rather than re-resolving live ordinals across asynchronous operations. Captures compare their complete raw control set before/after measurement, reject detachments or changed sets, retain failure context, and dispose element handles. Existing visibility, disabled/inert filtering, target spacing, focus, occlusion and reflow assertions are unchanged. Timeouts and thresholds are unchanged.

The integrated regression withholds the actual public scope response, proves that readiness waits and no scope request precedes first open, includes both late controls in the first measurement, and tests physical Report identity plus explicit changed-set refusal after native close. It runs in the normal accessibility verifier alongside the existing delayed HP control.

No product component, deferred-data lifecycle, user input handling, network endpoint or collection behavior changed. Native-close unmounting remains normal product behavior. Results are automated engineering evidence, not physical iPhone testing, human screen-reader acceptance, complete WCAG conformance, independent tag accuracy, or full original requirement completion.

Evidence:

- `runs/2026-11-20-deferred-details-vanishing-before.json`: authored close/stale-ordinal reproduction.
- `runs/2026-11-20-deferred-details-exact-sequence-before.json`: exact-order coverage omission; original timeout cause unestablished.
- `runs/2026-11-20-deferred-details-focused-after.json`: actual delayed-data and physical-identity controls.
- `runs/2026-11-20-deferred-details-probe-mutations.json`: unchanged defect-detection controls.
- `runs/2026-11-20-deferred-details-current-a11y.json`: final actual-build two-theme probe result.
- `runs/2026-11-20-deferred-details-execution.json`: source and served-byte binding for that execution. It does not claim that the root build equals every publication byte at the debug branch's commit.

The preserved original integrated report had SHA-256 `89e0744c1a2c8e93ef31f0bf91a8f912bd4cb2858efee5e725350520a4312587`: catalogue/light and PS/light completed; the next surface timed out resolving dialog control `nth(26)` with no failure context.
