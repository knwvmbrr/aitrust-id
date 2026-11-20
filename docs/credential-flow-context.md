# Inspect selected Python in its declared context

This optional offline development workflow binds selected Python code to the
document and surrounding context you choose. The existing credential-flow
method reports supported static reads passed into HTTP-call arguments. You
separately declare the selected context as `recommended`, `quoted_example` or
`unknown`. That declaration is **not verified or inferred by the checker**.

The same static flow can occur in a recommendation, a warning or a quoted
example. None of these results proves intent, authorization, execution, live
credentials or an actual transfer. No PS or other tag is issued. The standalone
[credential-flow command](credential-flow.md) remains available independently.

## Select your own document and code

Use CPython 3.12+ on macOS or Linux. No third-party Python package, requests
installation, account, model, Docker or network service is needed. The worker
requires existing macOS `sandbox-exec`, or system `libseccomp.so.2` on Linux
x86_64/aarch64. Missing required isolation yields Unavailable; no package is
downloaded and no unrestricted fallback is used.

Save the explicitly chosen document as UTF-8 in a private directory outside
the source checkout. Input files must be owner-held, regular, single-link and
mode 0600, without symlink ancestors. Output directories must already exist,
belong to you and use mode 0700. Keep credentials, private examples and selected
document text out of command arguments, public source and issue reports.

Create a private `selection.json` with exactly these fields:

```json
{"format":"credential-context-selection/v1","code_span":[0,5],"context_span":[0,5],"declared_context":"unknown"}
```

This minimal example selects the whole document `pass\n` (five codepoints).
For an actual document choose the code and an enclosing context range. Positions
are zero-based, end-exclusive **original decoded-document Unicode codepoints**,
not UTF-8 bytes, UTF-16 units, NFC positions or grapheme/screen columns. The code
range must lie inside the context range. A fenced example requires selecting
the Python inside the fences yourself; no fence removal, dedenting or whitespace
repair is inferred. An unsupported program becomes Unavailable.

## Prepare, then inspect the same bytes

```sh
python3 scripts/credential-flow-context.py prepare \
  --document /your/private/document.txt --selection /your/private/selection.json \
  --output /your/private/context.json
python3 scripts/credential-flow-context.py check \
  --document /your/private/document.txt --sidecar /your/private/context.json
```

Preparation captures whole raw document bytes/hash, whole frozen Unicode-15 NFC
document/hash, raw/NFC code and context spans, selected raw/NFC literal digests,
the caller's context declaration, canonical selection digest and method/source identities. It creates a new
0600 sidecar containing no selected words. Preparation binds a selection; it
does not promise that its Python program is supported.

Span mapping must reproduce the whole NFC document by normalizing the selected
prefix, content and suffix separately. Cuts that would change normalization
across a boundary refuse, rather than guessing positions or moving neighboring
text. No visual-grapheme boundary guarantee is claimed. Editing even raw bytes
that normalize identically requires a newly prepared sidecar. Source/selection
changes, unknown fields or stale hashes also refuse. A checksum identifies bytes;
it does not authenticate the caller, document or installed code.

`check` sends only selected normalized Python through a private pipe to the
bounded static worker. It never runs or imports that program, opens paths named
by it, consults named environment values or contacts its supplied URLs. Whole
surrounding prose is not supplied to an inference service. The parent compares
the complete result with the same capped canonical AST method before export,
then rebases read/sink positions into the normalized whole document. This checks
record consistency, not independent accuracy.

## Read the result without inventing use or intent

- `STATIC_FLOW`: at least one supported static credential read reaches a
  supported HTTP argument in the selected Python. This is program structure,
  not proof of exfiltration, recommendation or execution.
- `NO_SUPPORTED_FLOW`: the supported profile completed with no such flow.
  `flow_count: 0` is measured within that profile, not a safety clearance.
- `UNAVAILABLE`: source, prerequisites, worker, result or binding could not be
  evaluated. The count is null or absent, never a measured zero.

Completed observations exit 0; Unavailable exits2. `declared_context` always
remains caller-declared and unverified, including `recommended`. Quoted/example
context does not suppress a static flow or establish that it is harmless.
`unknown` does not become a recommendation. `use_mention_inferred`,
`authorization_or_intent_established`, `live_credential_verified`,
`independent_accuracy_evidence` and `PS_mapping_performed` remain false.

The console prints only fixed states, counts and your finite context label.
It omits selected words, source hashes, file paths, secret-key names, supplied
URLs and positions. Add `--private-report /your/private/report.json` to `check`
only if you deliberately want a new 0600 detailed record. It includes the
canonical code-relative observation plus explicitly named whole-document NFC
read/sink spans and identities, not document/code/context text. Hashes and
positions can still link information: share deliberately. No result file is
created if analysis is Unavailable. Delete your saved sidecar/report to remove
them; the tool does not collect, train on or automatically share input.

## Bounded failure and file handling

The document is at most 64,000 UTF-8 bytes and 16,000 raw/NFC codepoints. Selected
code is at most 8,000 raw/NFC codepoints; sidecars are at most 64 KiB and private results 256 KiB; the JSON-escaped worker request is bounded to 128 KiB. The canonical method keeps its 2,000 AST-node,
expression-depth 32 and 8,000-character propagated-literal bounds. Duplicate call
keyword names refuse. No input is silently clipped into a negative result.

Workers use fixed arguments, `-I -S -B`, a cleared environment, a six-second wall
deadline and existing owned-process-group cleanup (up to five additional seconds).
CPU 3 seconds, file/core 0 and descriptor 256 limits apply; Linux also sets 512 MiB
address space. IPv4/IPv6 loopback network-denial probes must pass before inspecting
code. Inspected text is never interpolated into code or a shell command. These
are narrow trusted-source/static-input protections, not an arbitrary-code sandbox.

Files are opened through no-follow descriptors, bounded before reading and
rechecked for drift before publication. New output uses atomic no-replace linking
of complete 0600 bytes. Ordinary pre-publication refusal commits no new final
destination, but failed cleanup can leave private `.credential-context-*` files.
After a successful/uncertain link, a sync/cleanup/close failure returns fixed
`output_commit_uncertain`, `output_may_exist: true`, exit 2. Inspect your requested
destination and private directory before retrying; do not assume rollback, delete
a complete file automatically or treat the failed export as accepted evidence.
Abrupt process/power loss may prevent delivery of any result. Raw descriptors
remain capture-owned with `closefd=False`; closes are attempted once even after
stream construction fails, and possibly reused descriptor numbers are not retried.
Same-UID hostile processes or compromised installations are outside this guarantee.

Run the focused controls in your existing development environment:

```sh
python3 -m pytest -q tests/test_credential_flow.py tests/test_credential_flow_context.py
```

F-012 remains open for its full proposed Semgrep/use-mention integration,
independent credential-flow validation and accepted PS mapping. These invented
engineering controls do not fulfill those gates. See the
[architecture and risks](credential-flow-context-plan.md).
