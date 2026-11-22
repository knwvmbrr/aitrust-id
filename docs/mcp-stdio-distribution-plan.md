# Complete MCP stdio distribution: proposed implementation

This is an implementation proposal, not permission to distribute the SDK bundle.
The existing `mcp-stdio` optional-SDK route remains blocked. The current personal
PS source export and ordinary source-checkout commands remain unchanged.

## Outcome and boundary

Produce a reproducible offline installation ZIP containing the actual local MCP
server source, its complete selected 30-wheel runtime, exact applicable notices
and source references, an installer/launcher, and an artifact-linked SPDX graph.
The installed server must support both existing tools, PS, and the existing
optional PII client. It must retain the latter's validation sources rather than
silently making PII unavailable by omitting files. The privacy service, its
models, CPython, pip and the operating system are separate prerequisites, not
shipped or declared cleared by this package. No service credentials are copied.

The artifact is an optional-SDK runtime distribution. It is not another PS-only
source export. Installing the SDK must not become mandatory for the personal
checker. No HTTP listener, new endpoint, host permission, account or inference
service is added.

## Exact proposed artifact matrix

The target record [contains all exact filenames, SHA-256 values, sizes and
publisher URLs](../runs/2026-11-22-mcp-stdio-target-proposal.json). Each of four
targets has the same 30 locked package versions. The 26 pure-Python wheels are
shared; CFFI, cryptography, pydantic-core and rpds-py are native. There are 40
distinct publisher wheels totaling 21,811,126 bytes, before source/notices and
packaging. All 120 selected wheel references match hashes already in the lock.
These are metadata observations; no new wheel was downloaded or installed.

| Target | Wheel bytes | Explicit prerequisite |
| --- | ---: | --- |
| CPython 3.12, macOS arm64 | 8,716,572 | macOS 11 or newer |
| CPython 3.13, macOS arm64 | 8,716,029 | macOS 11 or newer |
| CPython 3.12, Linux x86_64 | 9,774,907 | glibc 2.34 or newer |
| CPython 3.13, Linux x86_64 | 9,773,661 | glibc 2.34 or newer |

The two Linux targets deliberately select the already retained publisher
cryptography `cp311-abi3-manylinux_2_34_x86_64` wheel. This is not a relink or a
substitution intended to evade embedded-library obligations. Preserve all
publisher bytes. Windows, musl, other architectures, free-threaded Python and
newer Python minors are not qualified by this proposal. The existing broader
source-development path is not disabled. PM must explicitly accept the finite
artifact matrix before a release profile is admitted; this plan does not silently
equate it with every possible installation of the hash lock.

## Current implementation gaps

`tools/dependency_policy.py` intentionally admits only the exact PS source
profile. Merely changing a component label in the JSON does not admit MCP:
`_evaluate` also refuses every other distribution scope. `require_route` is the
nine-source-file PS exporter contract and must remain compatible.

The current `Graph.mcp` records lock declarations and alternative hashes. It does
not verify a selected wheelhouse, its installed runtime or its native obligations.
An actual MCP format verifier and graph adapter must bind the selected target,
all wheel bytes and members, dependency edges, source files, notices and the
installed/runtime contract before policy can authorize that artifact.

## Applicable grant and notice work

Read each exact wheel's METADATA, WHEEL, RECORD, license/notice members and any
bundled source/SBOM records; validate hashes and dependency markers. Do not use
installed metadata alone as canonical wheel provenance. Retain complete shipped
notice texts and each attribution, including exceptions in individual source
headers. A license expression with alternatives does not automatically require
the most restrictive alternative: record the actual chosen applicable grant and
its conditions. Conversely, an unrelated permissive package label does not clear
an embedded library.

