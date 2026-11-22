# C2PA native source and notice graph

This source-only companion gives the distribution graph an actual published
Cargo resolution instead of a generic Rust-dependency placeholder. It supports
F-057/X-02 evidence; it grants no distribution permission, release approval,
reproducible-native-build or tag/accuracy claim.

```sh
python3 -I -S -B scripts/verify-c2pa-native-obligations.py
```

Python3.11+ and the checkout are sufficient. This checks fixed source pins, all
retained manifest/license/notice material, every package/edge and current source
bindings. It opens and closes files sequentially; it does not hold thousands of
file descriptors. No network, installation, archived code or native library is
executed. Checkout-only consistency is not fresh artifact replay.

For fresh artifact replay, the exact checksummed public crate files belong in an
existing private cache outside the checkout. Every package's `source_identity.url`
and `archive_sha256` identify its official static.crates.io source. Pinned
upstream notice supplements use their recorded Git-blob/SHA256 identities and
`<sha256>.source` cache names. Existing selected wheels remain in their separate
previous C2PA cohort cache:

```sh
python3 -I -S -B scripts/verify-c2pa-native-obligations.py --cache-dir /absolute/private/crates --native-cache-dir /absolute/private/existing-c2pa-wheels
```

This rehashes and parses all441 archives, re-derives selected text records and
all1,131 lock edges, rechecks source supplements and scans the two exact native
members for bounded sanitized registry package/version labels. It still does not
execute code. Missing/changed archives, unknown retained files, incorrect edges,
changed license/source data or attempts to promote the false clearance flags
refuse with a fixed message and nonzero exit. Private argument values are not
copied to errors. The explicit `--collect --cache-dir ...` mode initializes a new
source-review cohort only; it refuses an existing manifest and never silently
replaces a reviewed graph. Existing pinned supplement/label observations remain
explicit collection inputs, not invented archive members.

## Evidence relationships

The Git commit's Cargo.lock URL really returns404. That historical observation is
preserved. Separately, the official `c2pa-c-ffi`0.91.0 crate contains Cargo.lock,
whose exact hash is hardcoded by this verifier. The archive checksum is
`612bffa120fdb58b5b6767602b0c0c77a20e139a7102b3e13e85236308ee49f4`;
its Cargo.toml.orig matches the previously retained source manifest exactly.
The crate's VCS metadata declares e7cc666c3409bdaf4cea8e49046dfbf8290dff89.
Cargo explicitly warns that VCS metadata does not guarantee every archived source
file equals Git; this tool preserves that limit.

There are441 exact package nodes and1,131 version-resolved edges in this
published package lock. Dependency declarations separately retain normal/build/
dev and target selectors plus optional features. The lock is a union resolution,
not an assertion that all nodes are incorporated into either native library.
Neither a missing label nor a missing edge proves absence from a native binary.

Both previously pinned native libraries contain135 matching sanitized registry
package/version labels. All are in the published lock. These are positive,
non-exhaustive source-version observations, not compiler authentication, complete
linkage, source equivalence or reconstruction of the exact release feature set.
Whole wheel/native hashes remain tied to the older observed C2PA artifacts.

There are2,518 retained distinct source/notice/declaration texts (8,639,460bytes).
Actual shipped LICENSE/COPYING/NOTICE/PATENTS/AUTHORS records are separated from
README declarations. Sixteen initial notice-filename gaps were investigated at
exact declared source commits. Separate upstream notice texts are labeled as
**not present in the selected crate**; they are never represented as bundled
members. Three packages have neither a shipped notice file nor a root source
license file at the pinned commit: btree-range-map0.7.2, range-traits0.3.2 and
static-regular-grammar2.0.2. Their actual README/Cargo declarations are retained;
no missing copyright text or permission conclusion is fabricated.

The graph preserves raw license expressions, including AND/OR alternatives,
Unicode/CDLA/MPL and legacy spellings. It does not silently choose a license or
call a successful parser legal clearance. Conditional source/notice requirements,
embedded/system code, exact compiled applicability, selected license alternatives
and distribution-specific packaging still belong in the owning distribution
policy. No outside-lawyer gate is invented by this evidence tool.

## Bounds and executed work

Individual compressed source archives are capped at16MiB; expanded reads128MiB,
individual members32MiB, retained text4MiB per package, member count20,000 and
packages1,000. Decompression is capped before extended tar headers are processed.
Unsafe paths, duplicate entries and non-regular/non-directory members refuse.
Sources are read through no-follow regular-file descriptors with size/drift
checks. Official registry fetches have per-operation timeouts and elapsed bounds,
a256MiB private archive-cache cap and at least2GiB free-disk reserve. No model,
large build tree, global package or local Docker operation is involved.

The actual source cache was approximately67MiB; no package/native code was run.
[Current five CLI controls](../runs/2026-11-22-c2pa-native-current-cli.json) include
checkout-only verification, complete private-cache/native replay and three real
refusals. An initial11-method focused run had10 passes and one test-fixture error
that expected only ValueError for a correct missing-file OSError. The three
affected fixed-lock/current-graph/refusal controls then passed; no unchanged broad
suite was repeated. [The source discovery record](../runs/2026-11-22-c2pa-native-source-discovery.json)
preserves the404 and actual remaining notice distinctions.

Primary references: [exact published FFI crate](https://crates.io/crates/c2pa-c-ffi/0.91.0),
[Cargo packaging behavior and VCS warning](https://doc.rust-lang.org/cargo/commands/cargo-package.html),
[Cargo manifest versus lock](https://doc.rust-lang.org/cargo/guide/cargo-toml-vs-cargo-lock.html),
[previous selected native artifact relationships](c2pa-cohort-review.md).
