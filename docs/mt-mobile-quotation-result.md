# MT mobile quotation candidate — implementation result

Codex / web_camo · 2026-11-21 · source base3a1e63766b9403c575f7e25ae45e65d9bfbb7647.

The existing ASCII quotation method was already available in the browser. This
increment adds a distinct selection, **Include curly quotes · preview**, for an
actual missing phone input case. The old method refused `The example says
“Experts agree [1]”.`; the candidate records one quoted phrase and no outside
phrase. It gives location/count evidence, not an MT tag or interpretation.

Canonical method: `mobile-double-quote-authority-observations/1.0.0`.
`tools/authority_mobile_quotation.py` SHA-256:
`f230f44ea5584302e08b1b462839b8b41c0e69d03f7f5e34fc197a0c47b2b4bd`.
Browser profile: `mt-device-mobile-authority/1.0.0`. Complete raw/NFC/source-bound
records have closed schemas, quote/span/count checks and a100,000-byte budget.
The JS validator trusts the hash-verified canonical worker; it does not separately
replay phrase matching or establish semantic completeness.

## Executed evidence

- 74 focused Python controls pass for canonical grammar, projection/positions,
  input/output limits, actual CLI/private export, optional safe packaging and
  existing MT adapter/builder behavior.
- 19 Node client/validator controls pass, including retained legacy cases,
  original raw input identity, malformed evidence, typed privacy refusals,
  cancellation and cleanup failure settling rather than hanging.
- Existing `scripts/verify-mt-device.cjs` passes actual Chromium and WebKit:
 30 full legacy records plus 28 full candidate records per engine, retained
  lifecycle/privacy/fault/reflow/axe controls, and stable source inventory.
- `scripts/verify-mt-mobile-site.cjs` passes the actual MT modal in both engines
 on a source-frozen prototype artifact: three whole native records per engine,
 private-details opt-in, unsupported→legacy urgency/ASCII recovery, edit/clear/
 close cancellation, empty reopen,320px at200% text, both themes,44px actions,
 no input network/storage/console, and candidate payload/module failures followed
 by actual successful legacy urgency checks. Four phone-view screenshots were
 inspected. Source and served hashes remained stable.

These are authored engineering controls, not independent detector error rates,
physical iPhones, human screen readers or final release validation. The prototype
used inherited3a site/main plus MT-only source changes, copied reviewed runtime
assets, and a bounded Vite build. It did not run the final PM preparation,
protected suite or publication. The first actual-site build refused an absent
ignored generated PS manifest; that candidate remains recorded. Running the
unchanged existing PS asset builder supplied its inherited prerequisite. No PS
source or method changed.

## Reuse and PM handoff

- Existing `build:mt-device` / `scripts/build-mt-device.py` now also prepares the
 separate optional mobile payload. Legacy canonical Python sources, manifest and
 source-bundle identity remain unchanged. Fixed inert optional metadata is in the
 shared worker; optional Python payload/JS validator load only on explicit Run.
- Existing `scripts/verify-mt-client.cjs` includes the new Node cases. Existing
 `scripts/verify-mt-device.cjs` includes28 candidate full-record cases alongside
 its legacy checks. A single shared worker/client architecture is retained.
- Add required actual built-site command `node scripts/verify-mt-mobile-site.cjs`
 to PM source-bound/protected website verification. Default artifact is `site/dist`;
 `AITRUST_MT_MOBILE_BUILD` selects another reviewed local build. Set
 `AITRUST_MT_MOBILE_SITE_REPORT` to a new evidence path when preserving a run.
- For actual published interaction, reuse
 `require('./scripts/mt-mobile-site-controls.cjs').verifyMTMobileSite(browser,base)`.
 It requires the real MT modal and actual canonical observations; it does not
 insert mock methods or bypass CSP.
- PM should add the normal preparation copy from `docs/mt-mobile-quotation.md` to
 `site/public/reference/mt-mobile-quotation.md` so future guide revisions remain
 synchronized. This candidate includes the exact current derived copy.
- PM owns new verifier/source inventory bindings, shared package/CI/preparation,
 final distinct review, protected integration, final real build and live proof.

No catalogue, taxonomy, production MT mapping, scope percentage, board/state,
account, endpoint, dependency/model/license, training collection or permission was
changed. Original T-MT/F-019c acceptance and independent/human gates remain open.