| Components | Observed licensing evidence and required work |
| --- | --- |
| Project Python sources | Root Apache-2.0 grant and `NOTICE`; preserve required attribution and modification information. Do not import/run the evaluator or service applications just to package their AST/identity inputs. |
| Assertion schema | `spec/LICENSE` explicitly declares CC BY 4.0. Include that scope, attribution, original source and a copy/link to the applicable full terms. Root Apache alone does not cover this file. |
| NFC table | Preserve the exact Unicode data grant/notice in `eval/vectors/unicode/LICENSE.txt`. |
| 26 pure wheels | Current installed declarations span MIT, BSD-3-Clause, Apache-2.0 and PSF-2.0. Inspect and bind each exact wheel's actual grant, copyright, NOTICE and any vendored exceptions. `rfc3339-validator` really ships its MIT grant despite lacking a License-File metadata field. |
| CFFI 2.1.1 | Root MIT-0 grant explicitly preserves separately stated exceptions. macOS binary observes system libffi; retained Linux wheel has no external libffi DT_NEEDED entry or separate libffi member. Identify the embedded FFI source/grant and required notice from pinned publisher build evidence. Its exact version/build mapping remains unresolved. Do not replace/rebuild its wheel to hide this gap. |
| cryptography 50.0.2 | Root Apache-2.0 OR BSD-3-Clause; wheel carries a 39-component Rust CycloneDX graph and a separate OpenSSL 4.0.3 component/source reference. Read exact grants/notices for the graph and OpenSSL source. The local native binary positively contains that OpenSSL version string. |
| pydantic-core 2.50.4 | Wheel carries a 101-component Rust CycloneDX graph. Resolve exact packages and applicable MIT/Apache/Unicode/Zlib/LLVM-exception grants, rather than treating the root MIT label as complete native coverage. |
| rpds-py 2026.9.1 | Wheel carries a 17-component Rust CycloneDX graph; bind exact sources and applicable MIT/Apache/Unicode/LLVM-exception terms. |

These SBOMs are useful publisher declarations tied to actual wheel members, not
independent exhaustive compiled-closure proof. Validate their identities against
exact source/lock artifacts; record the evidence role. Reuse existing retained
source/notice bytes only when the exact package/version/source checksum matches.
Preserve genuine unknowns and applicable source/offer requirements. Do not invent
a mandatory legal-professional approval or infer permission from a missing file.

## Complete source and consumer closure

Bind the actual imports and file reads, not only the two current policy entries:
MCP server, tag API and batch coordinator; PS CLI/worker/projection and evaluator
AST source; normalization/table; local privacy client/assertion schema; gateway,
anonymizer loader/lock and replay identity sources read by privacy validation.
Include the usage guide and applicable root/spec/Unicode notices. Enumerate this
closure mechanically and check all supported operations from an extracted copy.
Keep the API's existing optional privacy failure independent of PS.

Create a fresh private virtual environment without bundled pip, then use the
operator's explicit existing pip to install only the selected publisher wheels:
no index, no dependency resolution, no builds, hash checking, no bytecode output.
Pip officially supports managing a pip-free venv with `--python`; pin and report
the installer used in execution evidence. Verify the final environment contains
exactly the 30 intended runtime distributions and does not inherit site packages.
Do not ship the existing development venv or its extra build tooling. A venv's
absolute paths are not claimed reproducible: the ZIP bytes and selected inputs
are deterministic, while installation is a separately verified operation.

Use bounded regular-file reads, preflight ZIP central/local framing, safe fixed
paths/modes, no links/extras/duplicates, no overwrite, complete atomic output and
honest post-publication uncertainty. Failures must not echo input, private paths
or environment values. Installer output stays private and bounded.

## Proposed owned implementation files, after PM review

- New `tools/mcp_distribution.py`, `scripts/mcp-distribution.py` and focused
  `tests/test_mcp_distribution.py`: wheel/source/notice verification, deterministic
  bundle, safe offline installation and installed-consumer checks.
- New `sbom/mcp-runtime/` exact target manifest, dependency graph, grant/notice
  evidence and retained raw terms; new result/usage documentation and immutable
  execution receipts.
