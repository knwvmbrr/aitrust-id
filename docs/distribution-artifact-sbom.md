# Bind a built artifact to an inspectable SBOM

This stdlib macOS/Linux developer tool links the exact bytes of an explicitly
selected artifact to fourteen **declared/observed** source-graph adapters. It
produces SPDX2.3 plus a closed binding packet, checks them against current trusted
source, and verifies a real GitHub/Sigstore SBOM attestation with separately
selected trust roots. Nothing is installed, extracted, imported from an artifact,
uploaded or executed during local preparation. Python3.12+ is required.

A hash or valid signature identifies bytes and a signer; it does not grant
licenses, approve every dependency or establish detector accuracy. Metadata is
not silently promoted to complete embedded/native coverage. `NOASSERTION` stays
visible. The existing X-02 route policy remains independent: only the exact
PS source distribution is currently admitted. Unknown routes may be inspected
or authentically attested, but cannot pass the managed-release authorization.
Existing personal checks and ordinary development builds are unchanged.

## Actual artifact, three local steps

Start in this source checkout. Use an existing new owner-private folder outside
Git, and explicit paths to your already-built artifact. Resolve temporary-directory
links on macOS. No existing output is overwritten.

```sh
artifact_dir="$(python3 -c 'import tempfile;from pathlib import Path;print(Path(tempfile.mkdtemp(prefix="aitrust-artifact-")).resolve())')"
source_commit="$(git rev-parse HEAD)"
python3 scripts/export-ps-source.py build --output "$artifact_dir/checker.zip"
python3 scripts/distribution-artifact.py prepare --route ps-source --artifact "$artifact_dir/checker.zip" --commit "$source_commit" --output "$artifact_dir/evidence.json"
python3 scripts/distribution-artifact.py spdx --route ps-source --artifact "$artifact_dir/checker.zip" --commit "$source_commit" --packet "$artifact_dir/evidence.json" --output "$artifact_dir/artifact.spdx.json"
```

`prepare` hashes the actual artifact, binds current source/graph/policy and creates
one complete private JSON file. `spdx` first independently reconstructs that packet
from current source and the same artifact, then writes the exact canonical SPDX
predicate. Recheck later with `inspect` and the same flags, omitting `--output`.
An NFC/text finding is not performed by this tool; the PS exporter separately
checks its canonical nine source-and-notice members before SBOM preparation.

The `--commit` value is the expected signer source commit selected by the operator
from a trusted channel. Preparation alone is not a cryptographic claim that those
working files came from that commit. Actual verification enforces the protected
signer's source digest as well as every captured current source hash. A received
packet cannot choose its own trusted route or source commit: both are required
again on inspection/verification.

## Fourteen scopes, actual observations and remaining coverage

Use `graph --route ROUTE` for a brief count; add an explicit private `--output`
to inspect source paths, hashes, components, relationships and gaps. Supported:

- `ps-source`: nine admitted source/notice members and canonical ZIP checks.
- `source-snapshot`: all committed Git blob identities, not a PS-only package.
- `web-checker`, `ios-app`, `android-app`: locked website packages plus pinned
  assets/runtime, retained notices and selected source evidence.
- `gateway-linux-amd64`, `evaluator-linux-amd64`, `anonymizer-linux-amd64`: each
  actual source-bound observed image SPDX package inventory.
- `nli-linux-x86_64`, `nli-macos-arm64`: separate locked packages, selected wheel
  artifacts, model/tokenizer hashes and recorded notice/source qualifications.
  With the independently checked NLI-native dataset, all 650 source/notice nodes,
  1,561 edges and 3,571 retained text hashes are bound. The actual GNU source-offer
  and ORT source identity gaps remain explicit; a notice section does not prove
  that its component was incorporated into a selected wheel.
- `c2pa-linux-x86_64`, `c2pa-macos-arm64`: selected platform wheel/artifact and
  notice observations. When the separately verified native source graph is present,
  all441published Cargo packages,1,131edges and2,518retained source/notice
  hashes are bound too. Published lock closure and135positive source labels per
  native binary are not a claim of complete compiled dependency coverage.
- `mcp-stdio`: the SDK's hash-required transitive Python lock, with all alternative
  hashes retained as alternatives rather than called installed artifacts.
- `node-build-tools`: both complete npm locks, dependency edges and optional
  platform alternatives, preserving build/optional distinctions.

