# Independent language observations — architecture

Implementer: Codex. Scope: F-018, F-019a, F-019c. These are separately selected
offline reference observations, not HP/MT assertions or an intent classifier.
Existing production tag mappings and the five PS rules remain unchanged.

The uncertainty observer requires explicit caller-selected uncertainty spans,
bound to the NFC-normalized subject hash. It measures presence or absence of a
published English hedge lexicon inside those spans. It cannot decide where
uncertainty ought to exist. An absent/invalid expectation is unavailable, not
evidence of overconfidence. This dependency is visible in every finding.

The urgency observer reports its literal time-pressure phrases and the proportion
of supported sentence units beginning with a published directive verb. It retains
both the phrase and directive positions. This lexical density is not grammatical
certainty or a manipulation probability. Emergency directions, ordinary purchase
deadlines and quoted examples can contain the same pattern.

The authority observer identifies a published set of expertise/consensus appeals
and reports whether the same sentence unit carries an explicit URL, bracketed
numeric citation or selected source span. An unattributed lexical appeal is not
proof that no source exists elsewhere. Named-source claims and cited claims are
reported separately. It does not resolve citations or verify expertise.

Input is explicitly supplied English text, at most 8,000 characters. The selected
observer returns its own state, source identity, parameters, subject binding and
NFC codepoint positions. Unknown language, malformed/foreign-subject annotations,
non-text and size violations fail closed. No observer fetches a source, uploads
text, makes an accusation, captures behavior or grants a provenance tag.

Checks must cover exact spans after normalization, annotation mismatch, hedge
negation, quote/news/emergency/ordinary persuasion cases, source markers, long
inputs, deterministic output, metadata-only CLI failure and actual isolated Linux
execution. Each component's remaining accuracy/integration acceptance stays
visible; one observer's success does not complete HP or MT.
