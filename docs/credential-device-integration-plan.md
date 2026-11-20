# On-device Python flow preview — integration plan

Original scope: F-012, with T-PS's release boundary preserved. Implementer:
credential tag worker. PM and separate reviewer: Codex. This is a usable optional
method inside the existing PS panel, not a new tag or a released PS enhancement.

## User outcome

A phone or desktop user can paste a bounded Python snippet, explicitly inspect
it locally, and see whether a supported credential-named read reaches an HTTP
argument. The program is never executed. A short result explains the observation
without claiming a live secret, an actual transfer, authorization or intent.
Unsupported processing says Unavailable; zero findings is not a safety clearance.

## Architecture and owned integration

Keep the canonical credential-flow 1.0.2 source byte-identical. A credential-only
builder packages the required source and frozen Unicode normalization, notices
and hash manifest. A fresh, independently owned browser worker loads the existing
pinned, self-hosted Pyodide runtime assets. It does not import HP/MT tag workers.

The optional lazy Slot owns its import/render errors. The client binds raw UTF-8,
frozen NFC, source and method identities; a closed validated record must match
native execution. Bound input, startup, output and check time. Edit, clear,
cancel, new input and unmount invalidate/terminate pending work. No account,
gateway, upload, input storage or default export is added.

The worker owns new adapter, builder, manifest, worker/client/validator, React
component and focused controls. PM owns `main.jsx`, build/package hooks, current
verification/source inventory and scope/state/changelog. Mount the no-props
`CredentialFlowExplorerSlot` only in PS; a failed optional chunk/worker must leave
the existing PS checker and unrelated implemented previews usable.

## Risks and acceptance

Runtime downloads/memory, Unicode span errors, stale worker replies, malformed
records and misleading secret/intent claims are the main risks. Verify actual
Chromium and WebKit records against unchanged canonical native results, both
themes at phone width, keyboard/labels, no input network/storage, all cancellation
paths, malformed/changed identity refusal and actual PS operation after the new
chunk fails. Preserve source-bound evidence and require a distinct reviewer.

Freeze generated sources before capturing current integration fingerprints. Ship
only after protected checks and actual public verification. This named browser
software job can finish; F-012's accepted integration, representative independent
measurements, use/mention interpretation and applicable human/route release gates
remain open. Do not raise its original percentage or close T-PS from this preview.

The shared PS panel mounts this optional preview only when its disclosure opens.
Closing it unmounts the editor and stops its worker; it never takes over the
existing PS result. The accessibility verifier waits for the expanded preview
to mount before capturing its physical controls.
