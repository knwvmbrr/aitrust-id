# Resolve the numbered markers you explicitly map

This optional offline development tool associates literal `[1]`–`[9999]` markers
with documents in your existing [local reference corpus](local-reference-corpus.md).
You declare the mapping. It does not find sources, check a claim against a
passage, prove citation correctness, or issue FI, NF or any other tag.

Requires CPython 3.10+ on macOS or Linux. Only the standard library and project
source are used. No account, service, model, package install or network is used.
Existing personal checkers work independently of this optional component.

## Prepare an explicit mapping

Keep the selected subject and existing corpus-v1 file outside the checkout in an
owner-controlled private directory. Inputs must be regular, single-link files
with mode 0600; output directories must already exist with mode 0700. Symlinks,
including ancestor links, are refused. Use canonical absolute paths if your OS
aliases a temporary/home directory through a symlink.

```sh
python3 scripts/citation-resolution.py prepare \
  --subject /your/private/answer.txt --corpus /your/private/corpus.json \
  --map 1=handbook --map 2=notes --output /your/private/citations.json
```

Use actual document IDs already in your corpus. Each number has one declaration;
the same document may be selected for several numbers. Duplicate numbers and
unknown document IDs refuse the whole operation. Omitting `--map` explicitly
creates an empty mapping. This does not alter the corpus format or its bytes.

The new 0600 sidecar records exact raw and frozen Unicode-15 NFC subject hashes,
normalized character count, corpus-file and corpus-manifest hashes, the selected
documents' raw/NFC hashes and the parser/source identities. No answer or source
text is copied into it. A checksum detects changed bytes; it does not authenticate
the caller, source or installation. You can deliberately change declarations;
this is not a signed review or proof of a citation's intended target.

## Check the same captured inputs

```sh
python3 scripts/citation-resolution.py check \
  --subject /your/private/answer.txt --corpus /your/private/corpus.json \
  --sidecar /your/private/citations.json
```

The console prints occurrence counts only:

- `resolved-in-attached-corpus`: the supported number has your declaration to a
  document present with the captured bytes.
- `unresolved-in-attached-corpus`: the supported number has no declaration in
  this sidecar. It does not mean the source does not exist elsewhere.
- `unsupported`: bracket syntax falls outside the finite profile.

`COMPLETE` means this bounded inspection completed, including any unsupported
occurrences. Zero occurrences means no selected bracket markers, not absence of
all citations. Exit 0 is a completed observation. Exit 2 and fixed `UNAVAILABLE`
mean inputs, bindings, syntax options, limits or storage refused; no observation
or new private output is granted. No confidence, truth, source-support,
authenticity, freshness or independent-accuracy claim follows from either result.

For exact spans and bindings, explicitly add a new destination:

```sh
python3 scripts/citation-resolution.py check \
  --subject /your/private/answer.txt --corpus /your/private/corpus.json \
  --sidecar /your/private/citations.json \
  --private-report /your/private/citation-details.json
```

That 0600 file contains normalized subject marker spans, numbers, declared source
IDs and hashes, but no selected subject/source text. Hashes, IDs and spans can
still reveal or link information: share deliberately. The brief console omits
them. Nothing is saved automatically by `check`; existing files are never
overwritten. Changed raw subject bytes (even NFC-equivalent replacements),
corpus bytes, document bindings or method sources require a newly prepared
sidecar. Source hashes identify code; they do not authenticate an installation.

## Exact profile and limits

Only complete ASCII decimal `[1]` through `[9999]`, without leading zeros or
spaces, are supported. Every square-bracket group is inspected. Nested,
unmatched, escaped, nonnumeric, list/range and directly adjacent Markdown
link/definition forms are `unsupported`. An adjacent parenthesized/bracketed
link target or definition line is kept opaque, so an inner numeric token does
not become a new supported marker. For example, `[1][2]` is unsupported; `[1]
[2]` separated by whitespace contains two literal candidates. A backslash
immediately before a marker conservatively makes it unsupported. Only directly
adjacent link punctuation is recognized; whitespace-separated prose is inspected
as literal selected markers. This is not a general Markdown parser.

Quoted text, code examples and array indexing can contain the same literal
tokens. Their meaning is not interpreted. Author/year references, superscripts,
bare URLs, bibliography semantics, quotation/use-mention interpretation,
source lookup and inference are outside this profile. A caller's mapping can be
misleading. Do not interpret this as a reference-verification or falsehood badge.

Subject limits: 32,000 UTF-8 bytes and 8,000 original/NFC code points; at most 256
bracket occurrences. At most 128 mappings and a 64 KiB sidecar are accepted.
The existing corpus-v1 limits remain: at most 32 documents, 200,000 code points
per document, 2 MB combined source bytes and 4 MB serialized envelope. Private
details are bounded to 256 KiB. Excess refuses without clipping. Inputs are
captured through no-follow descriptors with pre-read size checks and stable
identity rechecks before output publication. These controls do not defend against
a malicious process already running as the same user or prove source truth.

Remove the sidecar/report files to remove these saved associations. The source
corpus remains independently user-controlled. There is no migration, hidden
collection, automatic attachment, capture hook or default-route registration.

## Verification and unfinished parent acceptance

Run the affected controls with the project's existing test environment:

```sh
python3 -m pytest -q tests/test_citation_resolution.py
```

The library exposes `prepare(corpus_bytes, subject_bytes, pairs)` and
`check(corpus_bytes, subject_bytes, sidecar_bytes)`. File callers should use the
CLI's descriptor-bound capture/export path; byte APIs validate the selected
captured values. Private details always bind the current method sources.

This implements FI's separate local resolution-evidence component. Full T-FI
still needs independent contradiction-versus-missing-evidence labels/error rates,
accepted tag mapping and supported human operation. No existing completion
percentage or release claim changes. See the [architecture and risks](fi-citation-sidecar-plan.md).
