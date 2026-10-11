# Find numeric details with no nearby source marker

This separate development checker counts supported literal numbers and
`YYYY-MM-DD` shaped tokens. It notes whether the same sentence contains a
`[12]` style citation marker or an HTTP/HTTPS URL. **A marker does not prove that
its source supports the statement, and no marker does not prove a statement false.**
It performs no reference lookup and issues no HP, NF, FI or other tag.

Use Python 3.10 or later, without an account, Docker, model or additional package:

```sh
python3 scripts/quantitative-observations.py --language en < /your/private/answer.txt
```

The brief output reports how many supported details have or lack a same-sentence
marker. It contains no answer text, subject hashes, URLs or spans. Nothing is
uploaded or saved automatically. `OBSERVATIONS` means at least one supported
literal detail had no same-sentence marker; `NO_SUPPORTED_PATTERN` means no such
supported literal pattern was found. Neither is a factual or safety verdict.
Unsupported input or a requested export that cannot be safely saved yields
`UNAVAILABLE` with exit 2.

Supported forms include ASCII digit tokens, signed numbers, standard comma
grouping/decimals, percentages and date-shaped tokens. Calendar validity,
written-out numbers, unusual date formats, ranges, word-attached identifiers and
adjacent non-ASCII token boundaries are outside the method. Adjacent non-ASCII
characters are explicitly skipped, avoiding different word-category behavior
between Python/Unicode versions. Marker-contained digits are excluded. Quotes,
code and examples are not classified as assertions or recommendations.

Limits are 32,000 UTF-8 bytes, 8,000 normalized characters, 256 details and 48
characters per numeric token. Longer tokens are skipped explicitly; excessive
detail counts fail instead of silently clipping. Normalization uses the existing
Unicode-15 method. Source-marker placement uses literal sentence units and may
not match a person's interpretation of a complex document. Sources elsewhere,
stale references, actual citation resolution, semantic specificity, uncertainty
and useful hallucination indicators remain separate work.

## Optional private details

Use a new destination in an existing directory you own with mode `0700`, outside
the source checkout:

```sh
python3 scripts/quantitative-observations.py --language en \
  --private-report /your/private/details.json < /your/private/answer.txt
```

The new file has mode `0600` and is never overwritten. Symlinks and public
parent directories are refused. It records the normalized subject hash, exact
spans, marker spans, method/source file hashes and parameters, without copying
text or source URLs. **Hashes and spans may reveal or link information; share
only deliberately.** Source hashes identify files; they do not authenticate an
untrusted installation or provide independent accuracy evidence.

This is F-015's literal-observation component. It does not complete a contextual
unsourced-specificity claim or the independently validated HP tag. The complete
scope remains preserved. The [architecture](quantitative-observation-plan.md)
and [executable controls](../tests/test_quantitative_observations.py) document the
supported and failure paths. No other tag depends on this optional checker.
