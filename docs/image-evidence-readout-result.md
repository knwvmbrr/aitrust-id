# PNG evidence readout — component result

Implemented by Codex, image-evidence engineering lane, 2026-11-16.
Source branch: `codex/image-evidence-increment`, based on `2739570`.
Integration/wording review remains with the PM. Nothing is committed or published
by this result record.

## What changed

The existing PNG inspection command now offers `--format text`. Previously its
only output was technical JSON; the separate observations required a reader to
interpret fields such as `matched`, `untrusted` and `unknown_skipped` themselves.
The new view gives fixed explanations for each axis, preserves contradictory
observations, and explicitly answers **AI origin: Unknown**.

```sh
python scripts/inspect-manifest.py --image tests/fixtures/c2pa-inspection-2026/altered.png --format text
```

The actual altered-fixture output retains both statements:

```text
Image binding: Does not match the recorded image bytes.
Record signature: The record signature matches.
Signer trust: Not trusted by the configured trust store; this alone is not fraud.
Revocation: Unknown. Online revocation checks are disabled.
AI origin: Unknown. This method does not determine whether AI made or edited the image.
No tag issued. Image contents and authorship are not verified.
```

Default JSON and explicit `--format json` retain the consumer shape and exit
semantics. Text output never interpolates embedded assertions, names, locations,
URLs, paths, hashes or arbitrary validation messages. Unknown axes and malformed
envelopes are refused before private export. An explicit full-report export stays
a separate private action and can contain identifying metadata.

## Executed evidence

| Check | Observed result |
| --- | --- |
| Existing parser/fault/pin tests, new presentation tests and workflow inventory tests | 96 passed, zero failures/skips |
| Actual pinned SDK, macOS arm64, non-root | 21 CLI controls passed; source identity unchanged during execution |
| Signed / altered / unsigned PNG text | Separate binding/signature/trust/revocation; AI origin always Unknown; no tag issued |
| Loader shadowing, ambient loader override and in-checkout environment | Existing reviewed-package protections still pass |
| Malformed/unsupported/oversized/linked/missing input and private export | Original refusals retained; text failure and private export exercised |
| Prior CLI versus candidate default JSON (signed, altered, unsigned, missing file) | Actual stdout bytes and exit statuses identical in all four cases |
| Parser, SDK pins and image-origin exclusion policy | Byte-identical to base |

[Component receipt](../runs/2026-11-16-image-evidence-text-component.json) includes
the three actual fixed-fixture text outputs. [Real SDK receipt](../runs/2026-11-16-image-evidence-real-sdk-mac.json)
binds all inventoried sources, pinned fixtures, package/native versions and
per-reader settings. [Prior/candidate JSON comparison](../runs/2026-11-16-image-evidence-json-compatibility.json) records actual compatibility results. Tests include native crash/timeout simulations, malformed
axis/envelope refusal, absence of private/terminal-control markers, unchanged
default JSON, unknown revocation and an intact signature with mismatched binding.

## Scope and remaining gates

- **F-025 remains 100%** for its previously accepted bounded PNG parser job. This
  readout is an additional presentation component, currently 60% (contract,
  implementation and executable checks); it is not a newly completed detector.
- **T-FA and T-PA remain 20%.** No generator-origin claim, classifier, watermark
  reader, human-authorship verdict, image tag or identity credential is issued.
- **X-07 remains unchanged.** The text-only gateway, tag enum and release allowlist
  are untouched. Optional image inspection cannot disable personal tags.
- Fresh isolated Linux execution and PM review of this exact readout remain
  pending. Current optional CI triggers include the new formatter and test source.
- No physical-device, independent accuracy, full provenance validation, kernel
  no-egress guarantee on Mac or complete native-parser sandbox is claimed.

The next image-method work must define and validate positive generation/edit
evidence before any FA/PA conclusion. A Content Credential, a valid signature,
an untrusted signer or an absent marker alone does not answer that question.
