# Explicit reference-pair comparison — architecture before implementation

Codex NF/FI evidence lane · 2026-11-16 · based on integration `85b885f`.
Scope contribution: F-020b, T-NF and T-FI. No parent tag or requirement closure.

## Job and outcome

Let a person compare one explicitly chosen claim line with one explicitly chosen
reference line, retaining exact corpus/document/claim evidence. The existing
retrieval route first requires lexical similarity; it misses the retained room
example at its default threshold. Explicit selection can deliver that exact pair
to the existing pinned offline NLI worker without changing global retrieval or
pretending the selection was automatic, exhaustive or independent.

## Contracts and file ownership

- New `research/nli/selected_references.py`: a separate strict one-pair selection
  profile, binding original and normalized subject hashes, corpus manifest,
  original and normalized document hashes, physical one-based line numbers,
  trimmed NFC/codepoint spans, normalization identity and canonical record digest.
  Rebuild the selected record from captured inputs and require exact equality
  before preparing or interpreting a worker result.
- New `scripts/prepare-reference-selection.py`: standard-library preparation from
  existing owner-private files; no model import/download/network. Use the existing
  private packet reader/writer and create a new output folder; refuse overwrite,
  links, public files, changed sources, invalid lines and malformed input. Console
  output omits raw text, paths, document IDs, hashes and offsets.
- Minimal `scripts/check-nli-references.py` integration: optional `--selection`,
  separate selected profile and no lexical score/threshold, same existing worker,
  output validator, cleanup, deadlines, private export and before/after declared
  review-window checks. Existing automatic invocation remains unchanged. Reject
  selection combined with explicit retrieval flags rather than ignore them.
- New focused module/CLI tests and usage/result/evidence documents; PM owns global
  scope, completion and platform integration.

One pair only. The whole claim remains within the existing 2,000-character/8,000
UTF-8-byte outer limit. Selected lines are nonempty ASCII text, at most 2,000
characters and 512 lexical tokens, with physical LF/CRLF line addressing and
trimmed spans. Existing model-token refusal remains authoritative; no truncation.
The prepared pair remains inside the existing 20,000-character worker request.
Selection files are capped at 8 KiB. No changes to the pinned model, identity,
labels, network-denied execution, 55-second outer/45-second worker deadlines,
35-second CPU budget or Linux 2 GiB address-space limit.

The new research result states that retrieval was not evaluated. It records the
exact selection, reference-as-premise/claim-as-hypothesis direction, all three
model scores and ties, but no calibrated probability, independent corroboration,
NF/FI/HP assertion, reference freshness or truthful-content conclusion. A missing
cache or invalid model result is Unavailable, not a negative claim verdict.

## Risks and acceptance

Caller selection can cherry-pick or omit contradictory evidence; the record must
name that scope. A selected document is not authenticated merely by a checksum,
and a caller-declared review window does not establish freshness. Line indexes
are physical one-based indexes, including blank lines; blank selection is refused.
Original/NFC hashes and recomputed spans prevent stale or manually moved evidence.
A selection digest is an integrity binding, not a signature or trust assertion.

The existing model's retained unrelated-sentence error remains. This increment
addresses reachability of a chosen pair, not representative semantic accuracy.
No new user data is collected, uploaded, automatically retained or trained on.
Hashes/spans in explicit private details can still link sensitive content.

After final edits run one focused set covering: valid bindings and exact pair
text; wrong/changed corpus, source and subject; bad line/span/hash/digest/types;
duplicate/unknown JSON; selected controls conflict; default route unchanged;
cache absence, invalid worker output, deadline/cleanup; output permissions,
no-overwrite and no private text echo; review-window refusal before inference and
expiry/clock change after inference. Existing real CLI controls remain separate.
Use already verified local model assets only after PM schedules that work. If no
cache/runtime is available, record Unavailable and do not download or pretend a
mock backend is real inference. Preserve the original 202/132/70 totals.

## Review addition: optional-route fault containment

After the initial component/model checks, self-review found the new module was
imported at command startup. Load it only for the selected route so its absence
cannot disable automatic retrieval. Catch only its import/syntax failure at that
seam with a fixed selected-route Unavailable; do not change the default route's
other failure semantics. The first candidate introduced a local variable-name
collision; retain that failed result, correct the name, rerun affected controls
and obtain current-source model evidence rather than reusing the old receipt.
