# Choose the two passages you want to compare

This optional offline research path compares **one claim line and one line from
your own reference corpus**. You choose the pair; it is not an automatic fact
check or a search over all evidence. It issues no NF, FI, HP or other tag.

Use it when the lexical selector misses the passage you wanted. The existing
example “The room is empty.” versus “There are people in the room.” does not meet
the default lexical threshold. Choosing those exact lines lets the existing local
model compare them without lowering the global threshold or claiming a better
retrieval score. The model can still be wrong.

## 1. Prepare a selection without a model

Start with an existing [private corpus](local-reference-corpus.md), a private
claim text file and its document ID. In the commands below, replace `PRIVATE`
with your private directory and `REPO` with the source checkout. Their parent
folder must already be owner-held, mode `700`, outside the checkout; input files
must be regular, single-link, mode `600` files. Do not put private passage text in
shell arguments, a public issue or source control.

```sh
python3 REPO/scripts/prepare-reference-selection.py \
  --corpus PRIVATE/corpus.json --subject PRIVATE/claim.txt \
  --claim-line 1 --reference-document manual --reference-line 1 \
  --output PRIVATE/selected-pair
```

Line numbers are **physical, one-based lines**, counting blank lines. LF and CRLF
are supported; selecting a blank line is refused. The selected lines must be
nonempty ASCII text, at most 2,000 characters and 512 lexical tokens. Surrounding
spaces/tabs are excluded from evidence spans. The entire claim file has the
existing 2,000-character/8,000-byte limit. Other corpus limits remain unchanged.

The new `selection.json` contains binding hashes, line numbers and exact trimmed
NFC/codepoint spans, not passages. It binds both original and normalized claim
identity, the whole corpus manifest and original/normalized reference identity.
If a claim or corpus changes, prepare a new selection; do not manually edit hashes
or positions to make old evidence look current. The selection digest identifies
its bytes and bindings; it is not a signature, an authenticated source or proof of
review. Hashes/positions can still link sensitive information.

Preparation uses only the Python standard library. It runs no model, creates no
service, retrieves no webpage and downloads nothing. Existing output folders are
never overwritten. It does not automatically choose or verify the relevant lines.

## 2. Compare using the existing local model

Use your **already verified** environment/cache from the
[existing setup guide](nli-pairs.md). This new route does not install packages,
fetch assets or substitute an unverified model. If the environment/cache is
missing or unsupported, the comparison is Unavailable.

```sh
PRIVATE/nli-env/bin/python REPO/scripts/check-nli-references.py \
  --corpus PRIVATE/corpus.json --subject PRIVATE/claim.txt \
  --selection PRIVATE/selected-pair/selection.json \
  --model-cache PRIVATE/nli-assets --details PRIVATE/pair-result
```

Omit `--details` if you do not want a saved result. Do not combine `--selection`
with `--threshold` or `--maximum`; the command refuses instead of silently ignoring
retrieval parameters. Invoking the earlier command **without** `--selection`
keeps its original automatic retrieval behavior and profile.

The reference is the model's premise, and the claim is its hypothesis. Reversing
them can change the result. Private details use
`selected-reference-nli-observation/1.0.0`; they retain all three model scores,
ties, model/runtime identity, exact selection and bindings. They explicitly say
retrieval was not evaluated and provide no retrieval score. They contain no raw
passage text. The console omits input, private paths, document IDs, hashes and
spans. Details and the selection remain yours to keep or remove separately.

## Meaning and failure

A completed comparison reports one model's interpretation—contradiction,
entailment or neutral—not verified truth, source authority, calibrated probability
or independent corroboration. You selected one pair, so omitted evidence is not
covered. One model analyzing several passages is still one model. The retained
sky/books false contradiction remains a known model error.

A missing/changed corpus, altered selection, invalid binding, unsupported line,
missing cache, failed sandbox, model error, timeout or export failure produces
Unavailable and exit `2`. It does not become “no similar passage,” “false” or a
successful partial comparison. The existing worker identity/score validation,
network denial and 55-second outer/45-second inner deadlines are unchanged.
No automatic retrial or truncation is added.

The optional existing `--review-windows PRIVATE/windows/review-windows.json`
works with this route too. Every attached reference must pass the declared window
before **and after** evaluation. Expiry or a backwards clock refuses without
saving partial details. The window is your declared review schedule, not evidence
of freshness or truth.

Nothing is uploaded, used for training or automatically retained. No account,
endpoint, collection permission or new production tag is introduced. Human
accessibility, representative claim/reference labels and NF/FI release acceptance
remain separate work.

[Architecture and risks](selected-reference-pair-plan.md).
