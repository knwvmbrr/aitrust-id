# Quiet paused checks

The existing Chrome profile showed a response-level Unsupported message while
checks were paused. Pause is an owner setting, not an evaluation result.

Keep the protocol's six result states unchanged. When checks are disabled,
remove mounted response controls, the global capture indicator and its retained
live announcement. Leave enablement and credential management in the existing
extension settings. Do not enable capture, read new text, send requests or grant
permissions as part of this repair. Enabling checks still starts a fresh check;
a canceled late result cannot restore a tag.

Implementation: expose a small UI pause cleanup operation, call it in the
bridge's disabled branch, and strengthen the existing actual unpacked-extension
privacy test. The cleanup is idempotent and must not emit its own mutation loop.
Check fresh installation, pause during a held request, rejected late response,
reset and reload. Verify that no AI Trust ID mounts or stale live announcements
remain while paused and that enabled authenticated findings still work.

Risk: clearing a shared live region during ordinary enabled scans would silence
valid findings. Limit this cleanup to disabled checks. Synthetic browser tests
do not establish current vendor compatibility, human screen-reader acceptance
or independent accuracy. Record any later live paused-state observation
separately. No new endpoint, runtime dependency or collection is introduced.
