# PNG recorded-action declarations — component result

Codex image-evidence engineering lane, 2026-11-16. Base: `85b885f`.
Implementation and Mac checks are complete for this component milestone. PM
integration, semantic review and fresh isolated Linux execution remain pending.

## What you can use

The optional [PNG inspector](manifest-inspection.md) can now answer a narrower
question: **does this image's bound active record explicitly declare a supported
generative-AI creation or editing action?** It reads a producer's statement; it
does not independently establish whether AI made the image.

Use the inspector's existing separate pinned Python environment; no account,
server, model download or network lookup is required. The PNG limits, dependency
verification and private-report precautions in its installation guide still apply.

```sh
python scripts/inspect-manifest.py --image your-image.png --profile action-declarations-v1 --format text
```

Omit `--format text` for the separately versioned JSON profile
`attached-png-action-declarations/1.0.0`. Omit `--profile` to retain the original
inspection output. Successful observation or absence exits0; unsupported or
unavailable inspection exits2. Exit0 is not an authenticity or AI-origin verdict.

The text can say a creation action or editing action **claims** generative AI
use. It separately explains image binding, record signature, signer trust and
unchecked revocation. Even with a supported declaration, AI origin remains
Unknown and no tag is issued. JSON includes asset/method hashes and bounded
action positions; those hashes can link records, so sharing JSON is a deliberate
choice. Human text does not print them or embedded private metadata.

## Coverage and refusals

Only explicit canonical IPTC values paired with `c2pa.created` or `c2pa.edited`
are recognized. Each accepted assertion must belong to the active manifest,
carry the SDK's signer-created attribution and have its own exact active
hashed-URI success, alongside matching active image binding and signature.
An untrusted signer is still untrusted; a matching signature does not repair an
altered image or clear unknown revocation.

Missing markers, ingredients, missing/gathered attribution, unknown/custom or
imprecise types, unsupported templates, assertion-metadata regions of interest
and unresolved action `parameters.relatedAssertions` cannot
supply a positive declaration. Multiple creation/opening actions produce Unknown
with an explicit unsupported-structure reason; they do not establish contradictory
AI declarations. Compatible creation and editing declarations do not establish a
human editing sequence. Recorded array order and `allActionsIncluded` do not
prove complete history. No human-authorship or truth conclusion is inferred.

## Executed checks

| Check | Observed result |
| --- | --- |
| Focused declaration/parser/presentation/workflow suite |166 passed; zero failures or skips on final source |
| New actual pinned-SDK CLI profile |24 calls across12 groups, JSON and text, non-root macOS |
| Existing actual parser/readout CLI controls |21 passed |
| Prior committed CLI versus candidate defaults |6 byte-identical output/status cases, signed/altered/unsigned PNG in JSON and text;12 calls |
| Authored test controls |7 frozen PNGs; hand-built pixels, synthetic untrusted signer, no private keys written |
| Privacy and failure controls |Unknown/private metadata omitted, malformed/oversized/missing refused, private0600 export and overwrite refusal exercised |

The [regional-scope correction receipt](../runs/2026-11-16-image-declarations-regional-correction.json)
and [final actual SDK run](../runs/2026-11-16-image-declarations-regional-real-sdk.json)
bind the final source to166 focused checks and24 real profile calls. Seventeen
additional in-memory bound-report controls cover ordinary metadata, regional and
related-assertion refusal, malformed mappings and private-text omission. They are
semantic guard tests, not independently sourced regional image ground truth.

The [structure correction receipt](../runs/2026-11-16-image-declarations-structure-correction.json)
and [fresh actual SDK run](../runs/2026-11-16-image-declarations-structure-real-sdk.json)
bind the final Unknown wording to149 passing focused tests and24 actual profile
calls. Earlier receipts remain historical and unchanged. The initial correction
test retained an obsolete sentence assertion; that failure and fix are recorded.

The [component receipt](../runs/2026-11-16-image-declarations-component.json)
retains the first failures and corrections. Initial fixture authoring failed
because the pinned SDK requires an explicit creation source type; the negative
template control was corrected without weakening validation. The first focused
run had15 failures because trust status incorrectly blocked cryptographic URI
binding; the fix separates those observations while retaining other failures.
An ad hoc compatibility command also stopped at a nonexistent fixture filename;
its corrected run used the repository's actual frozen filenames.

[New profile SDK receipt](../runs/2026-11-16-image-declarations-real-sdk-mac.json),
[original controls](../runs/2026-11-16-image-declarations-original-controls.json)
and [default compatibility](../runs/2026-11-16-image-declarations-default-compatibility.json)
bind the tested sources and preserve their limits. The hosted workflow now runs
both real verifiers in its existing non-root network-isolated environment;
that new hosted run has not yet occurred. The optional parser source, pinned SDK,
dependency lock and per-reader settings are unchanged.

## Scope and remaining work

Original scope percentages remain unchanged:132 complete and70 open. F-025
remains100% for its previously accepted parser job; this additional component
is60% pending integration acceptance. T-FA and T-PA remain20%. X-07 is unchanged.
There is no adopted image-origin detector, FA/PA release, new public endpoint,
issuer, model, telemetry, new taxonomy or training ground truth.

The fixtures are authored record statements attached to ordinary generated test
pixels, not evidence that AI produced those pixels. Mac checks do not establish
kernel network isolation, a full native parser sandbox, physical-phone operation,
complete C2PA2.5 conformance or independent accuracy. Positive generation/editing
evidence must still earn its own validated tag contract before release.
