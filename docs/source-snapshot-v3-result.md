# Source snapshot v3: actual hosted result

The corrected source at `b75f434b7d1b82d7641b8fefd44e3013328f1c77` passed
[the read-only Linux qualification](https://github.com/knwvmbrr/aitrust-id/actions/runs/45043627100).
All 16 controls passed with no errors, failures or skips. The real isolated CLI
built and v3 inspected all 12,829 committed source files: 128,339,526 raw source
bytes, above the old 128,000,000-byte limit. The unchanged v2 reader refused it.
The exact archive SHA256 is
`552a8ef19448d7b51ac8dca6c2c67138f7900e4a3e146933b59a5d6cf551b53e`.
No source member was extracted or executed.

Current source-graph preparation, canonical packet reconstruction and SPDX
publication passed on that same real archive. The packet is 14,935,218 bytes;
SPDX is 9,216,070 bytes. The existing 16,000,000-byte packet cap stays unchanged:
only 1,064,782 bytes remain, so the final combined source/graph must be measured
again rather than assuming the MCP and later additions fit.

The 768 MiB address-space limit was inherited by child processes. Reported self
and largest-child RSS maxima were each 233,656 KiB (about 228 MiB); they are
per-process maxima, not a measured simultaneous aggregate. The retained provider
artifact contains only the bounded JSON report, not the archive, packet or SPDX
payloads. There was no local large archive, installation or disk-reserve waiver.

The first `4d494944` hosted candidate passed all 16 controls but its builder
returned exit 1. Its exact lost stderr category remains unknown. Independent
local help-command reproductions demonstrated a real isolated-import bootstrap
defect in both active CLIs. The corrected trusted-script-directory bootstrap
keeps `-I -S -B`, immutable v1/v2 and all limits. Both help commands and an actual
six-file owned Git-fixture CLI build passed before the changed-source hosted run.
The failed first report and source commits remain preserved.

This is functioning archive-capacity software and developer source evidence. It
does not attest a release, approve a distribution route, clear licenses, establish
independent tag accuracy or close full F057/X02. Source format remains unchanged;
small v1/v2/v3 output bytes match, while older readers retain their smaller caps.
The metadata-only evidence handoff changes the Git source commit: its archive
and the future integrated main archive require their own current measurements
and protected signing. No qualification is relabeled to that later commit.

The final evidence lives on `codex/source-snapshot-v3-evidence`, a normal child of
the qualified source commit. This avoids a third capacity run: the reviewed push
trigger matches only `codex/source-snapshot-v3`. No workflow, skip-CI marker or
qualified source input was altered for that handoff.
