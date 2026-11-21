# Selected browser-runtime source and notices

This offline tool packages the preferred JavaScript source and two full license
texts associated with the exact Pyodide314.0.7 loader shipped by the website.
It repairs an actual carried-notice gap: the loader source map embeds adapted
StackFrame/error-stack-parser files, but their adjacent upstream MIT copyright
notice was missing from the existing carried runtime and website notice bundles.

The ten source-map files byte-match upstream commit
`b1e4fcc2488962f6360a97f19b9982d6fdb5d16f`. The downloadable ZIP contains those
ten preferred files, the exact source map, the full unmodified pinned upstream
source archive, the notices and an identity index. The readable notices retain
both the upstream MPL-2.0 and vendor MIT texts without modification.

## Use it without installing anything

From a normal source checkout with Python available:

```sh
python3 scripts/pyodide-js-sources.py
python3 scripts/pyodide-js-sources.py --export site/public/runtime-js-sources
python3 scripts/pyodide-js-sources.py --check-built site/dist
```

The exporter requires an existing owner-controlled parent directory. It creates
`PYODIDE-JS-SOURCES.zip`, `NOTICES.txt` and `index.json`. Verification is entirely
offline and does not evaluate the source, execute package binaries or extract
archive-selected filesystem paths. The optional `--npm-archive` flag replays an
already cached exact npm archive; it never downloads one.

`--check-built` requires all five exact selected runtime files under
`device/runtime-314.0.7/` and all three exact source/notice outputs under
`runtime-js-sources/`. Missing, changed or extra files in these two selected
folders refuse the check. This does not inspect every other website artifact.

## What the check establishes

The retained archive, map, preferred files, licenses and generated bundle are
byte-bound to the selected release and producer. An exact producer-anchored
five-runtime-member digest prevents coherently rehashed mutable release/cohort
data from substituting unrelated binaries. All five members were replayed from
the exact SHA512/SHA256-pinned cached npm archive. Bounds apply before gzip/tar
metadata parsing and output allocation. Output replacement stages all files
first; input refusal and pre-replacement failures preserve previous outputs.
A failure after replacement begins reports `output_commit_uncertain` and may
leave a backup/output for manual inspection. This is not a crash-atomic transaction.

The current proof used the five actual files copied from an existing normal
website build. The original build lacked this new artifact and correctly failed;
the owned copy passed after actual export. Altered notices, bundle, index, runtime
and an unknown carried file each refused. The root build was not changed by that
proof, and public delivery is still pending integration.

## Limits and integration handoff

This is selected JavaScript source/notice delivery, **not complete corresponding
source for the WASM binary**, a rebuilt compiler result, signature verification,
legal clearance or admission of the website distribution route. The rest of the
WASM/native/build dependency obligations remain open. Existing website JavaScript
notices remain34 exact archive records plus one separately sourced supplement
whose exact2.3.8 release correspondence is unverified; this work does not change
that qualification or any of the13 unknown route decisions.

The PM must wire normal preparation to export the three files, run the actual
built-artifact check after build, add a discoverable notice/bundle link and bind
these new inputs to the appropriate verification inventory. The website's
explicit offline-cache allowlist does not currently include this new directory;
any offline notice carriage needs its own bounded integration. No hook, route,
permission, endpoint, tag assertion or release status is changed by this branch.

## Recorded correction and current proof

The initial producer had a return-value unpacking defect, corrected before its
first focused tests. PM review then demonstrated a separate genuine gate bypass:
coherently changed release/cohort metadata could substitute all five runtime
identities while leaving producer source unchanged. The original candidate
receipt is retained as historical evidence, rather than reused for current
approval. The corrected producer anchors the exact reviewed projection and
refuses that unchanged-source counterexample.

The current receipt is `runs/2026-11-21-pyodide-js-source-corrected.json`:36focused
controls and11actual CLI/artifact/control outcomes pass. This is engineering
source/notice evidence; it is not legal advice or release approval.
