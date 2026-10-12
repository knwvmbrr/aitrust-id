# A reference changed. What needs another check?

This free, offline tool compares an earlier reference set with a new one. It
helps you avoid carrying an old comparison forward after its source changes.
It issues no NF or FI tag and makes no accuracy or factual-truth claim.

- **Changed or removed source:** check the findings tied to that document again.
- **Unchanged pair:** its exact claim and reference context still match.
- **Changed reference set:** run passage selection again. A new passage can rank
  above an unchanged one. Keeping a pair does not keep the old ranking.
- **Review window:** an optional date range you declare. It is a reminder to
  review a source, not proof that the source is authentic, current or correct.

## Try it with invented examples

Use Python 3.12 or newer on macOS or Linux and a current source checkout. No
account, server, model download or network service is needed. Run these commands
from the repository. The first makes a private folder outside the checkout:

```sh
install -d -m 700 "$HOME/AITrust-ID-review"
python3 scripts/prepare-reference-revision-demo.py --output "$HOME/AITrust-ID-review/practice"
python3 scripts/review-reference-revision.py \
  --previous-corpus "$HOME/AITrust-ID-review/practice/old.json" \
  --current-corpus "$HOME/AITrust-ID-review/practice/new.json" \
  --subject "$HOME/AITrust-ID-review/practice/subject.txt" \
  --observation "$HOME/AITrust-ID-review/practice/observation.json" \
  --review-windows "$HOME/AITrust-ID-review/practice/windows.json" \
  --at 2026-10-12T12:00:00Z
```

Expect one unchanged pair, one changed pair, and
`"global_retrieval_must_rerun": true`. Those results describe the two invented
reference versions. They do not determine whether the fee or bicycle advice is
true. The example time and date windows are invented too.

Run the same command with `--details "$HOME/AITrust-ID-review/details"` to save
the individual dependencies in a new private folder. Existing output folders are
refused. Remove the practice and details folders when finished; this tool does
not keep a separate copy. A downloaded or separately shared copy cannot be
recalled by deleting your original.

## Use your own material

Create old and new corpus files with the [local corpus tool](local-reference-corpus.md).
Keep the exact subject and original output from the [lexical comparison](corpus-support.md).
All input files must be owner-held regular files, mode 0600, in private mode-0700
directories outside the checkout. Symlinks, hardlinks, pipes, altered evidence
and unsupported method versions are refused. Do not put private text in shell
arguments or source control.

The lexical method supports ASCII claim and reference lines with its existing
size limits. It compares exact NFC codepoint spans and the full document hash.
An edit elsewhere in the same document conservatively invalidates that document's
old findings. Recompute the original observation from the same supported method;
do not manually edit it to make a stale result appear current.

`--review-windows` is optional. Without it, window status is `unknown`. If supplied,
the JSON must use `declared-reference-review-windows/1.0.0`, the current corpus
`manifest_sha256`, and a `documents` array. Each entry contains `document_id`, its
exact `document_sha256`, `opens_at` and `expires_at`. Times use whole-second UTC
`YYYY-MM-DDTHH:MM:SSZ`. Opening is inclusive; expiry is exclusive. Omitted document
windows remain unknown. A wrong hash or malformed window refuses the whole job.

The summary shows counts and the next action. It omits text, source names,
hashes and offsets. Explicit private details contain source IDs, hashes and
spans, which can link content; protect that file and preview it before sharing.
Neither result authenticates the supplied policy, proves source freshness,
runs an NLI model, grants release approval or creates a public tag.

## Check the implementation

```sh
python3 -m pytest tests/test_reference_revision.py tests/test_corpus_support.py tests/test_nli_references.py -q
python3 scripts/verify-reference-revision.py --output output/verification/reference-revisions.json
```

These are synthetic engineering checks. Independent claim/passage labels,
representative source selection, actual freshness/authority and human operation
remain separate acceptance work for NF/FI.
