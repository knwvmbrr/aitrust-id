# Visual baseline and next executable capability

Codex / web_camo, 2026-11-22. Read-only planning at exact source
2f03b9de (full commit in accompanying JSON). No root, policy, catalogue, scope,
state or deployed source changes. No model, SDK, browser or native-code run.

## Decision

Build one **local JPEG Content Credential and recorded-action reader with explicit
trust scope**. This is beyond metadata because it actually verifies the attached
record's signature/content binding and reads only its bound action assertions.
It is not an image-origin classifier, a VLM, an FA/PA issuer or a new protocol.

Do not write another PNG declaration wrapper. The existing pinned PNG inspector
already does that job. Its JSON/text contracts and source bytes should stay
unchanged. The concrete user gap is that an ordinary JPEG photo cannot currently
use that reader. The browser's useful new PNG/JPEG preview reports container
facts only and correctly does not pretend to verify a Content Credential.

This proposal is a complete bounded component, not completion of T-FA/T-PA/F155,
and does not change any of the202 criteria or existing counters.

## Actual inventory

| Existing code | What actually works | Gap that remains |
| --- | --- | --- |
| tools/manifest_inspection.py; scripts/inspect-manifest.py | Native pinned c2pa-python0.38.0/SDK0.91.0, PNG only, local10MiB input, separate binding/signature/trust/revocation,12s child, no remote manifest/OCSP lookup | JPEG/video refused; no browser-compatible native library; configured trust source is not an origin verdict |
| tools/manifest_declarations.py; action-declarations-v1 CLI | Bound active PNG action claims for c2pa.created+trainedAlgorithmicMedia or c2pa.edited+compositeWithTrainedAlgorithmicMedia, strict URI validations,128action cap, Unknown for regions/templates/related references/ambiguous inception | Real JPEG input unsupported; declarations still do not establish full generation or human rework |
| ImageMetadataExplorer + fixed PNG/JPEG AST cohort | Private browser file container/header/category observations, no raw values/hash by default, full-record binding, failure isolation | No cryptographic Content Credential, watermark or pixel-origin verification |
| services/adjudicator/verdict.py, adjudicate.py, tag_bridge.py | Pure supplied-status/claim lattice and research rollup, subject checks, conflict/refusal rules | No real media verification adapter. The bridge's FA claim requires generation without human intervention; PA requires generation followed by human rework. Current C2PA action pairs do not establish either complete claim. Do not wire them to those values |
| tools/synthid_input.py and optional check-tags input | Official token-only research-statistic input with explicit unbound relation to PS text | Not a Google production image detector, no production key, no trusted decoded watermark/FA/PA result. F155 remains open |
| protocol/reserved_subjects.py/.cjs; spec/subject-profiles.json | Supplied decoded-pixel/sample/frame reference identities; video timing/Merkle primitive | No video-file decoder or video detector. F062's recorded100% is explicitly the reserved subject-definition job, not a working video engine |
| RFC0003 | Six reserved wire modalities, current runtime evaluates text | No adopted3D value. NeRF is an existing reconstruction technique, not a project origin detector or automatic3D conformance; any future3D modality needs its own RFC |

No VLM or NeRF implementation/model weight was found in the inspected project
paths. The existing quiet-layer architecture explicitly separates OCR/VLM
extraction from origin/authorship/truth. Root owns the broader VLM/3D research
plan; this deliverable requires no VLM/model/weights/hardware-license decision.

## Contract and user-visible result

Proposed new CLI: `python scripts/inspect-jpeg-provenance.py --image photo.jpg`.
Default short text prints controlled words only: supported/unsupported inspection,
attached record or none, asset binding, record signature, signer trust under the
named policy, revocation status and a producer's supported creation/edit claim.
It always states that origin/authorship/truth are not established and issues no
tag. It never prints the path, filename, signer name, embedded text, GPS, URLs,
thumbnail, full report or asset hash. No automatic save, upload or sharing.

An explicit `--json` choice returns a bounded closed versioned observation with
encoded-file SHA256/byte count, active-record/action identities as bounded
ordinals, source/method/pin hashes, exact trust-context hash and separate axes.
Warn that the fingerprint can link copies. This is an encoded JPEG identity,
not the reserved canonical decoded-image subject hash; never substitute one for
the other. No raw SDK report/export option in this first component.

An optional `--trust-anchors` reads only an explicitly selected local public PEM
bundle (at most64KiB/four certificates). It is not a URL, secret key or global
trust-store change. Default remains the pinned SDK trust context; extra anchors
are used per invocation only. Hash the public trust policy and retain whether it
was selected by the caller. Report only SDK-established trust relative to that
context, never institutional endorsement. First prove the exact pinned SDK's
setting semantics with synthetic roots; current main-branch docs are not enough.
If that cannot be proven, refuse the anchor profile rather than weaken trust
verification or silently accept a leaf/allowlist.

