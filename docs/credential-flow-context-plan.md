# Credential-flow source/context architecture and risks

Before implementation, Codex, 2026-11-19. Base
`eb7873ddc861bfadf921d50d338ab2d2607e0d8b`; original target F-012 remains open.

## Confirmed defects before the new component

The standalone method accepts repeated keyword names because `ast.parse` alone
does not perform that compile-time check. A duplicate `data` call can therefore
produce STATIC_FLOW for a program Python cannot run. Refuse duplicate keywords
before expression propagation. Separately, repeated `a=a+a` statements can create
exponentially large propagated literal strings despite the subject limit. A safe
108-character/17-doubling instrumented fixture reached 131,072 characters; no OOM
payload was run. Check combined literal length before addition and refuse above
8,000. Version this refusal correction 1.0.1, retaining the published profile and
all original semantics on supported programs. Preserve original failed receipts.

## Missing capability and complete bounded deliverable

Existing credential-flow analysis takes standalone Python, and PS use/mention
rules inspect their own shell candidates. There is no explicit whole-document
context binding around a selected Python program. Build a separately invoked
prepare/check workflow; do not reuse a PS result or classify prose heuristically.

The caller selects original decoded-document codepoint spans for code and its
enclosing context, and declares recommended, quoted_example, or unknown. Bind
raw document bytes/hash, frozen NFC document/hash, raw/NFC code/context spans and
literal digests, declared context and method/source identities. Mapping requires
normalizing prefix/selection/suffix independently to reproduce the whole NFC
document, refusing boundaries whose normalization crosses the selection. Do not
silently dedent, strip fences or change the selected source. Analyze only the
selected code using the corrected canonical method and rebase its read/sink
locations into the normalized whole document. Context declarations remain
unverified caller assertions; recommendation/authorization/intent are not inferred.

Use one bounded, clean-environment pipe worker, existing group supervision,
macOS deny-network sandbox or the existing system-libseccomp mechanism adapted
into the new credential worker. Apply wall/CPU/memory/output/descriptor budgets;
required sandbox failure makes the observation Unavailable. No inspected code
is executed, imported, or interpolated into commands. Named credential files,
environment values and supplied URLs are never accessed. The parent checks
canonical result equality before rebasing/export; no structural-only score or
finding acceptance. Unknown evaluation yields null count, never measured zero.

## Isolation, privacy and acceptance

Own new credential-specific I/O, adapted with provenance from the audited
descriptor primitive; import no sibling tag. Keep no-follow regular bounded
private reads, stable source identity, no-overwrite 0600 exports, capture-owned
raw descriptors and exactly-once close. Report post-link/cleanup/close/link-outcome
uncertainty explicitly, without rollback claims or private diagnostics. The old
standalone checker must work with the optional context module absent/broken;
an unrelated independent checker must remain usable when credential context fails.

Owned existing files: `tools/credential_flow.py`, `tests/test_credential_flow.py`,
`docs/credential-flow.md`. Owned new files: credential-context library, private
I/O helper, worker, CLI, tests, this plan/guide and immutable runs/events. No PS
mapping, service, endpoint, shared catalogue/state/scope/board/CI changes.

Verify duplicate keyword/literal-growth refusal, adversarial declarations,
Unicode mapping and bisected boundaries, stale raw/NFC/code/context/source
bindings, private outputs, malformed arguments, canonical result corruption,
worker failure and tag independence. Run actual bounded Mac/Linux paths through
the existing authorized route without packages, credentials, Docker or deployment
changes. Require a different reviewer after freezing. Full F-012 acceptance still
needs the proposed Semgrep/use-mention integration contract, independent flow
validation and accepted PS mapping; these engineering controls cannot replace it.