- Narrow reviewed integration in `tools/dependency_policy.py` and
  `eval/dependency-policy.json`: an explicit optional-SDK artifact profile, not a
  relaxation of the PS source profile or of the other twelve blocked routes.
- Narrow reviewed `tools/distribution_artifacts.py` MCP adapter/format validation
  and corresponding artifact-policy controls. Existing signing identity,
  repository/commit/predicate/subject checks remain mandatory.
- Only after source review: exact CI registration and existing guide link to the
  qualified installer; no unrelated website, state, scope or ledger edits here.

The shared integration paths above require an explicit PM ownership transfer
before editing. No such implementation or policy change is made by this plan.

## Done criteria and execution sequence

1. Acquire only the 40 selected canonical wheels and bounded exact official
   native source/notice evidence into a private cache; verify lock/publisher
   digests before parsing. No package source execution or native rebuild.
2. Finish the complete applicable grant/notice/source mapping for every shipped
   wheel/native component. A remaining unknown blocks admission of that target;
   it must not be hidden by a broad root-license label.
3. Build each target ZIP twice from the same frozen input set; require identical
   bytes, exact member inventory and canonical whole-artifact SPDX reconstruction.
4. On available matching macOS/Linux Python interpreters, install in owned private
   temporary environments offline. Run the actual official MCP client/server:
   discover exactly two tools, obtain PS finding/no-finding, reject malformed and
   oversized requests, preserve cancellation/capacity, no input echo, and recover
   PS when optional PII is unavailable. Unsupported targets remain refused, not
   counted as executed. No new interpreter install is authorized by this plan.
5. Exercise missing/extra/tampered wheel, false license/notice/source identity,
   incompatible target, altered graph, link/path attacks, existing output and
   post-publication uncertainty controls. Check the existing personal PS route
   still works without the SDK and that no network is required by the installer.
6. Distinct source/evidence review, then admit only the complete exact target
   profile. Use the existing protected attestation mechanism on the real admitted
   artifact and verify it independently against caller-selected repository,
   commit and trust roots. Fake GH controls are not signing evidence.

## Remaining risks and authority limits

The Linux CFFI embedded-FFI mapping is a concrete unresolved technical task, not
an owner-only gate. The 40-wheel set is now exact but canonical bytes/RECORDs and
all native grants are not yet replayed. Available CPython 3.12/3.13 interpreters
on both test systems must be checked before promising four actual installations.
If a publisher wheel cannot be adequately mapped, propose a separate explicit
target with full build/source/compiler binding; never silently substitute it.

No new account, paid dependency or model is presently identified as necessary.
This plan does not authorize new installs, downloads beyond reviewed bounded
inputs, or policy permissions. Completing this route alone is not full F-057 or
X-02 closure, independent detector accuracy, an operating privacy service, or
clearance of every project distribution.

