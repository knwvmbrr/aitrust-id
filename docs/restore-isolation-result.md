# Early restore refusal

Codex implemented the existing synthetic restore’s preflight boundary before filesystem creation, secret reads or subprocesses. The current source requires an isolated root Linux process with only loopback and keeps the same namespace before restoration and startup. Linked, service-owned, shared, special or cross-filesystem generation members refuse inspection; private root-owned regular-file hard links remain permitted. Lazy traversal enforces 100,000 visited entries and a 30-second budget. The existing named target, schema and backup-label contracts remain unchanged.

Forty focused tests pass, including 37 new guard/permission/budget controls and the three existing forced-SSH protocol tests. Eighteen actual kernel/filesystem checks pass on the dedicated Linux host using invented private fixtures, including host-namespace CLI refusal and refusal of an isolated namespace containing virtual network interfaces. Both owned staging directories were removed. CI will repeat the actual kernel checks and unit refusals. No real restore, production installation, configuration change, new endpoint or collection occurred.

F-073 and N-011 remain open with their original full acceptance. Named operational ownership, incident/adapter response, full replacement-host recovery and outstanding security findings remain distinct work. This component does not certify a backup, defend against hostile root or fulfill owner recovery custody.

[Kernel evidence](../runs/2026-10-12-restore-isolation-kernel.json) · [Staging cleanup](../runs/2026-10-12-restore-isolation-staging-cleanup.json)

The complete current Python suite passes 2492 tests (one platform-specific skip and one upstream warning), with checked sources unchanged during execution. All five selected capability checks and all eight website checks pass. The failed first website receipt remains available; its changelog ordering was repaired before the successful rerun. [Full suite](../runs/2026-10-12-restore-isolation-full-suite.json) · [Focused controls](../runs/2026-10-12-restore-isolation-focused.json).
