# Artifact-linked SBOM and release decisions — architecture before implementation

Base: `40d85dfabcd6a3d97b84977992d0523b0995c0d9`. Isolated owner:
Codex `/root/share_debugger`, `codex/distribution-artifact-sbom`. The PM owns
shared scope, state, publication and final original-acceptance adjudication.

## Outcome and original boundaries

F-057 supplies an inspectable SBOM linked to the actual distributed artifact,
then an authentic Sigstore statement and outside-user verification of that same
artifact/SBOM/source identity. Source-snapshot signatures do not attest an APK,
OCI image or website. X-02 separately requires a complete technical dependency
conflict boundary. An accurate SBOM may retain `NOASSERTION`; it must not turn
unknown licenses, a package declaration or a policy refusal into legal clearance.

Implement one functioning mechanism across the existing fourteen registered
scopes, rather than adding another isolated package cohort. Derive actual
component graphs from trusted locked source, actual image SPDX observations,
pinned runtime/model assets and notice/source evidence. Preserve embedded/native
coverage gaps visibly. Model-card declarations are evidence; no LICENSE-filename,
professional legal approval or arbitrary binary-reproduction gate is invented.

## Proposed implementation

- A foundational stdlib artifact module derives all fourteen route graphs from
  closed trusted-source adapters. Package identity includes exact lock/archive or
  installed-image identity; files, graph and source digests are bound. Nothing
  in a received artifact or caller-supplied license label can approve a route.
- Capture the explicitly selected regular bounded artifact without following
  links; do not execute packages or extract received archives. Produce valid
  SPDX2.3 and a closed binding record for its bytes, route, source inputs, graph,
  notice/source evidence, unresolved observations and actual policy decision.
  Artifacts and external prerequisites remain distinct.
- A release-consumer interface verifies the exact artifact plus its graph and
  source snapshot before a reviewed release can proceed. Unknown/paid/closed
  decisions refuse. Existing ordinary development observations/builds stay
  explicitly unapproved and independent; personal PS remains available. No silent
  exemption or automatic approval is created for already working previews.
- Existing protected identity-based signing can attest the artifact and SPDX
  predicate. Detached verification captures bounded artifact, SPDX, bundle and
  separately trusted roots, invokes the real `gh attestation verify`, checks
  exact workflow/issuer/ref/source identity and verifies the returned statement.
  A carried digest, local key or mocked verifier is not an actual signing proof.
- A new standalone CLI supports graph inspection, generation, inspection and
  detached verification. Fixed diagnostics exclude private paths/content. New
  outputs are private, complete, no-overwrite and report publication uncertainty
  honestly; input drift and precommit failure cannot grant a released artifact.

## Ownership and integration

Own new foundational artifact/I/O module(s), CLI, focused tests and this plan/guide
plus fresh evidence. Necessary consumer integration is isolated and explicitly
listed for PM review; no shared ledger/state/UI is edited. Review current signing
and builder contracts before choosing exact integration files. Do not replace
existing notice, signing, PS or dependency controls. Changes to public build or
release entrypoints require the same exact source and failure checks as the new
interface; unused helper registration is not consumer enforcement.

## Risks and verification

Bound file sizes/counts/JSON/graph expansion and process time/output. Reject raw
path traversal, duplicate identities/JSON, stale or invented sources, forged
license decisions, mismatched artifact/SBOM/signature subjects, unknown scopes,
links, partial publication and overwrite. Preserve the independent PS route when
another scope is unavailable. No caller content, package execution, network
upload, new model/download, account or service is required for local generation.

Implementation precedes focused controls. Exercise real current PS packaging and
artifact generation/inspection, all fourteen trusted graph adapters, known
negative/fault cases and the actual detached verifier interface. Signing requires
real protected workflow execution before any signed-success claim. Do not run
broad repository/browser/native suites as a substitute. Full original closure is
not inferred from a route count or generated JSON: all applicable original
artifact, source/notice, policy and attestation acceptance must actually pass.


## Historical acceptance constraint retained

The F-057 ledger predecessor to9139eb57 explicitly retained complete client/build/
model/OS/architecture inventory, notices/licenses, scanner identity and runtime
release binding. The later conditional "before claiming license clearance" does
not silently erase that earlier retained scope. This implementation separates
working artifact/SBOM attestation from X-02 permission decisions without assigning
full-original closure. Declared/observed graphs and eligible PS signing do not by
themselves clear unobserved embedded/native terms or all other artifacts.

## Measured whole-source capacity amendment (before changing limits)

The exact root `1626cced2c4996859bef11edf364b18cd2474b03`, C2PA `41b8d52e`
union plus the current frozen NLI and owned artifact feature files contains
12,467 source files, 1,567,202 bytes of Git tree listing and 113,431,132 raw source
bytes (largest file 3,427,741 bytes). The minimized measurement receipt records
that this is a union measurement, not a completed combined commit or signing run.
The old 10,000 source-file and 12,000 graph-node ceilings cannot represent it.

Use a finite 16,384-file/node ceiling in both the committed-source archive and
artifact graph. Reject 16,385 rows before reading blobs or constructing nodes.
Keep the existing 2MB Git listing, 16MB packet, 32MB source-file, 128MB expanded
source, 64MB compressed archive, and all subprocess time/output limits. No source
or notice is omitted. A final actual combined committed-tree/archive/SPDX replay
must measure real packet and archive sizes and refuse if any unchanged byte cap
is exceeded. Counts alone do not authorize a release or resolve a license gap.
