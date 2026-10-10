# Current privacy boundaries

Privacy is checked per route across capture, transfer, logging, persistence and
disclosure. These checks cover the current selected application paths. They do
not promise anonymity, complete redaction, secure physical memory erasure, a
compromise-proof OS, or independent detector accuracy.

| Clause | Website/device PS | Optional local service and Chrome |
|---|---|---|
| Capture | Only the answer pasted into the checker; starting a check is a deliberate action. Editing, Clear and closing cancel/drop application state. | Starts paused. Separate opt-in for assistant responses on the one supported site, chatgpt.com. No prompt, toolbar, keystroke, other-site or identity capture. Settings expose pause and reset. |
| Transfer | Public runtime files download from the site; answer text is passed to a browser worker, without answer-bearing network requests. | Text goes to the authenticated fixed loopback gateway. Detected redaction precedes evaluation. Internal services are unpublished and network-isolated; host TCP probes are bounded evidence, not a universal no-egress guarantee. |
| Logging | Pyodide stdout/stderr are suppressed; console canaries and network requests are checked. Hosting providers receive connection/request metadata under their own practices. | Uvicorn URL access logs are disabled. Validation/internal errors do not reflect input. Synthetic body, URL, credential and upstream-error canaries are checked against responses and application stdout/stderr. |
| Persistence | Theme preference and optional public offline assets only. No application answer/label storage. User-triggered downloads remain under the user's control. | Only the local token and consent are saved by the extension. Current evaluation responses are no-store. Service roots are read-only and internal evaluation has no persistent volume. No automatic assertion registry/research upload. |
| Disclosure | Default summary omits answer identifiers/positions; a distinct opt-in detailed download contains potentially linkable fingerprints and positions. Research label downloads contain the examples by design. | Compact tags show brief observations; full details/download are deliberate actions with a fingerprint/position warning. Neither route publishes content or treats output as a training label. |

The capture timestamp and subject fingerprint describe a client/service
observation of the evaluated subject. They do not establish who wrote it,
human origin, truth, source independence or a cryptographic attestation. The
gateway's `captured_at` is its evaluation-time timestamp, not proof of when the
original author composed or published a response. The extension can be affected
by vendor DOM changes; its unsupported/unavailable states are distinct from a
completed check with no finding.

Pause removes application tags/references and aborts pending browser fetches.
Reset additionally removes local consent and the token. A request already
received by the service may still have done work; cancellation is not a promise
to undo it. Reset does not rotate the server token, delete vendor conversations,
remove user-owned downloads or control browser/OS administrator access.

The owner-held local reference corpus intentionally persists attachments and is
a separate explicit CLI action, not automatic evaluation storage. Public GitHub
posting, a future consented research service and future organization retention
each need their own terms and tests. They are not enabled by these checks.

## Current evidence

- `runs/2026-10-10-http-privacy-service.json`: actual three-service Linux staging,
  32 HTTP cases, source-bound shared factory, direct internal validation-error
  tests, no-store/nosniff headers and both application log streams.
- `runs/2026-10-10-current-extension-consent.json`: actual unpacked Chromium
  extension with synthetic vendor page/service; default pause, separate token
  save, opt-in, in-flight abort, stale-result rejection, resume, reset, reload
  and storage/DOM checks.
- `runs/2026-10-10-consent-worker-faults.json`: 42 actual service-worker-source
  fault scenarios with synthetic storage/fetch, including absent/false/non-boolean
  consent, missing/bad credentials, invalid envelopes and oversized streams.
- `runs/2026-10-10-consent-component-browser.json`: actual bridge/renderer on
  synthetic DOM fixtures; prompt/hidden/toolbar exclusion, races, six states,
  evidence disclosure, compact layout and automated accessibility.

`runs/2026-10-10-privacy-device-engines.json` passed 127 method-parity cases
in each engine, offline save/reload/removal, console/storage/network canaries,
no session storage and empty IndexedDB on both engines. The 9 version 1.3 policy
pages and real no-script downloads passed in
`runs/2026-10-10-privacy-policies-local.json`. Public publication is verified
separately after deployment. Physical phones, a human
screen-reader, broader live-vendor compatibility and installed-profile refresh
are not substituted by these synthetic engineering tests.