Supported JPEG: the existing reviewed8-bit baseline/single-scan subset, at most
10MiB/4M header pixels/4096markers with explicit APP/JUMBF bounds. No pixel or
entropy reconstruction. Well-formed unimplemented progressive/multiscan/etc is
Unsupported, not AI-made, corrupt or malicious. APP11 presence alone is opaque.
Validate an attached credential only through the pinned SDK's image/jpeg Reader.

Declaration reading uses only the active manifest from the same native call.
Require positive active data-hash, signature and exact action-assertion hashedURI
bindings before describing the claim. Do not adopt ingredient-only claims,
unknown/custom source values, templates, regional/related assertions, conflicting
bindings or multiple inception actions. Missing declarations remain Unknown.
Recognized generative editing is not proof of subsequent human work. Preserve
untrusted signers and unknown revocation as separate facts, never fake Valid.

## Architecture / exact proposed ownership after approval

New files only:

- tools/jpeg_provenance.py: descriptor-bound immutable input/trust snapshot,
  fixed MIME/native child, strict result validation and text/JSON projection.
  Reuse the existing verified SDK loader/status helpers as a foundation; do not
  alter the PNG entrypoint, settings, default formats or method versions.
- tools/jpeg_provenance_actions.py: a separately versioned strict JPEG
  declaration profile derived with attribution from the current PNG logic.
  Bind that source identity and add parity/refusal controls for shared semantics;
  do not mislabel JPEG as the old attached-png profile or refactor its source.
- scripts/inspect-jpeg-provenance.py: actual public CLI, fixed worker mode,
  controlled failure strings, default text and explicit minimal JSON.
- tests/test_jpeg_provenance.py; tests/fixtures/jpeg-provenance-v1/generate.py
  and owned synthetic JPEGs/identity manifest. No private test keys on disk.
- scripts/verify-jpeg-provenance.py: source-bound actual supported/failure CLI
  checks, with exact SDK/platform identity and privacy-safe structured outcomes.
- docs/jpeg-provenance-plan.md, guide and result, plus attributed run/change
  records in the isolated implementation branch.

A small fixed source binding to the reused JPEG container preflight and loader
must fail closed on dependency/source drift. Do not dynamic-load arbitrary code
chosen by packet JSON. Existing metadata browser/PNG inspector/PS/MT remain
independent if this optional environment is absent or fails.

Root later owns any existing manifest-inspection workflow registration, guide
entry, catalogue/policy/source-inventory update and protected/public integration.
No server endpoint, web image upload or gateway modality change is proposed.

## Resource, network and ownership limits

Check encoded-file size/type/link/identity before allocation and recheck the held
file after reading. Send bytes, not the user path, to one freshly owned process.
Use12s wall/8s CPU/4MiB raw SDK report/32KiB public JSON limits, core dumps off,
clean0700 working space and Linux1GiB address-space containment. Reuse already
pinned dependencies; no weights/GPU/service/background install. Inspect the
pinned SDK's decode/backing-store settings before enabling JPEG, and refuse any
unbounded behavior. Bound trust decoding/certificate count before native use.

Keep per-reader verify_after_reading/trust/timestamp verification enabled;
remote_manifest_fetch=false, ocsp_fetch=false, allowed_network_hosts=[] and
identity assertion decoding disabled. Do not follow credential/ingredient URLs,
fetch a remote manifest, scan a local network, resolve a URL argument or update a
trust list. Linux acceptance must observe kernel network isolation and a local
network canary; fixed SDK settings on macOS alone are not kernel no-egress proof.
OCSP is never silently fetched: revocation stays unknown unless a specifically
supported offline response is validated with its scope/time. No false fresh or
not-revoked conclusion from a valid signature. Native fault containment is not a
complete sandbox or protection against a compromised host.

Close/kill/reap only owned pending processes. Guard known reaped IDs. Handle
spawn/selector/clock/pipe/close failures, cancellation and repeated cleanup
without leaked native children or signalling unrelated replacements. The API
lane's corrected supervisors are reference patterns, not blanket inherited proof.

## Executable acceptance (before calling this component complete)

1. Actual same-pinned-SDK JPEG created/edit-declared/unsigned/altered fixtures;
   whole closed records checked, exact encoded-file identity and expected active
   binding/signature axes, untrusted versus explicitly selected-root outcomes.
   These pixels and declarations are authored synthetic controls, not measured
   AI-generated image ground truth.
2. Ingredient-only, wrong active signature URI/action hash, missing declaration,
   ambiguous inception/templates/regions/related scope, malformed/unknown type,
   positive+failure conflict, expired/revoked/unknown statuses; never issue tags.
