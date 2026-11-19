# MT device explorer — initial component result

**Superseded for integration.** Review found missing request-to-result binding,
open nested record fields and unsafe builder input reads in the initial component.
The [integrity correction](mt-device-integrity-correction.md) and its new receipts
replace this initial result for current adoption; original run records remain
unchanged historical evidence.

Codex's MT on-device evidence engineering lane built this increment from
`324db5a83ad6883551d5baeaab0ec2793bea50be` on 2026-11-19.

The component is working in an unpublished browser fixture. Users choose and run
an urgency or authority-quotation observation, receive a short explanation and
can deliberately open exact private method/position details. No check is selected
by default. No MT assertion, account, upload, storage or telemetry was added.

The [safe slot](../site/src/MTExplorerSlot.jsx) contains lazy child import/render
failure; the [component](../site/src/MTExplorer.jsx), separate client/worker and
[Python adapter](../tools/mt_device.py) preserve existing methods and input bounds.
The deterministic source bundle carries original LICENSE, NOTICE and Unicode
attribution. Existing third-party runtime notices are preserved, not cleared.

Verification:

- **80 focused Python tests** passed, covering adapter parity with existing
  urgency/quotation methods, limits, exact source/notice bytes and optional
  authority failure without disabling urgency.
- **8 Node client groups** passed, covering separate lazy workers, cancellation,
  deadlines, identity/refusal checks, explanations and source attribution.
- **Chromium and WebKit** each matched **26 full native-Python records**. Current
  browser checks passed for editing/Clear/unmount cancellation, no input in
  requests/storage/console, private-detail opt-in, quote-refusal recovery,
  malformed/oversized bundles, unsupported workers, evaluation deadline, actual
  missing MT chunk and injected import/render isolation. A separate tool probe
  remained usable; the actual PS worker was not retested in this lane.
- Both engines passed 320px reflow at 200% text, at least44px form controls,
  keyboard navigation and zero selected-rule axe findings. Light/dark WebKit
  screenshots were visually inspected. Safari full-control navigation uses
  native Option+Tab, with no custom keyboard behavior.

The [source-stable receipt](../runs/2026-11-19-mt-device-explorer.json) links the
[current browser record](../runs/2026-11-19-mt-device-browser.json) and preserves
the initial fixture source-discovery and keyboard-expectation failures. This is
engineering evidence, not independent accuracy or complete accessibility
conformance. Physical iPhone 14 Plus and human VoiceOver remain outstanding.

PM still owns the shared MT-modal mount, build hook, actual production Tailwind
build and deployment. Use the [integration contract](mt-device-explorer.md) and
[architecture plan](mt-device-explorer-plan.md). Shared catalogue, availability,
performance, usage, scope, state and build preparation files were not edited.
No full MT requirement closure or status promotion is claimed.
