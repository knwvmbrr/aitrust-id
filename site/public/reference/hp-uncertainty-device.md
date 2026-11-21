# Look for uncertainty words — on your device

Paste an English passage. Select **I expect uncertainty to be expressed in this
whole passage**, then press **Check uncertainty words**. Your selection is
required: the checker cannot decide when uncertainty is needed.

This is an optional HP method preview, not an HP tag or an assessment of truth,
confidence, writing quality or a person's intentions. It finds a limited list of
literal words: may, might, could, possibly, perhaps, probably, likely, unlikely,
uncertain, unclear, approximately, roughly, estimated and estimate.

“No listed uncertainty words found” does not mean a claim is false or wrongly
confident. Other words can express uncertainty. Quotes and examples can contain
these words too. “Not likely” retains the word `likely`; negation is not interpreted.
`May 12` is excluded as a narrow calendar candidate, not a validated date.

Your complete passage is the selected context. This is different from choosing
part of a longer document; use the existing [private annotation CLI](language-observations.md)
for narrower contexts. Full HP/F-018 contextual, independent and human acceptance
remains open.

## Supported boundary and private input

Input is limited to 8,000 raw and frozen-NFC Unicode codepoints and 32,000 UTF8
bytes. Input is never clipped. Blank/NUL/invalid-Unicode/oversized input refuses.
This separately versioned device profile is
`hp-explicit-uncertainty-device/1.0.0`, with
`hp-uncertainty-safe-boundaries/v1`. The canonical Python hedge method remains
unchanged at `english-context-observations/1.0.0`.

Unicode elsewhere in the passage is preserved, including normalized accents and
emoji positions. Curly quotes, a declared set of nonword punctuation and Unicode
whitespace are supported. A potential listed word touching an ambiguous
non-ASCII letter or boundary refuses the **whole** check: for example `mayé`,
`émay`, `mİght`, `eſtimate` and `May 12é`. This avoids guessing whether Python and
a browser interpret the same word boundary. Unsupported does not become zero
findings. The unrestricted canonical CLI is a separate observation, not evidence
that this narrower browser profile supports those forms.

The annotation binds your explicit whole-passage selection to the frozen-NFC
subject hash. Results preserve that annotation, raw-byte and normalized identities,
exact method/source hashes, original canonical measurements and codepoint spans.
The browser replays the bounded lexical/calendar rows and compares the entire
closed record, including omitted evidence and counts, before display. This is
record consistency, not independent validation or semantic corroboration.

## Privacy and stopping

No account, gateway, input upload, automatic saving, research enrollment or
training permission is involved. The first Run downloads the existing self-hosted
Python runtime and this method's source bundle. Computation is local; initial
runtime/source availability is not an offline-installation guarantee.

Every Run has a fresh worker: 45-second load and 6-second check deadlines, a
262,144-byte result bound and cleanup after completion/error/cancellation. Source
and runtime files may be downloaded; input is never placed in a URL or request.
Editing the passage removes the old result and resets the whole-passage selection.
Unchecking the selection, Clear, Cancel or closing the preview cancels pending
work. This describes application state, not forensic memory erasure or deletion
of browser clipboard/history outside the application.

**Method and exact positions** opens private details only when requested. They
include hashes and positions that can reveal or link text, but no pasted text.
No record is exported automatically. Failure is Unavailable; numeric HP, PS, MT
and other optional checks keep their separate runtimes and results.

## Source, setup and current delivery boundary

This lane supplies a standalone engineering fixture. It does not mount or publish
a new production HP control by itself. Use a source checkout with CPython3.10+ and
the repository's existing locked site development dependencies. There is no new
package, model, service or license agreement. The fixture uses the existing
Pyodide314.0.7 runtime; license/source notices are retained, not independently
cleared for every distribution route.

```sh
python3 scripts/build-hp-uncertainty-device.py
node tests/hp-uncertainty-client.mjs
python3 -m unittest discover -s tests -p test_hp_uncertainty_device.py -v
node scripts/build-hp-uncertainty-fixture.mjs
node scripts/verify-hp-uncertainty-device.cjs
```

Use `AITRUST_VERIFY_PYTHON` for your existing verification interpreter when needed.
The final two commands require the existing site packages and installed pinned
Playwright browsers; they install nothing. Output lives under ignored `output/`.
No local Docker, native app, server account, private key or production data is used.
PM integration, separate review, protected checks and publication remain distinct
from this fixture. Emulated Chromium/WebKit controls do not establish physical
phone, human accessibility, independent labels/accuracy or full HP release.
