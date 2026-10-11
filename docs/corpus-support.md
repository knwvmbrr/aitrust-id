# Find similar passages in your own references

Create a private local corpus with [the existing import guide](local-reference-corpus.md).
Then use Python 3.10 or later, without accounts, Docker, models or extra packages:

```sh
python3 scripts/corpus-support.py --corpus /your/private/reference.json < /your/private/claims.txt
```

Use your actual private paths. Each nonempty input line is one claim unit. Each
nonempty reference line is one candidate passage. The first method supports
ASCII words and numbers. Its word-frequency cosine similarity ranges from zero
to one. The default observation threshold is 0.75, configurable using
`--threshold`; it is a retrieval parameter, not an adopted tag gate or probability.
`--maximum` limits findings to one through ten across all claims.

Results identify `sig.corpus_support.v1`, the score and exact query/reference
spans. Positions are code-point offsets in Unicode-15 NFC text, with the end
excluded. Original and normalized source hashes and the full corpus manifest
identify the selected reference version. Reference freshness remains
`unestablished`; attaching a source does not prove it is current or accurate.
No source or query passage is echoed, uploaded or saved by this command. Hashes,
IDs, scores and positions can still link or reveal information: share deliberately.

**A similar passage is not a verified fact.** Word order, negation, units, dates,
quotes and fabricated statements can all fool lexical resemblance. “Water is
safe” and “Water is not safe” can match. Results report `truth_established: false`,
`entailment_checked: false`, `score_is_probability: false` and an empty tag list.
NF and FI are not issued or independently validated by this signal. No similarity
match is also not proof that a claim is false.

Limits: 2,000 subject characters, 32 claim lines, 512 tokens per line, 4,096
reference lines and ten returned findings. Unsupported reference lines are
counted and skipped; unsupported subject units, no usable references, excessive
counts, corrupted manifests, missing files and invalid parameters yield
`UNAVAILABLE` with exit 2, never a negative truth finding. Sources must first pass
the existing private-corpus integrity, size and permission checks.

This completes F-020a's retrieval-similarity job. Corpus contradiction/NLI,
semantic entailment, factual labels, fresh-reference authentication, outside-user
acceptance and NF/FI independent accuracy remain separate work. Tests cover
actual CLI import/query, span identity, score mathematics, malformed/corrupted
files and deliberately misleading similarities.