The artifact itself has an exact checksum. Graph nodes are associated declared or
observed source material, using an explicit SPDX `OTHER` relationship rather than
claiming they are all contained in that supplied file. This is useful source-bound
SBOM evidence, **not** a fresh scan of an arbitrary binary, a full installed graph,
a complete corresponding-source offer, a license decision or release permission.
Native and embedded coverage remains a concrete separate obligation. Owner-chosen
OS/browser/hosting prerequisites are not relabeled open-source processing code.

## Real protected signing and detached verification

The accompanying protected-main workflow creates the actual PS source artifact,
creates its linked SPDX, uses the pinned official GitHub attestation action, and
verifies the actual resulting SBOM statement before offering its artifact. The
SBOM predicate type is `https://spdx.dev/Document/v2.3`. The exact expected signer
is `knwvmbrr/aitrust-id/.github/workflows/artifact-sbom.yml@refs/heads/main`, with
GitHub's OIDC issuer and no self-hosted runner. A local unsigned fixture, injected
verification response or PR build is not actual signing evidence.

Public downloaded evidence, SPDX, bundle and trust-root files may retain their
normal0644 permissions; they are regular no-follow inputs, not secret credentials.
Requested new outputs still require an owner-private0700directory and are0600.
For an actual downloaded artifact, evidence packet, SPDX, bundle and separately
trusted roots, use:

```sh
python3 scripts/distribution-artifact.py verify-attestation --route ps-source --artifact "$artifact_dir/checker.zip" --commit "$source_commit" --packet "$artifact_dir/evidence.json" --sbom "$artifact_dir/artifact.spdx.json" --bundle "$artifact_dir/sbom.sigstore.json" --trusted-root "$artifact_dir/trusted-root.jsonl" --output "$artifact_dir/verified.json"
```

GitHub CLI with artifact-attestation support is a separately trusted prerequisite.
The verifier captures the selected bytes in a new private directory, uses the real
`gh attestation verify` against supplied bundle/roots, and compares the complete
verified SPDX predicate and actual artifact subject. Its fixed command never uses
packet-provided executable/flags/endpoints. The helper has60seconds, a16MB JSON
file/output limit, bounded pipes and process-group cleanup. A2GiB disk reserve is
required after staging the artifact. Offline bundle/root verification does not
send the artifact or an input text to an API.

`authorize-release` has the same flags and verifies **both** current route policy
and actual attestation; a verified unknown route still refuses. It is the common
managed-release consumer for all14scope IDs. Passing authenticity alone returns
`release_authorized:false`. Existing builders produce development observations,
not an automatic call to this managed-release authorization. Broader consumer
integration and unknown obligations cannot be claimed complete from an unused
interface or the route count.

## Safety and failure

Artifact input is a regular singly linked file, at most1GB, hashed in64KiB chunks.
Source/metadata reads are at most16MB each,64MB total and256files. Graphs have at
most12,000nodes/30,000edges, with bounded source labels and JSON. The complete
packet is at most16MB. The tool reads trusted repository graph evidence; it does
not accept caller-supplied license approvals or arbitrary graph adapters.

All input paths are selected explicitly; no raw artifact content or private path
is printed. Only requested private output includes identifying hashes and source
metadata. Source/artifact drift, unknown scope, duplicate/malformed JSON, wrong
subject/predicate/source/identity, missing prerequisites, links and existing
outputs refuse with fixed `UNAVAILABLE`/exit2. No refusal becomes zero or safe.
Prepublication refusal creates no new final output; a cleanup failure can retain
private `.artifact-evidence-*` temporary bytes. After publication is attempted,
cleanup/fsync/close failures report `output_commit_uncertain` and
`output_may_exist:true`; inspect the requested destination and private directory
before retrying. The tool never promises rollback or forensic deletion.

Full F-057 and X-02 acceptance is a separate source/evidence decision. This tool
does not replace actual artifact coverage, applicable source/notice obligations,
protected signing execution or independent review with a test count.

Git source entries retain their exact Git blob OID and mode as source identity.
An OID hashes the Git header as well as content and is not labeled a plain file
SHA1 checksum in SPDX. Artifact and other actual content hashes stay separate.

The artifact-only child supervisor owns setup, selectors and pipes from spawn
through reap, never signals a reaped numeric process group, and attempts each
owned pipe close once. Its fixed deadlines and byte limits are unchanged. The
signing workflow initializes its temporary path at step execution time.

Whole-source archives and graphs admit at most16,384 committed files/nodes,
with the existing byte, path and wall-time limits retained. The measured union
requires this finite capacity; it does not claim an executed combined artifact
until a final source-bound replay is recorded.