Primary references: [pip repeatable installs](https://pip.pypa.io/en/stable/topics/repeatable-installs/),
[pip managing a different interpreter](https://pip.pypa.io/en/stable/topics/python-option/),
[wheel format and license/SBOM directories](https://packaging.python.org/en/latest/specifications/binary-distribution-format/),
and [cryptography 50.0.2 installation](https://cryptography.io/en/50.0.2/installation/).

## Approved phase 1: exact inputs and a working development bundle

PM accepted the four-target artifact contract and the named implementation files.
Acquire only the selected publisher wheels and exact official source/term inputs
in a private project cache: at most 32 MiB per additional input and 128 MiB total,
with at least 2 GiB free throughout. Verify expected digests before parsing. No
interpreter, operating-system or global package installation is authorized.

Implement the complete deterministic bundle and safe installer as development
tools even while admission is blocked. Format validity and functional operation
must remain distinct from distribution approval. There is no caller-controlled
approve/ignore-obligations switch. Any later policy integration must still refuse
the route until the exact source/notice, format, runtime and distinct-review
criteria are met. Do not turn source-bound publisher SBOM observations into an
unsupported claim of complete compiled closure.

PM approved one measured archive exception before its acquisition: the exact
OpenSSL 4.0.3 publisher source is 55,235,667 bytes, SHA-256
`325b5c806167c13b40b1ffeadfe0248197c00eccc4cf123ec1e28d2d2fd216d9`.
This one input may exceed 32 MiB compressed; the total new-input budget remains
128 MiB and free-space reserve remains 2 GiB. Stream size/hash validation before
parsing; bound expansion to 512 MiB, 100,000 members and 32 MiB per member. Refuse
larger members rather than silently omit obligations. No filesystem extraction,
package execution, test-key/corpus retention or source build is authorized.

The source replay now has a finite 150-archive input set: 146 exact registry
components declared by the wheel SBOMs, the three Python native source roots and
OpenSSL. A separate standard-library collector validates compressed size/SHA
before parsing; its tar reader bounds metadata before allocation and performs no
filesystem extraction. Retain actual source notices and leading runtime comment
notices; do not retain test keys, corpora or arbitrary source bodies. Consolidate
deduplicated raw terms into one artifact asset with exact byte ranges/hashes and
per-package source/notice links. Preserve wheel publisher graph declarations
separately from complete compiled coverage. The observed three Rust source
commits require their own standard-library exception review before admission;
their root MIT/Apache texts alone do not close those exceptions.

The artifact adapter will verify the received MCP format before preparing an
artifact-linked SPDX packet, bind its exact target and profile digest, and select
the actual 30 wheels for that target. A cache-free route inventory may show the
union of all 40 qualified wheel candidates, with explicit observed/declaration
roles. The exact SDK dependency graph propagates the SDK's required PyJWT crypto
extra and evaluates only the finite, reviewed metadata-marker/version subset;
it never evaluates Python or accepts arbitrary requirements/URLs. Keep selected
wheel, source/notice and publisher-declared native edges distinguishable.

The dependency-policy consumer will validate the selected MCP source profile but
continue returning blocked pending runtime/notice/reviewer acceptance. This is
not an approval switch, and its optional import is selected only for MCP: a
broken MCP profile must not affect the admitted nine-member personal PS route
or change the other twelve refusals. No signing workflow or permission changes.

Installed verification will check every unchanged wheel payload against its
RECORD-derived hash, not only package version labels. Pip-generated RECORD,
INSTALLER, REQUESTED and direct-url metadata are separate permitted metadata;
unknown packages, code or path links are refused. The finite wheels contain no
`.data` relocation or `.pth` payloads, so unknown layouts are unsupported. Add an
explicit private-connection verification and a bounded actual SDK stdio probe;
derive launch paths from the validated workspace rather than executing commands
chosen by a received configuration. The probe uses only fixed invented examples
and reports canonical mechanism parity, never independent detector accuracy.

Preserve the existing HOME value unchanged. Task-specific temporary/configuration
paths, isolated Python/pip, a null pip configuration and no-index/no-deps flags
provide the required boundaries without redirecting HOME or reading credentials.

## Measured source-budget amendment

Root's current source plus pending image evidence leaves only 6,535,879 bytes
under the unchanged 128 MiB source-archive limit. The new MCP/CFFI/Rust candidate
adds about 6.96 MB. Canonical whitespace compaction alone saves only 459,639 bytes.
PM therefore approved storing the newly authored machine graph as one lossless
gzip member: 317,836 bytes instead of 1,803,304, with the exact original expanded
SHA-256 `c26b2f4503739275a5f6d8f7686de052a5de065d3016f51293185fcc25cb6675`.
No graph field, relationship, source identity or raw notice is removed. The raw
1,112,353-byte combined notice and all immutable component data remain unchanged.
Historical plain-JSON candidate artifacts and execution facts remain historical.
The reader accepts one fixed gzip framing only, at most 2 MB compressed / 4 MB
expanded, and refuses truncation, trailing data, concatenated streams or overflow
before existing JSON/schema validation. No global archive or descriptor cap rises.

The source review also found and corrected a prerequisite verification gap:
installed payloads and a launch-path match alone do not establish that the
current interpreter still matches the artifact. `verify-install` now repeats the
fixed five-second isolated stdlib ABI/platform probe and refuses a mismatched
target before any SDK probe. The original counterexample and the genuine earlier
selected-platform pass remain separate historical evidence.

The pinned MCP2.3.0 client deliberately launches its server in a separate session.
The authored probe cancels inside its contexts at25 seconds so SDK shielded
teardown (stdin close, bounded graceful/TERM/KILL stages) can finish before the
outer45-second supervisor. The outer group guard owns the probe process; it is
not a guarantee of reaping an SDK-detached server after an abnormal hard timeout
or an unkillable OS process. Such failure is Unavailable, never a healthy proof.
Normal completed-session observations are distinct from that unexercised limit.

## Proposed actual four-target CI

Use one narrow read-only workflow with four fixed matrix jobs: standard public
GitHub `macos-15` arm64 and `ubuntu-24.04` x86_64, each CPython3.12 and3.13 from
the already approved setup-python action. There are no paid/larger runners,
project dependency installs outside the owned private venv, containers, secrets,
service calls or signing. Confirm actual ABI/architecture, never trust the label
alone. Retain all four outcomes (`fail-fast:false`); any failed job makes the
workflow fail. Upload bounded JSON evidence only, not the unadmitted wheelhouse,
bundle, installation configuration or private paths.

A new dispatch-only workflow cannot be invoked before default-branch registration.
Therefore the proposed workflow also has a narrowly filtered `pull_request`
trigger on its own file and the exact MCP source/data/consumer paths. After PM
and distinct workflow review, one ordinary changed-source draft PR can execute
all four targets before main. Subsequent manual dispatch is available only after
normal registration. Do not open/push/dispatch it before that approval. Existing
protected workflows and release permissions remain unchanged.


## Current execution and capacity boundary

The earlier selected macOS CPython 3.13 artifact completed all eight fixed SDK
controls, including complete canonical records and optional privacy failure
isolation. That result predates the actual-interpreter verification repair and
lossless graph encoding, so it is historical evidence rather than a current
four-target claim. The corrected format candidate was built twice identically
for all four targets; its later local install returned exit 2 without a connection
file. The original refusal did not identify its internal stage. Measured free
space was below the retained 2 GiB reserve, consistent with the capacity gate.
Do not call that measurement a captured root-cause trace. Further local runtime
execution is paused. A new fixed capacity diagnostic refuses before creating a
workspace or spawning an installer; its focused inert control passed.

Only positively owned completed installation workspaces were removed, after
preserving their configuration and payload-inventory digests. Archives, exact
publisher wheels, sources, grants, execution records and unrelated files remain.
Historical connection files referring to those removed workspaces are not live
connections. No interpreter, package, disk reserve or HOME setting is changed.

The proposed CI records the actual isolated stdlib target observation before
acquisition, not just a runner label. GitHub's current public runner table lists
`macos-15` as M1 arm64 and `macos-15-intel` separately:
https://docs.github.com/en/actions/reference/runners/github-hosted-runners
The four jobs use those standard included public runners, no larger runners.
Each job binds build, install and full eight-case SDK proof to the same exact
artifact. It reconstructs the selected-target SPDX packet and confirms the
managed consumer refuses the still-blocked policy before invoking a signature
verifier. This is unsigned enforcement evidence; no cryptographic release or
whole-route acceptance is implied. The workflow has only been parsed and its
inline Python and shell syntax checked locally. Actual hosted outcomes remain
pending PM review and an ordinary changed-source run.