3. Valid-but-unsupported JPEG variants, truncation, trailing bytes, marker/count/
   APP/integer/size limits before native entry; report limits and worker failures
   separately from no attached record. SDK absence/hash/platform mismatch is
   Unavailable for this tool only.
4. Intrinsic file/trust limits, links/FIFOs/drift, report-output overflow/deadline,
   cancellation/kill/reap and known-reaped fault controls. No-overwrite if a
   later explicit export is proposed; none is needed for the first CLI.
5. Default stdout/stderr has no private metadata/path/hash/URL; explicit JSON
   includes only the documented linkable evidence. No automatic input save,
   network lookup, research/training permission or model invocation.
6. Actual isolated install/use/removal on each claimed platform, disk reserve
   before setup, offline/no-egress controls where claimed, PS and existing PNG
   inspection unchanged before/after optional environment absence/outage. Do not
   download/install locally while the2GiB reserve is unavailable; use approved
   existing hosted slots/caches after root schedules actual execution.
7. Distinct source/evidence review, exact current receipts, normal attribution
   and protected source publication. No FA/PA/F155/full-original completion or
   independent accuracy credit from passing synthetic software controls.

## Primary sources read for this decision

- [C2PA2.5 technical specification](https://spec.c2pa.org/specifications/specifications/2.5/specs/C2PA_Specification.html#_binding_to_content): hard asset binding is distinct from signer trust and truth; sections12.2,13.1,14.7–14.10.
- [C2PA action assertions](https://spec.c2pa.org/specifications/specifications/2.5/specs/C2PA_Specification.html#_provenance_workflow): recorded actions/source types and allActionsIncluded are generator statements; sections16.4.1 and16.9.1 govern templates/regional metadata.
- [C2PA revocation](https://spec.c2pa.org/specifications/specifications/2.5/specs/C2PA_Specification.html#_validate_the_credential_revocation_information): offline/stapled/current revocation has its own validation rules; no conclusion is manufactured by skipping a fetch.
- [IPTC generative edit source type](https://cv.iptc.org/newscodes/digitalsourcetype/compositeWithTrainedAlgorithmicMedia): describes generative enhancement, not proof of human rework or full origin.
- [Official Python reading API](https://opensource.contentauthenticity.org/docs/sdk-repos/c2pa-python/docs/usage/): local JPEG Reader and context exist. This current documentation is not execution proof for the project's pinned0.38/0.91 build.
- [Official context settings](https://github.com/contentauth/c2pa-python/blob/main/docs/context-settings.md): verify/network/anchor settings need exact-version confirmation; never copy permissive defaults from main into the pinned adapter.

The selected wheels/versions/digests and source/notice records already exist in
eval/c2pa-inspection.lock, eval/dependencies/c2pa-inspection.json and the retained
C2PA cohort/native graphs. They record MIT OR Apache-2.0 and transitive terms;
this task does not provide blanket distribution/legal clearance. No VLM code or
weights were acquired or their license/hardware suitability claimed, because the
selected deterministic cryptographic inspection does not need them.

Video BMFF action/binding adapters, frame decoding/temporal reasoning and VLM
caption/OCR observations can follow only as separately specified capabilities.
Descriptions/inferences are not positive forensic origin evidence. 3D/NeRF
reconstruction requires an explicit future modality/subject-coordinate RFC and
its own rights/evaluation/hardware contract before any live enum or tag support.

## Implementation authorization before feature edits

Root approved this full bounded working CLI increment after the read-only plan.
Use new JPEG-only modules, an independent pinned-SDK loader and existing exact
c2pa0.38.0/SDK0.91.0 lock bytes. Do not change PNG source, PS/MT, applications,
gateway, shared state or existing workflows. Native qualification is pending
review of a narrowly read-only hosted workflow; no local install/build below the
2GiB reserve. Preserve all historical sources and20percent FA/PA gates.

## Qualification-only amendment after first hosted failure

Run45040187485 installed the exact existing lock and passed15 focused controls,
then stopped at the environment check before native execution. The nonroot
`/proc/1/ns/net` read depends on procfs ptrace permissions and was an unsuitable
mandatory witness. Exact exception was not captured, so the first failure's
specific syscall is not asserted. Capture the original namespace identity in the
outer reviewed shell, verify a different self namespace inside unshare, and pass
that fixed-format identity to the dropped-privilege driver for its own self check.
The driver also records only a fixed accessible/permission-denied result for the
init-namespace read. This does not waive nonroot/network isolation or change any
CLI/parser/action/timeout behavior. First artifact and source remain immutable.
The amended qualification additionally clears supplementary groups, drops all
capability sets and sets no-new-privileges before the driver. The driver requires
actual effective capabilities zero, no-new-privileges one and no supplementary
groups. Inert current tests refuse a missing/same namespace identity, root UID,
retained capability, missing no-new-privileges or retained group before SDK work.
