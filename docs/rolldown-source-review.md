# Rolldown source and bundled notice review

Architecture before implementation: inspect the exact fifteen locked
`@rolldown/binding-*` 1.2.13 platform archives and their locked `rolldown`
wrapper, without installing or executing package code. Reproduce their existing
archive and member hashes, compare package/platform selectors with the wrapper,
and bind the declared upstream source and build metadata to retained exact bytes.

The wrapper already contains `THIRD-PARTY-LICENSE`. The generic notice-name
collector does not select this filename, and the native README inventory has
no corresponding declaration. This cohort must preserve the actual bundled
notice, compare it with the exact upstream source notice and refuse its loss
or replacement. A top-level MIT label is not a substitute.

Use bounded in-memory archive reads with strict regular-member, path, duplicate,
count and expanded-byte controls. Source tarballs remain private. Retain only
licenses and selected source/build metadata in a content-addressed public store.
The ordinary verifier is offline. A replay explicitly needs the existing npm
cache and the saved source archive; no install, extraction or reviewed code
execution follows from verification.

Risks: Cargo metadata lists possible source dependencies, not proof of the exact
compiled graph/features in each published addon. Platform names or source tags
do not authenticate compiler, binary origin or build reproducibility. Node,
libc/musl, Rust and linked native/runtime obligations remain explicit. Internal
build use differs from redistributing binaries. Preserve all existing false
permission/signature/full-coverage flags and original X-02/F-057 requirements.

## Implemented bounded result

The cohort verifier now binds the 15 platform addons and the `rolldown` wrapper at
version 1.2.13 to their actual site lock entries, existing notice archive hashes,
existing native members and their exact bytes. Explicit cache replay checks lock
SRI before inspecting any package, then package identity, OS/CPU/libc declarations,
wrapper optional dependencies, NAPI targets, and addon entrypoint/member hashes.
No addon or package script is loaded. ARM `linux-arm-gnueabihf` has no libc selector
in its package metadata; the evidence preserves `null`, rather than inferring one
from the target name. The current lock omits libc fields for six packages whose published metadata declares
glibc or musl; both observations are preserved without filling in the lock. These
are declared selectors, not verified ABI compatibility.

The wrapper archive contains `package/THIRD-PARTY-LICENSE` (2,209 bytes). The
existing generic notice inventory records only its `package/LICENSE` (1,302 bytes).
The new source/notice cohort retains both complete files as content-addressed
public text. Both match the pinned upstream source byte for byte. The third-party
file carries Rollup contributor and Evan Wallace/esbuild MIT notices. Its loss or
truncation now makes this cohort refuse verification. This is a usable supplemental
notice mapping; it does not silently rewrite the old observation or change the
shared collector's existing selection rule.

The pinned source's `build-binding.ts` names `rolldown_binding` and its Cargo
manifest. Its package NAPI targets match the published wrapper's targets; all 15
native target names appear in the retained release recipe. The extra declared
WASI target is recorded but is not one of this locked cohort's 15 native addons.
The source lock contains 406 package declarations: 353 registry entries and 53
workspace/path entries. Those counts describe the whole workspace lock, not the
compiled reachability, selected target features, bundled source or actual runtime
of any addon. `rust-toolchain.toml` declares channel `1.99.0`; it is recipe evidence,
not authenticated compiler identity.

## Run it

Ordinary verification is offline and checks the current selected lock/inventory
projection, exact preserved text, source relationships and false-clearance flags:

```sh
python3 -B scripts/verify-rolldown-cohort.py
python3 -B -m unittest discover -s tests -p 'test_rolldown_cohort.py'
```

A custodian holding the exact private archives can additionally replay them:

```sh
python3 -B scripts/verify-rolldown-cohort.py \
  --archive-dir /path/to/npm-archive-cache \
  --source-dir /path/to/pinned-source-cache
```

Each archive is capped at 64 MiB, each member at 32 MiB, and expanded archive
content at 300 MiB. Members are read in memory, never extracted; absolute paths,
traversal, duplicate names and unexpected links/devices are refused. The one exact
upstream test-fixture symlink is counted but never followed. Malformed/private CLI
arguments receive a fixed refusal without echo. Normal verification does not fetch
anything. The source archive hash is an observed checksum, not a verified publisher
signature or independent upstream archive checksum.

## What remains unresolved

This evidence does **not** approve redistribution or close X-02/F-057. The actual
compiled Rust dependency graph/features, mimalloc/native support code, Rust runtime
and platform SDK/system library obligations, binary/source equivalence and actual
compiler provenance remain unresolved. No dependency is declared paid or proprietary
because metadata is absent. Likewise an MIT package label does not clear the entire
binary. Source archives are privately retained; the exact public excerpts here are
not a complete corresponding-source offer. Distribution-specific inclusion of all
required notices/source/relinking material still needs an evidenced assembly path.
Internal build use and redistribution of addons are different routes, and this
cohort alone authorizes neither. Existing inventory permission/coverage flags remain
unchanged and false; other tag routes continue independently of this verifier.

## Primary sources

- [Pinned upstream source](https://github.com/rolldown/rolldown/tree/f7de35f45bcd4cb8e4b6d8d11e74fbfb20b03127)
- [LICENSE](https://github.com/rolldown/rolldown/blob/f7de35f45bcd4cb8e4b6d8d11e74fbfb20b03127/LICENSE)
- [Third-party notices](https://github.com/rolldown/rolldown/blob/f7de35f45bcd4cb8e4b6d8d11e74fbfb20b03127/THIRD-PARTY-LICENSE)
- [Binding build entrypoint](https://github.com/rolldown/rolldown/blob/f7de35f45bcd4cb8e4b6d8d11e74fbfb20b03127/packages/rolldown/build-binding.ts)
- [Release target recipe](https://github.com/rolldown/rolldown/blob/f7de35f45bcd4cb8e4b6d8d11e74fbfb20b03127/.github/workflows/reusable-release-build.yml)
- [Exact wrapper archive](https://registry.npmjs.org/rolldown/-/rolldown-1.2.13.tgz)
