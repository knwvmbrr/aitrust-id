# Embedded zlib source and notices

The website's pinned Pyodide314.0.7 runtime reports zlib1.3.1. Its exact cached
Emscripten port recipe selects a source archive whose SHA512 matches the cached
archive. The complete upstream zlib LICENSE and zlib.h notice were missing from
the carried notices. The older CPython acknowledgement is preserved; it is not
substituted for the selected release's complete text.

This producer carries the unmodified zlib source archive, full LICENSE, full
zlib.h source/header, and exact Emscripten recipe with its complete upstream
MIT/NCSA notice. No source archive or library code is executed by the producer.
The separately recorded synthetic version probe used the five exact existing
runtime files, completed without network calls and returned zlib1.3.1.

## Offline commands

```sh
python3 scripts/zlib-source-delivery.py
python3 scripts/zlib-source-delivery.py --export site/public/runtime-zlib-sources
python3 scripts/zlib-source-delivery.py --check-built site/dist
```

The existing owner-controlled parent directory must be present. Export writes
exactly `ZLIB-SOURCES.zip`, `NOTICES.txt` and `index.json`. The deterministic ZIP
contains six members and the full upstream source archive. Default verification
uses the retained cohort files; it needs no private cache, network or install.
`--replay-cache` separately replays the two exact already cached source archives.

The artifact check requires the exact five runtime files and all three generated
files. Missing, changed or extra files refuse. The producer anchors source,
recipe, notice and observed runtime identities independently of mutable carried
metadata; coherently rehashed runtime/source substitutions do not approve them.

## Resource and failure behavior

Compressed source identities are checked before parsing. Gzip expansion and tar
metadata are bounded before tarfile parses the cached recipe archive. Source
members must be regular, unique and bounded. Archive-selected paths are never
extracted into the filesystem. Generated ZIP/input/notice sizes are bounded.

All output files stage before directory replacement. Pre-replacement refusal or
write failure preserves prior outputs. A failure after replacement starts reports
`output_commit_uncertain`; a backup or output may remain for inspection. This is
not a crash-atomic rollback guarantee. Raw output descriptors are owned explicitly
through wrapper construction and relinquished before one close attempt; a close
error is never retried against a potentially reused descriptor number.

The first candidate's actual artifact proof passed, but distinct review found a
raw-descriptor leak if fdopen construction itself failed. Its proof is retained
as historical. The corrected source passes32focused controls, including actual
constructor-failure closure, close-after-release/reused-marker protection and a
fixed private CLI diagnostic. Seven current actual export/artifact/cache checks
pass; the original16checks are not relabeled as current reruns.

## Scope and integration

This is an existing F-057 attribution/source-delivery repair, not a new tag or
full-original completion. It does not establish reproduced compiled linkage,
full WASM corresponding source, publisher signature verification, legal
clearance, global distribution admission or complete project obligations. All
13unknown routes and the separate34exact+1unverified JavaScript qualification
remain open.

Root must add this exporter after pinned runtime preparation, retain the existing
selected-JS exporter, and append the actual zlib artifact check to normal
postbuild and predeploy commands. Add discoverable readable-notice/source links,
source inventory/fingerprint inputs and focused controls. Existing checks stay
in place. The new directory is not automatically in the existing offline cache;
offline carriage requires explicit bounded integration. No shared hook, policy,
state or public deployment is changed by this isolated source branch.
