# Compare the claim and source passage you choose

This optional offline development workflow compares an explicitly selected part
of your subject with an explicitly selected passage in your local corpus. It
reports two separate observations: exact literal occurrence and ASCII cosine
resemblance. It issues no NF, FI or other tag and does not verify a fact.

Existing whole-corpus retrieval and selected-line NLI remain separate commands.
This workflow adds arbitrary contextual span selection without a model. It does
not extract semantic claims, select the right source for you, search the web,
resolve citations, assess authorship or establish source freshness.

## Prerequisites and private inputs

Use CPython 3.10+ on macOS or Linux, a current source checkout and the existing
[corpus-v1 importer](local-reference-corpus.md). No third-party Python packages,
account, model, Docker or download is needed. macOS requires its existing
`/usr/bin/sandbox-exec`; Linux requires existing system `libseccomp.so.2` on
x86_64/aarch64. Required sandbox setup failure makes that check Unavailable; it
never falls back to an unrestricted worker. This does not review/clear all
distribution dependencies or modify an existing service.

Keep the UTF-8 subject, corpus and selection file outside the checkout as
owner-held regular single-link files with mode 0600. For output, use an existing
directory owned by you with mode 0700. Symlinks (including ancestors), hardlinks,
pipes, public input files and existing output destinations refuse. Use canonical
absolute paths when your OS aliases directories through symlinks.

Create `selections.json` with a closed object of this shape:

```json
{"format":"nf-pair-selections/v1","pairs":[{"claim_span":[0,14],"document_id":"manual","source_span":[0,18]}]}
```

This example selects all of subject `Water is safe.` and all of document `manual`
containing `Water is not safe.`. Replace the IDs/spans for your actual inputs.
Spans are zero-based, end-exclusive codepoint offsets **after frozen Unicode-15
NFC normalization**, not UTF-8 bytes or UTF-16 screen positions. Select nonblank
parts; duplicates refuse. Overlapping selections are allowed when the pairs are
different. Choosing only part of a sentence can omit negation or qualification;
the tool records your selection and does not certify its adequacy.

## Prepare, then inspect

```sh
python3 scripts/check-nf-source-evidence.py prepare \
  --subject /your/private/subject.txt --corpus /your/private/corpus.json \
  --selections /your/private/selections.json \
  --check literal --check cosine --output /your/private/pairs.json
python3 scripts/check-nf-source-evidence.py check \
  --subject /your/private/subject.txt --corpus /your/private/corpus.json \
  --sidecar /your/private/pairs.json
```

Select either check alone or both explicitly. The private 0600 sidecar binds raw
subject bytes, NFC subject, corpus bytes/manifest, original/NFC source documents,
selected claim/passage spans and digests, requested checks and method sources.
It contains no selected words. Checksums are identity, not source authenticity
or a signature: the caller can prepare a different explicit selection.
Any subject/corpus/common-method change requires a fresh sidecar. Optional
cosine-method drift affects cosine only; reprepare if you want that changed
method considered. Unchanged sources elsewhere cannot establish freshness.

The console contains counts and check states, not words, source IDs, hashes,
spans or scores. `COMPLETE` means all selected observations completed; `PARTIAL`
means at least one completed and another is Unavailable. Exit 0 permits either
state; inspect each check. When all are Unavailable, exit 2 reports that state
and creates no requested result file. A check is one batch over the selected
pairs; one unsupported pair makes that whole check Unavailable. It does not
erase completed results of the sibling check or change other personal checkers.

To explicitly save details, add `--private-report /your/private/result.json` to
the `check` command. That new 0600 file contains linkable identities, exact
original subject/document spans, declared selections and observations, but no
subject/source text. Sharing hashes/spans/IDs can reveal information; share
deliberately. Nothing is saved automatically by `check`. Delete your sidecar and
report to remove those saved records; the source corpus remains independently
user-controlled.

## Read the observations within their limits

