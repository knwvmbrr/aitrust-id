# Practice selected choice wording in a local browser

This experimental standalone page runs the reviewed choice-framing method on
your device. It does not issue MT or decide that someone is manipulative. The
existing MT preview, PS and other tags remain unchanged and independent.

## Build and open

Use the source branch containing this guide and an existing cached Pyodide
314.0.7 directory from the project's locked website environment. This builder
installs and downloads nothing. It checks all five runtime bytes against the
tracked release manifest and carries project, Unicode, runtime and selected
JavaScript/zlib source notices. Full WASM corresponding-source coverage and global
license clearance are not claimed.

```sh
python3 scripts/build-mt-choice-practice.py --runtime /your/existing/node_modules/pyodide --output output/choice-practice
python3 -m http.server 8765 --bind 127.0.0.1 --directory output/choice-practice
```

Open `http://127.0.0.1:8765/` on that computer. The server must stay bound to
loopback; it serves public application/runtime files, not input text. This is a
local development route, not a production publication. A mobile-sized browser
check is not a physical-phone or human accessibility acceptance.

## Choose a complete input

1. Choose an invented additive example, or paste your own English passage.
2. Enter the two exact item strings in their order, and the additional passage
   you nominate as context. Each item must occur once; no automatic clause or
   alternative discovery occurs. Explicitly choose the whole passage as the frame.
3. Choose **Check selected wording**. Read the brief, then deliberately open
   **Show exact record** if you want private hashes and positions.

The five paired constructions use the existing method: either/or, only/or,
neither/nor, between/and and additive not-only/but-also. Additive markers are
separate from binary markers and have no proposed false-dilemma signal. An old
research proposal may appear in the exact legacy record; it is not a released
signal, accusation or tag. An additional passage is not verified as relevant,
feasible, authentic or fresh. Quoted lessons, menus, safety advice and ranges can
use the same wording.

## Limits and failure

The entire passage is one caller-declared frame: at most 2,000 original/NFC code
points and 8,000 UTF-8 bytes. Each exact item is at most 256 code points/1,024
bytes. The nominated passage has the same 2,000/8,000 bounds. The complete JSON
request must fit 24,000 bytes. Whole oversized pastes remain visible and refuse;
nothing is clipped into an accepted example. Missing, repeated, overlapping or
out-of-order items, absent declaration, unsupported input, integrity errors and
worker/startup/deadline failure are **Unavailable**, never safe or zero findings.
A completed unsupported-grammar observation means only that this finite grammar
did not match the selection.

The initial public manifest fetch and stream have a separate 10-second deadline.
A stalled or invalid manifest leaves Check disabled and announces Unavailable
politely; it sends no input. Each explicit Check starts its own worker. Startup is bounded to 45 seconds;
evaluation/validation to 6 seconds. Editing, Clear, Cancel or leaving removes the
old result, stops pending ownership and ignores late replies. Clear removes the
input fields too. This describes application state, not physical memory erasure.

Only public runtime and source files are fetched from this local origin. Inputs
travel as bounded worker messages/function arguments; no input is executed,
uploaded, automatically stored, exported, enrolled or used for training/research.
Details are mounted only when chosen and contain no full input words. Hashes,
positions and method results can still reveal or link information; inspect before
sharing. No browser storage or account is needed. Delete the generated public
folder and stop the loopback server to remove this development tool.

The source bundle and exact raw-request, frozen NFC, item/reference and corpus
identities bind the result before display. Closed records, counts, literal
construction/marker validation and stale-result guards do not provide
cryptographic verdict attestation against a compromised page, runtime or OS.
Canonical Python and client consistency checks are not independent methods or
independent accuracy evidence. Runtime metadata can differ from native Python;
comparison evidence must distinguish that disclosure rather than relabel it.

This is a bounded optional user workflow. Full F-019b and T-MT contextual/error,
independent labeling, accepted mapping and human operation remain open. No
production deployment or original requirement closure is granted here.
