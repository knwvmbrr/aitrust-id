# Current capture mechanisms — executed acceptance

The eight named jobs completed in this increment are the current evidence
resistance assessment (F-009), selected DOM fallback (F-031), response/revision
binding (F-088), duplicate suppression (F-089), character-data observation
(F-090), streaming settle (F-032), local-token options (F-091), and distinct
result-state rendering (N-002). None is a released detector or a completed
whole capture package.

Two real timing defects were fixed before acceptance. Unrelated DOM changes no
longer restart a response's settle timer. A manual check consumes that timer,
preventing a later duplicate automatic request. `scripts/live-dom-acceptance.js`
executes both failure-triggering scenarios and records passing results. The
current bridge invalidates results on content, identity, page, request revision,
streaming and consent changes. Loss of assistant ownership removes the badge.
Character-only edits and out-of-order replies are tested directly.

`runs/2026-10-10-capture-timing-current.json` contains executed browser checks,
including duplicate suppression, text mutations, unknown evidence, unsupported
capture, six separate result states and zero automatic axe violations.
`runs/2026-10-10-options-current-extension.json` uses a real unpacked extension
in its own disposable Chromium profile: default pause, token save distinct from
consent, enable, pause/abort, invalid-token unavailable result, reset and reload
all function. No answer is persisted; the token is absent from the options DOM.
The local test service is synthetic and is identified as such.

The earlier audit attached whole live-vendor, independent-human and detector
release gates to each unrelated DOM/options mechanism. Those requirements remain
open under F-037/F-156 (vendor coverage), F-035 (human accessibility), F-142
(outside-user setup/removal), N-012 (physical phones) and T-PS (tag release).
They are preserved in each row's prior-acceptance mapping, not declared performed.
Selected synthetic markup derives from observed assistant anchors; it is not
a new live-vendor run. Real browser operation is not human screen-reader testing.

The separate source-bound engineering revalidation receipts run the current
PS and extension checks and detect subsequent source/fixture/dependency changes.
The command method uses a frozen word class to reproduce server/browser results;
137 cases agree in each Chromium/WebKit engine, including actual regression
cases that initially failed. Physical handset performance remains unverified.
