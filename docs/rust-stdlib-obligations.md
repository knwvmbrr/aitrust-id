# Rust standard-library obligations in the selected MCP native wheels

This is a source/grant/notice map for the exact ten selected cryptography, pydantic-core and rpds-py native wheels. It supplies a concrete attribution artifact to the separate MCP distribution producer. It does not claim a reproduced build, exhaustive compiled closure, route admission, legal approval, tag accuracy or original closure. No compiler or package code was imported, installed, built or executed.

## Exact observations and publisher scope

All ten wheel and native-member SHA256 values were independently checked against the retained publisher bytes. All 532 recorded `/rustc/<commit>/...` path literals occur in those exact native members; they normalize to 176 unique commit/path pairs, all under `library/`. The three commits are:

- `48a229ceaefd4985c50990b14116b6d856af0985`
- `58cf8f9c35b355199727627d07ae34a4e2846d67`
- `b940084d7eb6a299eb4bfeb8e34901bc051e7ac4`

[Artifact bindings and literals](../sbom/mcp-rust-stdlib/wheel-source-paths.json) preserve exact identities; [the path grant map](../sbom/mcp-rust-stdlib/path-grant-map.json) records applicable publisher annotations and generated metadata. Paths are evidence of correspondence, not proof that every function/file or locked dependency was linked. No arbitrary local source path or executable was selected from those strings.

The old `.reuse/dep5` path returns404 at all three commits. The actual publisher [COPYRIGHT](https://github.com/rust-lang/rust/blob/58cf8f9c35b355199727627d07ae34a4e2846d67/COPYRIGHT) points to [REUSE.toml](https://github.com/rust-lang/rust/blob/58cf8f9c35b355199727627d07ae34a4e2846d67/REUSE.toml), `license-metadata.json`, and Cargo metadata. All176 observed paths independently agree between REUSE and the generated metadata. General `library/**` uses MIT OR Apache-2.0. Specific runtime grants remain separate:

| Scope | Exact evidence and treatment |
| --- | --- |
| Core Unicode tables | `library/core/src/unicode/unicode_data.rs` is explicitly Unicode-3.0, not covered solely by generic MIT/Apache. Its native path is positively observed for58cf8f9c. The complete1991–2024 Unicode copyright/permission/name-use notice is retained conservatively for all three commits; this does not assert the table was linked into every wheel. |
| Embedded backtrace | All three Rust commits identify the same backtrace-rs gitlink `d902726a1dcdc1e1c66f73d1162181b5423c645b`. Actual normalized backtrace paths occur for each commit. Full MIT/Apache texts and AlexCrichton/RustProject attributions are retained. |
| compiler_builtins0.1.160 | `alloc` directly depends on this in-tree runtime crate. Its more-specific Cargo grant is **MIT AND Apache-2.0 WITH LLVM-exception AND (MIT OR Apache-2.0)**. Retain the whole publisher LICENSE and its inherited compiler-rt copyrights/exception. Do not substitute the generic Rust root label. This runtime component is not the rustc compiler executable. |
| compiler-builtins libm | The three commits have the same exact libm/src Git tree `841d2a69b88ad0b87336be5f3d1e11b9f7214141`. All159 source files (691,681B) were read and checked against their Git blob SHA1 and SHA256. Full libm LICENSE and74 copyright/permission comment segments (22unique) are retained, including musl/Sun/Arm/CORE-MATH-derived attribution. This is a conservative source-cohort superset, not an all-files-linked assertion. |

The LLVM exception expressly permits qualifying compiled embedded portions without Apache sections4(a),4(b),4(d) conditions. Full terms are nevertheless carried, without inventing a whole-compiler source requirement. The source grant's AND and OR relationships are preserved.

## Standard-library dependency grants

Exact `library/Cargo.lock` files and std/alloc/core/unwind/panic/std_detect Cargo inputs identify the supported Unix runtime candidates and their dependencies. Eighteen distinct registry package/version archives were checked against lock checksums:13 reused existing source caches; five official archives added867,819B. They cover addr2line, adler2, cfg-if, foldhash, gimli, hashbrown, libc, memchr, miniz_oxide, object and rustc-demangle. Complete license/notice/copyright texts and Cargo/README evidence are retained in [the registry grant index](../sbom/mcp-rust-stdlib/registry-candidate-grants.json). Foldhash is **Zlib**, not generic MIT; other actual alternative grants remain visible. Optional features and linker participation are not inferred from lock membership.

WASI/Windows/SGX/Hermit and dev/test-only packages were not automatically treated as linked to the selected macOS/Linux artifacts. The nonshipped compiler-side LLVM wrapper, LLVM/GCC source trees, rustdoc fonts and compiler tests do not become distributed components merely because rustc built a wheel. The source map does not prove absence of every possible runtime component; that remains an explicit compiled-closure limit. The route author's separate wit-bindgen evidence is not replaced by this packet.

## Required artifact action and limits

Actually include [RUST-STDLIB-NOTICES.txt](../sbom/mcp-rust-stdlib/RUST-STDLIB-NOTICES.txt) in the assembled MCP distribution and bind its exact hash, the three source identities and ten wheel hashes in the artifact graph/notice check. It carries complete source-specific and dependency grants plus qualified coverage labels. Identical license texts are deduplicated with explicit references; copyrights in differing texts remain distinct. Source files and extracted byte ranges remain hash-bound. This branch supplies inputs; it has not performed artifact integration or the route's offline install/use/remove checks.

The generated release `COPYRIGHT-library.html` was not acquired: actual pinned REUSE/generated metadata/Cargo/licenses are used directly. This is not replaced with the entire toolchain copyright list, and no requirement for compiler installation, binary reproducibility, counsel or a paid account is invented. Exact enabled features, compiled-object closure and publisher build attestation remain unestablished. No source-disclosure/source-offer condition was identified in these retained permissive texts; that fact is not global commercial/legal clearance.

The [machine manifest](../sbom/mcp-rust-stdlib/manifest.json) and immutable execution record preserve scope and false claims. Additional official HTTP payloads total2,202,422B, below the initial4MiB and coordinated shared128MiB budget; the2GiB disk reserve was checked. No wheels, compiler executable, model, service or credentials are copied into Git.
