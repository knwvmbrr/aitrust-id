# Early restore refusal

Codex implemented the existing synthetic restore’s preflight boundary before filesystem creation, secret reads or subprocesses. The current source requires an isolated root Linux process with only loopback and keeps the same namespace before restoration and startup. Linked, service-owned, shared, special or cross-filesystem generation members refuse inspection; private root-owned regular-file hard links remain permitted. Lazy traversal enforces 100,000 visited entries and a 30-second budget. The existing named target, schema and backup-label contracts remain unchanged.

Forty focused tests pass, including 37 new guard/permission/budget controls and the three existing forced-SSH protocol tests. Eighteen actual kernel/filesystem checks pass on the dedicated Linux host using invented private fixtures, including host-namespace CLI refusal and refusal of an isolated namespace containing virtual network interfaces. Both owned staging directories were removed. CI will repeat the actual kernel checks and unit refusals. No real restore, production installation, configuration change, new endpoint or collection occurred.

F-073 and N-011 remain open with their original full acceptance. Named operational ownership, incident/adapter response, full replacement-host recovery and outstanding security findings remain distinct work. This component does not certify a backup, defend against hostile root or fulfill owner recovery custody.

[Kernel evidence](../runs/2026-10-12-restore-isolation-kernel.json) · [Staging cleanup](../runs/2026-10-12-restore-isolation-staging-cleanup.json)

The complete current Python suite passes 2492 tests (one platform-specific skip and one upstream warning), with checked sources unchanged during execution. All five selected capability checks and all eight website checks pass. The failed first website receipt remains available; its changelog ordering was repaired before the successful rerun. [Full suite](../runs/2026-10-12-restore-isolation-full-suite.json) · [Focused controls](../runs/2026-10-12-restore-isolation-focused.json).

## Hosted process-observation repair

Both new kernel/host-config runs passed. One existing no-egress test observed ESRCH while reading a child that had just been reaped. Its helper now treats ENOENT and ESRCH as candidate disappearance, still requiring a second kill(0) failure; running/zombie interpretation and permission-error refusal are preserved. Eighty-two focused recovery/reference-process tests pass, including both disappearance regressions. This changes test observation, not model deadlines, recovery controls or required CI policy. The failed hosted run is retained and the new exact head must pass before merge.

The next hosted run caught an additional test assumption: documented Linux dead state X was rejected because the helper accepted only Z. The helper now accepts Z/X/x as terminal, as documented in [proc_pid_stat(5)](https://www.man7.org/linux/man-pages/man5/proc_pid_stat.5.html), and explicitly refuses ten active/unknown states. Permission failures still fail, and disappearance still requires kill(0) confirmation. All 94 focused tests pass. Both hosted failures remain recorded; the production recovery code and model deadlines are unchanged by these test repairs.