- `literal` uses the existing case-sensitive NFC `corpus.query` on just your
  selected passage. Located text is not semantic support; absence is not
  falsehood. It finds nonoverlapping matches and returns at most 10. If the cap
  is reached, the total count is unknown. Unicode literal matching can complete
  even when cosine cannot process the same selection.
- `cosine` uses the existing `corpus_support.observe`, unchanged: ASCII words/
  numbers, nonempty trimmed lines, threshold 0.75 and at most 10 findings. The
  selected claim must be one physical LF/CR line; unsupported input or no usable
  reference lines is Unavailable. Unsupported reference lines are counted by
  that existing method. A score is word resemblance, never confidence or an
  adopted NF gate. Negated/false statements can be highly similar.

Each passage is represented internally by an explicitly identified corpus-v1
projection of its selected NFC bytes. Projection hashes are **not** the raw
original document's hashes. Private results preserve both identities and the
selected original pair. `match_offset_origin: original_subject_and_document`
means returned match positions have already been rebased into those originals;
virtual projection offsets never replace them. Omitted claims/sources are not
evaluated, and a passage quote can itself be wrong or stale.
Before accepting a cosine record, the validator replays the same capped
canonical selections and compares the complete numeric/span/result rows. This
detects changed scores and omitted matches; it is record consistency, not an
independent accuracy study or corroboration. Replay does not search other sources
and a replay failure makes only that check Unavailable.

## Resource and error handling

Each selected check gets its own pipe-only subprocess with a cleared environment,
`-I -S -B`, an eight-second wall deadline and existing process-group termination/
reaping (up to five additional seconds for failure cleanup). The worker sets
CPU 4 seconds, file output/core 0 and descriptor 256 limits; Linux also sets a 512 MiB
address-space limit. macOS uses deny-network sandboxing and Linux uses the
system-libseccomp socket/network/io_uring denial mechanism. Both IPv4/IPv6
loopback denial probes must pass before examining the selected input. No user
text is sent in a probe, argument or subprocess stderr. This is a narrow local
trusted-code workflow, not an arbitrary-code sandbox or factual verifier.

Limits: subject 32,000 UTF-8 bytes and 8,000 original/NFC codepoints; 1–8 pairs;
each selected claim/passage at most 2,000 NFC codepoints; 64 KiB sidecar and 256 KiB
worker/private result. The existing corpus limits stay unchanged (32 documents,
200,000 codepoints/document, 2 MB combined source bytes and 4 MB envelope). Excess
refuses without clipping input. Inputs are captured via held no-follow
descriptors and rechecked before export. Sources are captured once per command
and their held identities checked before/after workers, avoiding descriptor
amplification. NF owns its I/O helper; FI module absence does not affect NF.

Ordinary fixed `invalid_or_unsupported_selected_source_request` errors exit 2
without a new final destination. Existing destinations are preserved. Temporary
cleanup can fail and leave private `.nf-evidence-*` names. After link succeeds,
or if an unexpected link error makes the outcome unknown, fixed
`output_commit_uncertain` includes `output_may_exist: true` and exits2. A complete
file may exist: inspect your selected destination and private directory before
any retry; do not automatically delete it or treat the failed export as accepted
evidence. The tool promises no rollback on filesystem failure. Raw output
descriptors remain capture-owned using `closefd=False`; every owned close is
attempted once, even after stream-construction failure. A close error can mean
already closed/reused, so descriptor numbers are never retried. Same-UID hostile
processes, compromised installed code and abrupt power loss remain outside
these file-handling guarantees.

Run focused controls with the existing development environment:

```sh
python3 -m pytest -q tests/test_nf_source_evidence.py
```

The implementation/CLI evidence uses invented material. Full T-NF remains open
for independent claim/passage labels, useful semantic support/coverage evidence,
accepted mapping and required human operation. No scope percentage, production
route, public tag or license-clearance claim changes. See the
[architecture and risks](nf-source-evidence-plan.md).
