# Optional C2PA source and notice evidence

This finite inventory covers ten locked Python packages and fourteen distinct
wheels from the existing macOS ARM64 / CPython 3.12 and Linux x86-64 / CPython 3.13
inspection workbenches. Shared wheels appear in both selections, for twenty
package slots. Other Python versions, platform alternatives and the live service
are outside this cohort. Nothing here changes SDK activation or tag validation.

From a downloaded checkout, with Python 3.11 or newer:

```sh
python3 scripts/verify-c2pa-cohort.py
```

The command checks exact current lock/parser pins, the retained source-tool bytes,
every preserved public upstream text, package identities, full wheel RECORD
inventories and selected source/native relationships. It makes no network calls,
installs nothing and never runs archived code. Checkout-only success checks the
retained observations, not a fresh download or binary execution.

To replay original artifacts, obtain the exact URLs/filenames listed in
[sbom/c2pa/manifest.json](../sbom/c2pa/manifest.json) into an existing private cache
outside the repository, including the ten PyPI JSON records, fourteen wheels,
ten source distributions, two native release ZIPs, release JSON and six pinned
Rust-source documents. Then run:

```sh
python3 scripts/verify-c2pa-cohort.py --cache-dir /absolute/private/cache
```

Replay rechecks whole-artifact hashes and sizes before parsing. It independently
reconstructs wheel metadata, RECORD digests, notice selections, Python-file
relationships and exact native release comparisons in memory. No archive is
extracted. Unsafe names, duplicate members, links/devices, encrypted ZIPs, hash or
size drift, unsupported metadata, missing selections and attempted permission
promotion refuse verification. Each archive is limited to 64 MiB compressed,
40 MiB per member, 160 MiB expanded and 10,000 members. Public text is capped at
4 MiB per retained document.

## What is established

The two c2pa-python 0.38.0 wheels contain no matching license-notice members. Their
version-matched source distribution supplies LICENSE-MIT and LICENSE-APACHE.
Those original texts are retained with their **source-distribution** member names,
not represented as files bundled in the wheels. The source pyproject explicitly
sets `license-files = []`; it remains available in the upstream source archive.

The four existing wrapper pins match source-distribution files exactly. The
native library in each selected wheel matches the corresponding member of the
upstream c2pa-rs 0.91.0 release ZIP exactly. Matching bytes identify those observed
artifacts; they do not establish which compiler, flags or dependency graph built
them. Other Python-file comparisons record exact matches at selected source
paths or explicitly record that no such match was found. Generated or unmatched
code is not silently called reproducible.

Official primary references:

- [c2pa-python 0.38.0 files and declared license](https://pypi.org/project/c2pa-python/0.38.0/).
- [Wheel format and RECORD requirements](https://packaging.python.org/en/latest/specifications/binary-distribution-format/).
- [Native 0.91.0 release](https://github.com/contentauth/c2pa-rs/releases/tag/c2pa-v0.91.0).
- [Exact release-commit workspace manifest](https://github.com/contentauth/c2pa-rs/blob/e7cc666c3409bdaf4cea8e49046dfbf8290dff89/Cargo.toml).

## What remains open

The retained Cargo manifests identify versioned source declarations, not a
resolved transitive native graph. The source-commit Cargo.lock URL returned 404;
the full source archive exceeded the 64 MiB retrieval cap and was not retained.
Selected source manifests and license documents were retrieved by exact commit.
Rust crate notices, OpenSSL/libffi and other incorporated code, resolved versions,
source offers, packaging obligations and unselected platforms still need review.
The native ZIPs include compiled libraries and headers, not a complete third-party
notice bundle. Matching Python/source records do not settle those obligations.

```sh
python3 scripts/verify-c2pa-cohort.py --require-clearance
```

This refuses with exit status 2. Evidence consistency is not legal permission,
vulnerability clearance, verified publisher identity, reproducible-build proof or
release approval. All five permission/build/graph flags remain false. X-02 and
F-057 remain open. Existing native/nested inventories are preserved unchanged.
