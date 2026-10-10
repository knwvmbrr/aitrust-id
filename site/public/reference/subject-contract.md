# Subject contracts — frozen text v2 and exact code bytes v1

A subject identifies the exact evaluated artifact. A hash is a correlation
identifier, not anonymisation, truth, authorship or an authenticity certificate.
These primitives neither redact nor evaluate input.

For text, redact first, then normalize to Unicode 15.0.0 NFC, encode strict UTF-8 and
hash with SHA-256. Length and spans address Unicode code points in that normalized
redacted text, not JavaScript UTF-16 units or original-source offsets. Preserve
newlines and all other characters. Reject unpaired surrogates. The implementation
accepts at most 200,000 input code points; empty input has a defined hash, even
though the evaluation endpoint requires nonempty input.

For code, hash exact bytes without normalization, decoding or newline conversion.
Length and spans address bytes. Preserve BOM, source encoding, whitespace, CRLF,
NUL and binary octets. The primitive accepts at most 800,000 bytes. It does not
make arbitrary bytes executable or prove a language parser accepts them.

`protocol/subjects.py` and `protocol/subjects.cjs` implement the same versioned contracts. Text results declare `subject-v2` and
`NFC-Unicode-15.0.0/v1`; code retains `subject-v1`. The old v1 text vectors
are historical and insufficient for cross-version normalization.
[Normalization and migration](normalization-contract.md) describes the correction.
`eval/vectors/subjects-v2.json` carries fixed expected outputs and deliberately
different code/text artifacts. Run `python3 scripts/verify-subjects.py` with Node
available to compare both implementations. Invalid and oversized inputs fail.
The public vectors include 60 exact-output cases (including 41 measured version regressions) and eight invalid-input cases;
oversized cases use compact repetition instructions. Both language implementations
must reject every invalid case, including unpaired surrogates and wrong types.

The gateway still evaluates **text only**, including code pasted as text. The raw
code subject primitive is an implementer contract, not a functioning code-modality
detector or a change to the adopted assertion format. Image, audio, video and
document subjects remain proposals requiring complete canonical formats. Two
local implementations do not constitute an outside implementer's acceptance.
