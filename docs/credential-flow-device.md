# Inspect Python credential flow on your device

Paste a Python snippet and choose **Inspect Python**. This optional method
preview shows whether a credential-named read feeds a supported HTTP call
argument in a finite straight-line Python program. It does not issue a PS tag
and does not change the existing PS command checker.

The program is never run or imported. Its named files, environment keys and URLs
are never opened, read or contacted. A static flow does not establish execution,
live credentials, authorization, recommendation or intent. **No supported flow**
is not a safety clearance or a check of all possible program behavior.
**Unavailable** means a valid complete result was not obtained; it is never
reported as zero flows.

## Use and privacy

The mounted component needs no account, Docker or installed Python. Analysis
starts only after **Inspect Python**. The first run downloads the public pinned
Python runtime and source bundle from the same website. Once loaded, the method
runs inside a dedicated browser worker. No pasted source is uploaded, placed in a
URL, saved in application storage, logged or automatically exported. Browser/OS
input features are outside this code's control. This increment does not provide
an installed offline cache or physical memory erasure guarantees.

Edit, **Clear Python**, **Cancel inspection** or closing/unmounting the preview
cancels its owned worker and invalidates old replies. Every run owns a fresh
worker, terminated on completion, failure or cancellation. Failure of this
optional chunk, worker or method is local; the original PS worker and method
remain independent. Shared static hosting/runtime delivery is still foundational
infrastructure, so this does not promise immunity to a website-wide outage.

**Method and exact positions** is optional and private. It contains the complete
canonical observation plus input/source identities, not the pasted program.
Hashes and spans may correlate private code; keep them on your device. There is
no default export or sharing action.

## Exact supported method

The canonical `tools/credential_flow.py` remains byte-identical method
`python-credential-flow-observation/1.0.2`. See
[its complete profile](credential-flow.md). Supported straight-line imports,
assignments, literals, containers and concatenation connect recognized literal
credential-path reads or named environment keys to supported `requests` arguments.
Import aliases are supported. An unrelated read, overwritten value, comment,
ordinary file, `timeout` argument or credential mention is not a flow. Unknown
calls, loops, functions, transformations and other unsupported syntax refuse.

The canonical bounded AST is parsed, inspected and compiled for syntax/semantic
validity; its code object is never executed. Repeated keywords, illegal reserved
bindings such as `__debug__` and excessive propagated strings refuse. Native
compiler warnings and inspected-source diagnostics are suppressed, not echoed.
No external `requests` package is loaded: an import in pasted source is only an
AST observation. Python analysis never consults the real environment or filesystem
named by the subject.

Limits are 8,000 raw and frozen-NFC Unicode codepoints, 32,000 UTF-8 bytes, the
canonical 2,000 AST nodes / expression depth32 / propagated string8,000 limits,
and a complete adapter record cap262,144 bytes. A larger record refuses in full.
Runtime loading has a 45-second deadline; observation plus validation has a
six-second deadline. Lazy component import has a separate 15-second deadline.

The browser envelope `credential-flow-device/1.0.0` includes the complete
canonical `recognized_read_spans` and `findings`, exact raw and frozen-NFC subject
hashes/counts, source hashes and explicit false/no-tag assertions. The client uses
only its owned worker channel, not page-wide message events. Before brief or
private details render, the validator checks closed nested data schemas, current
sources/method, exact requested input identities, dense bounded spans/read
membership, sink uniqueness and count/state consistency. It deep-freezes and
brands accepted objects. Unbranded records cannot be described by the UI.

Trust boundary: this is the same hash-verified Python mechanism, not a second
independent semantic checker. Native/browser whole-record parity verifies the
selected controls. The JS validator is not a Python parser and cannot prove that
a coherently forged record from a compromised trusted worker expresses the
canonical AST semantics. Source identity and matching records are not
cryptographic proof of verdict correctness or empirical accuracy. No caller
context declaration is offered by this standalone source profile.

## Developer integration

This branch supplies the complete optional component and an unpublished fixture;
the PM owns production mounting, shared build hooks and final integrated checks.

1. Keep the existing pinned static runtime preparation. Run
   `python3 scripts/build-credential-device.py` before Vite. It generates
   `/credential-device/method-<sha256>.json`, `/credential-device/notices.txt` and
   `site/src/credential-device-manifest.json`, with no dependency installation.
2. Mount the no-props `{CredentialFlowExplorerSlot}` exported by
   `site/src/CredentialFlowExplorerSlot.jsx` in the existing PS modal. The Slot
   lazy-loads the component and contains import, missing-chunk and render faults.
3. Preserve the original PS checker and result mapping. This is an optional
   source-code method preview, not production PS evidence or full F-012/T-PS
   completion. Source notices retain exact LICENSE, NOTICE and Unicode text;
   runtime notices remain separately linked. No license-clearance claim is made.
4. Include the new JSX files in the production style scan and keep existing
   stylesheet tokens. Verify the mounted production route separately.

The credential-only builder adapts the audited descriptor/publication pattern
from `scripts/build-hp-device.py`; it does not import HP or any sibling tag.
Captured sources/notices are bounded regular no-follow/nonblocking single-link
files under held/rechecked root and ancestor descriptors. It validates frozen JS
normalization against the exact bundled Unicode tables. All captures and staged
outputs are rechecked before the first replacement. Prepublication refusal
preserves prior published outputs. Failure during/after publication reports fixed
`output_may_exist:true` uncertainty: inspect outputs before retrying rather than
assuming rollback. Owned descriptors are closed once, including fdopen failures;
cleanup failure may leave private temporary bytes and must not be silently
classified as success. No captured source is imported/executed by the builder.

From a source checkout with the existing pinned site/verification dependencies:

```sh
python3 scripts/build-credential-device.py
python3 -m pytest -q tests/test_credential_device.py
node --test tests/credential-device-client.mjs
node scripts/build-credential-device-fixture.mjs
node scripts/verify-credential-device.cjs
```

The fixture uses an owned random-port loopback server, existing public runtime
assets and sequential Chromium/WebKit engines at phone-sized viewports. It adds
no production route. The verifier compares every canonical record field and
refusal against native Python; injects corrupt results, bundle/import/render and
missing-chunk failures; checks cancellation, privacy, 320px enlarged text and
accessibility; and runs the actual existing PS worker after optional failures.
Desktop-hosted browser evidence is not physical-phone, human accessibility,
independent accuracy, use/mention evaluation or full original acceptance.
