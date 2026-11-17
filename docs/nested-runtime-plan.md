# Nested runtime source and notice evidence

Architecture/risk plan before code · 2026-11-17 · F-057 / X-02.

Inspect the one nested archive left by the existing 205-artifact inventory:
Pyodide 314.0.7's `package/python_stdlib.zip`. The existing cached npm artifact,
lock SRI, parent SHA-256, nested hash and selected-asset record identify the same
bytes. Keep those older inventories and their execution records unchanged.

The observed ZIP contains 614 entries: 567 files including 559 Python source
modules, and 47 directories. Inspecting its filenames alone is insufficient.
The source includes explicit MIT/Apache SPDX declarations, contributor/license
headers and a vendored macholib README. The existing external runtime license
files do not include every component acknowledgement. The full CPython 3.14.2
`Doc/license.rst` is therefore a necessary small upstream-text retrieval; freeze
its exact bytes/hash and origin, without claiming tag/signature authentication.
Do not substitute an unrelated package's MIT notice because its holder matches.

## Implementation

- Add `tools/nested_runtime_inventory.py`, `scripts/verify-nested-runtime.py` and
  focused controls. Use only the standard library and existing safe readers.
- Validate the existing parent/asset inventories, lock SRI and parent SHA before
  reading the same captured tar bytes. Reproduce the selected nested identity
  and runtime metadata. No source path extraction, import or execution.
- Preflight ZIP central-directory counts/lengths before ZipFile allocation;
  refuse ZIP64, multi-disk, encryption, extra/comment records, unsafe/duplicate
  paths, special/link files, overlapping local regions, unsupported compression,
  nested containers and expansion/count/member excesses. Stream every member to
  EOF, checking CRC, length, hash and UTF-8 source profile.
- Record every member and every Python module's distribution context, exact
  retained header, explicit SPDX declarations, shipped-source presence and
  applicable notice/source-reference bindings. Include the vendored README and
  explicit third-party declarations. No header means no inferred per-file grant.
- Machine-check the unchanged existing runtime notices, CPython's version-matched
  acknowledgement text, Apache terms where explicitly declared, version-correct
  source references, source/header retention and complete member/module coverage.
  Reject changed/missing notices, source links, declarations or promoted clearance.
- Write a separate `sbom/nested-runtime` inventory/obligation record. Offline
  consistency cannot prove archive bytes; explicit cached-archive replay does.
  A no-overwrite export produces a fixed-name notice/evidence text bundle, never
  archive-member paths. Shipping-package integration remains separately visible.
- Publish the fifth runtime notice from the verified bundle after Vite has
  staged the built runtime. Require the exact five runtime member sizes and
  digests before writing the notice, then add it to the existing public offline
  allowlist and licensing page. Retain the four verbatim notices. Missing,
  altered or duplicate release output fails the staging step. The web and
  native builders can consume the same digest-checked bytes, with native
  resource verification and release fingerprint changes handled separately.
- Update this lane's docs, execution receipts and attributed changelog only.
  Global scope/state and completion decisions remain with PM integration.

## Risks and acceptance

Hostile archives can hide links, corrupt CRCs, overlapping entries and bombs.
Bound both declared and actual reads and avoid following paths. Checksums do not
establish upstream identity. A filename/marker classification is a distribution
and retention observation, not a legal grant or independent license review.
Source files in this ZIP do not establish complete corresponding source for the
WASM executable, native libraries, build recipes, other assets or architectures.
URLs are declared references; do not claim they were fetched or matched to each
module. The retrieved acknowledgement file has its own honest provenance.

Run focused safe/malformed ZIP, source/header/notice/source-reference binding,
no-overwrite export, drift and attempted-clearance controls. Reprocess the real
cached parent and all 614 nested entries. Retain failed controls; no dependency
install, runtime/model execution or paid service. Permission clearance and full
transitive/source-offer coverage remain false until their full criteria pass.
