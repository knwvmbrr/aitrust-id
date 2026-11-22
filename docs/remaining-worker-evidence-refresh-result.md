# Current owned-worker execution evidence

The worker repair is now exercised by fresh local conformance and macOS capture
runs, plus an already executed exact-source Linux audit artifact. This refresh
changes no public tag, original acceptance or production service.

- [Conformance](../runs/2026-11-22-conformance-worker-ownership.json): all28
  reference contract checks and12 focused tests pass under the current selected
  producer source. The selector was frozen before capture because it is itself
  an input. Outside-person acceptance and accuracy remain false.
- [macOS capture](../runs/2026-11-22-host-worker-ownership-macos.json): all20
  actual foreground/private-PTY controls pass with no failures, errors or skips.
  No automatic upload, company collection, physical-phone or human claim follows.
- [Linux audit](../runs/2026-11-22-organization-audit-worker-ownership-linux.json):
  all31 actual controls pass. Exact source22bindings match the current source.
  This is the original byte-for-byte artifact from successful run44982217342 at
  source01fcec9, retaining its original capture time. No database lab was rerun.

The selected auxiliary audit environment is exactly PostgreSQL18.7
(`postgres (PostgreSQL) 18.7 (Ubuntu 18.7-1.pgdg24.04+5)`) with
`pgBackRest 2.60.1`. The old2.59.3 guard correctly refused this new environment;
PM explicitly accepted this actual tested tuple. The guard now requires that
exact pair, and focused controls refuse old/unknown version combinations. Earlier
2.59.3 guides and receipts remain historical and unchanged. This is not a
production upgrade, lockfile change or a claim that arbitrary versions work.

Fresh Linux capture20 remains pending the newly registered hosted workflow.
The producer, original cases/deadlines and twelve source inputs are unchanged.
The workflow adds no project dependencies and requires the actual current Linux
receipt, non-root execution and network-namespace flags before succeeding. No
current full two-OS capture claim is made until that actual receipt is selected.
