# esbuild platform source and notice review

Architecture recorded before implementation: review the exact 26 locked
`@esbuild/*` 0.28.1 archives independently from the wrapper and unrelated native
cohorts. Read binary build metadata without running any binary. Bind the lock,
existing observed archive/member identities and the upstream source/notice bytes.

The parser accepts only a unique aligned modern inline Go build-info header,
bounded varints/strings, strict UTF-8 and parsed module/settings records. Refuse
unsupported layouts and ambiguous headers. Archive replay checks integrity before
reading regular members, refuses links/unsafe or duplicate names, and enforces
member/count/expanded-byte limits. The exact esbuild source-only browser-test
symlink is counted without following it; it is not a selected notice or metadata
source. Other links are refused. No extraction or package/native execution.

Official source archives remain private. Public files contain exact license text
and selected build metadata only, addressed by their own SHA-256. Record observed
source archive sizes/digests, source declarations, toolchain versions and
unsigned/unreproduced relationships separately. A matching source version is not
proof the published binaries were built from it.

Risks: Go runtime and module code are additional components; a first-party MIT
label cannot clear them. Build metadata can be forged and is not publisher
attestation. Missing metadata does not establish proprietary or paid code.
Internal build use differs from redistributing compiled binaries. Changed locks,
source bytes, notice files or unsupported platform data must refuse verification.
Do not alter the existing inventory clearance flags or claim original X-02/F-057
completion from this bounded cohort.

## Observed result

All 26 exact lock-pinned platform archives were read in memory. Their 29 executable/native member
sizes and SHA-256 values match the existing native inventory. No binary
was extracted or executed. Every one of the 26 Go-code members (23 native plus three Wasm members)
lacks the 14-byte Go linker marker `ff 20 47 6f 20 62 75 69 6c 64 69 6e 66 3a`.
A `go1.26.4` literal occurs in each Go-code member, but a literal does not prove compiler identity.
The review therefore reports **build info unavailable** for all 26 Go-code
members. Three archives additionally contain a Node.js launcher, recorded
separately as scripts with a Node prerequisite; no Go metadata is attributed
to those launchers.

This is consistent with the exact upstream Makefile: its `go-compiler` target
modifies the Go linker to omit `ctxt.buildinfo()`. `go.version` declares 1.26.4;
`go.mod` declares the one external module `golang.org/x/sys` at
`v0.0.0-20220715151400-c0bba94af5f8`. These are recipe declarations, not a
reproduced build or authentication of the published executable.

The official Go 1.26.4 source confirms the exact marker, 32-byte header and modern
inline format. Its archive SHA-256 and size match Go's separate published
download metadata. The x/sys module ZIP's canonical Go `h1` digest matches
esbuild's retained `go.sum`. The esbuild archive has an observed SHA-256 and an
API-observed tag-to-commit relationship; no publisher signature or independent
archive-checksum verification is claimed for that archive.

Selected full MIT/BSD notices and Go patent grants travel with the review. Exact
build metadata excerpts retain their original bytes and line ranges. Selected Go
vendored notices are retained as source-distribution context; this does not prove
which vendored packages are linked into each executable. No model, image, app,
other native cohort or global scope percentage is cleared by this review.

## Use and redistribution boundaries

Internal use as a build tool does not itself redistribute the tool. If an
AI Trust ID distribution includes these binaries, retain applicable first-party
MIT and Go/x/sys BSD notices and grants with that distribution. Do not replace
upstream terms with this repository's Apache license. The retained MIT/BSD terms
do not impose a general corresponding-source or relinking offer requirement;
this is not an assertion about other dependencies or the complete shipped
license set. Exact compiled dependency membership, publisher authentication and
binary/source reproducibility remain unestablished. No paid or proprietary
requirement is inferred from absent build metadata.

## Offline checks

`python3 scripts/verify-esbuild-cohort.py` checks the public selected-input,
source-text and observation bindings. It reports that archive bytes were not
replayed. For actual archive replay, add `--archive-dir` pointing to the existing
205-artifact cache and `--source-dir` pointing to the four retained upstream
files listed in the review. The verifier makes no network requests, installs
nothing and executes no reviewed code. Unsupported build-info layouts stay
Unavailable. This profile deliberately does not accept a permission or release
approval flag.

## Upstream sources

- [esbuild source revision](https://github.com/evanw/esbuild/tree/bb9db84c02433fbe37b3509f53f9f3e3cc48725e), including `LICENSE.md`, `go.mod`, `go.sum`, `go.version` and `Makefile`.
- [Go source release](https://go.dev/dl/go1.26.4.src.tar.gz) and [download metadata](https://go.dev/dl/?mode=json&include=all).
- [Go build-info reader](https://github.com/golang/go/blob/go1.26.4/src/debug/buildinfo/buildinfo.go) and [linker](https://github.com/golang/go/blob/go1.26.4/src/cmd/link/internal/ld/data.go).
- [Pinned x/sys module archive](https://proxy.golang.org/golang.org/x/sys/@v/v0.0.0-20220715151400-c0bba94af5f8.zip).

Source archives remain in an owner-private cache. Public review files contain
license text and selected build metadata, with no private acquisition paths.
