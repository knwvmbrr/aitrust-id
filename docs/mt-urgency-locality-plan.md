# MT lane: local urgency association

Architecture before implementation · Codex MT owner · 2026-11-16.
Scope contribution: F-019a and T-MT. No new adopted tag or production mapping.

The current English observer separately measures time phrases and supported
sentence-start directive verbs, then combines them across the entire input. Its
published behavior is accurate to that method, but a time word in one unrelated
sentence can nominate an urgency observation for a directive in another.

Actual baseline examples:

- `The committee met today. Read the archived minutes.` nominates an urgency
  observation at density 0.5.
- `Install the patch. The news was published today.` also nominates one.
- `Read the evacuation notice now.` nominates one; this is legitimate safety
  advice, not evidence of manipulation.

## Change and invariants

For urgency only, pair a supported starting directive and time phrase within the
same existing sentence unit before nominating the signal. Retain the published
whole-input directive-density threshold and all literal measurements. Report the
paired units and unpaired time-phrase spans. A finding's supporting spans contain
only its paired observations rather than unrelated directives elsewhere.

Publish urgency method revision `english-context-observations/1.1.0`. Hedge and
authority algorithms retain revision 1.0.0 and their existing behavior; the common
source fingerprint changes and remains visible. This is an offline observation
profile change, not a wire-schema or live tag-code change.

## Risks and limits

`Buy the guide. Last chance today.` can express genuine cross-sentence pressure.
This stricter observer will retain its measurements but cannot establish the
association and will not nominate it. No claim of general urgency detection or
improved population accuracy follows. Sentence splitting is still a published
lexical heuristic. Quotes, news, emergency advice, ordinary persuasion and word
sense are not classified as manipulation. The density threshold is not a
calibrated probability. Contextual grammar, representative evaluation, independent
labels, MT integration and human acceptance remain open.

The input limit stays 8,000 Unicode codepoints, language stays explicitly English,
normalization and evidence units remain frozen NFC/codepoints, no network or model
is added, and the output still has no tags or truth/intent verdict. Unavailable
input remains distinct from a completed no-supported-pattern observation.

## Verification

After all edits, run the existing language-observation suite and the focused
locality controls once. Cover unrelated dates, actual within-unit associations,
wrong-unit evidence leakage, cross-sentence ambiguity, emergency/ordinary/quoted
examples, the unchanged density threshold, NFC positions, language/size refusal,
unchanged hedge/authority revision behavior, and real CLI metadata-only output.
Record the authored examples separately from independent accuracy evidence.
Retain before/after observations and update the scope contribution/result,
execution receipt and changelog. Do not change global completion percentages.
