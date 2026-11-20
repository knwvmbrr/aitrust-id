# Optional Python-flow production UI review

Codex / web_camo · 2026-11-20 · bounded F-012 / T-PS engineering review.

The reusable `scripts/credential-site-controls.cjs` exports `verifyCredentialSite(browser, base)` for an already running reviewed static fixture. Its standalone entry starts only an owned loopback fixture, runs Chromium then WebKit sequentially and closes its browsers, contexts and server. It does not publish, upload source, register credentials or change the production tag mapping.

This checks the actual `/#person/PS` route, not the standalone method fixture. It measures the new optional native disclosure's cold lifecycle, complete canonical Python records, private-details opt-in, source privacy, unsupported-source recovery, cancellation on native close, empty reopen, narrow enlarged layout and isolation from the existing PS checker. A failed optional chunk must show its local fallback and still allow an actual PS command check.

The browser uses only synthetic inert snippets. Canonical expectations come from the unchanged `tools.credential_device.inspect_credential_device` in the integrated source tree. Requested source is not executed. Native record equality is engineering parity, not a measured detection accuracy or independent validation of the whole PS tag.

Standalone execution from the integrated repository:

```sh
AITRUST_VERIFY_PYTHON=/path/to/existing/verification-python \
AITRUST_CREDENTIAL_SITE_REPORT=output/verification/credential-site-review.json \
node scripts/credential-site-controls.cjs
```

For a separate reviewer worktree, `AITRUST_CREDENTIAL_SOURCE_ROOT` selects the integrated source tree and `AITRUST_CREDENTIAL_BUILD` selects its frozen `site/dist`. These explicit local paths avoid copying the integration's source or changing its build. The standalone receipt hashes the reviewed helper, integrated method/UI sources and actual served assets before/after. It does not assert that every served publication byte matches the reviewer's commit.

The script requires actual response CSP and makes no CSP bypass. Normal inputs must remain absent from requests, browser storage and console messages. The missing-chunk context intentionally expects a confined loading failure; it never treats the fallback as a method result. Optional import/runtime download needs an initial network connection. Neither physical-phone behavior, human screen-reader acceptance, complete WCAG conformance, source authorization, real credentials, execution nor intent is established.

## Executed result

`runs/2026-11-20-credential-production-independent-review.json` records successful Chromium and WebKit runs against the PM's frozen integrated production build. Each browser compared three complete native records, checked the closed/open/Run lifecycle and cancellation on close, inspected normal/private/result/error states, and completed actual PS checks after both optional-close and optional-chunk failure. All reviewed source and served asset hashes stayed stable during execution. No product or method source was edited by this review.

Light Chromium and dark WebKit screenshots were visually inspected from `output/playwright/credential-production-{chromium,webkit}-{light,dark}.png`. They show a scrolled mid-panel reading position rather than the entire long modal. Real phone and assistive-technology acceptance remain separate.
