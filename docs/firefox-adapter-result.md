# Additional browser implementation — executed 2026-10-13

Codex implemented the Firefox temporary build, explicit origin-permission lifecycle,
deterministic package writer and native browser verification. Chrome's manifest,
ChatGPT adapter, UI, background and settings sources remain unchanged. No endpoint,
production service, detector, tag taxonomy or data collection changed.

Thirty Python package/framing controls and ten Node permission/race controls pass.
Fourteen actual Firefox 153.4.0/Linux controls pass in an owned read-only,
non-root, capability-dropped, network-disabled container. The local fixture used
a private trusted CA rather than disabling TLS. Actual temporary install,
credential/public-file settings, assistant-only capture, authenticated PS rendering,
unsigned/altered refusal, pause, reset and uninstall all execute. These are
synthetic vendor/service observations, not live ChatGPT or independent accuracy.

Failures are preserved. Firefox's port-containing permission pattern did not grant
loopback access; its documented portless pattern fixes this without changing the
fixed request endpoint. The test initially navigated away before consent settled,
assumed a permission panel must appear even when grants existed, navigated after
uninstall had closed the options tab, and discarded the session before shutdown.
The corrected driver waits for persisted settings, accepts only a displayed panel,
uninstalls from a vendor tab and uses the live driver session for owned-browser
shutdown. No TLS, signature, consent or containment check was relaxed.

The Mac headless binary did not start Marionette; its failure is not a Mac pass.
Firefox requires a different background format and cannot limit a browser grant
by port. The guide states the browser-level grant honestly and retains the
fixed authenticated 8787-only code destination. Existing Chrome use remains
independent of this optional preview's failure.

F-156 advances to selected-integration evidence (80%). Full acceptance remains
open: current live vendor use, a stable user distribution/install lifecycle and
any additionally declared site/browser support must be executed. No full
requirement is closed by a developer fixture. The 43-or-fewer target remains.

[Guide](firefox-preview.md) · [Plan](firefox-adapter-plan.md) ·
[Actual Linux receipt](../runs/2026-10-13-firefox-linux-integration.json).

## Actual application route

The final licensed package also executes against the real source-verified
gateway, anonymizer and evaluator together. Fifteen actual Linux controls pass.
The browser sees real signed application assertions for synthetic text; unsigned
and altered bytes still refuse a finding. All sixteen distinct application and
protocol source paths match the checkout before launch. Services use separate
locked import roots and private shutdown pipes, with fresh fixture keys/tokens.
No real credential, existing database or production service is touched. The
container remains read-only, non-root, capability-dropped and network-disabled.

[Current three-service receipt](../runs/2026-10-13-firefox-real-services-linux.json).
Earlier cleanup failures stay failed; the passing run includes service shutdown.
The archive now includes the actual Apache license. Source, nonce, signature,
consent and cleanup conditions were preserved throughout. This advances F-156's
selected integration; it does not complete current live vendor/outside-user
acceptance or release PS.
