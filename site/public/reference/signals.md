# Registered Signals v0.1.0

A signal is a named, versioned detector. Changing a detector's behaviour requires a version
bump — this is what lets a third party reproduce an assertion.

This catalog includes specified and proposed methods; a row is not evidence of an
implemented or validated detector. Only the command-pattern development methods
described below currently execute in the evaluator. The remaining methods require
their own implementation, independent measurement, and release acceptance.

| ID | Feeds | Method | Cost to defeat | Notes |
|---|---|---|---|---|
| `sig.selfcontradiction.v1` | HP | NLI entailment between sentence pairs, contradiction probability | `statistical` | ONNX DeBERTa-v3-small; CPU |
| `sig.unsourced_specificity.v1` | HP | Precise figures / dates / named citations with no provenance marker in context | `statistical` | Proposed regex + NER; precision and recall are unmeasured |
| `sig.duplicate_loop.v1` | HP | n-gram repetition above threshold within response | `statistical` | Cheap; catches degenerate generation |
| `sig.hedge_collapse.v1` | HP | Hedging language absent where uncertainty is expected | `statistical` | Weak signal; never sufficient alone |
| `sig.urgency_frame.v1` | MT | Time-pressure lexicon + imperative density | `statistical` | |
| `sig.false_dilemma.v1` | MT | Binary-choice structure where alternatives exist | `statistical` | |
| `sig.authority_appeal.v1` | MT | Unattributed appeals to expertise or consensus | `statistical` | |
| `sig.piped_installer.v1` | PS (UC proposed) | `curl`/`wget` piped to a shell | `statistical` | **Corrected 2026-10-08:** previously claimed a near-zero false positive rate. The prior implementation produced 2 false positives on 24 regression examples. Regression precision 10/12 = 0.833, Wilson 95% CI 0.552&ndash;0.953. This does not estimate production accuracy. That development version is now historical; the current implementation uses v3 below |
| `sig.fetch_execute.v1` | PS | Historical fetch-and-execute prefix prototype | `statistical` | **Withdrawn from runtime 2026-10-08.** Matched downloads saved to files as if stdout were executed. Retained for historical traceability; no conformance acceptance or independent accuracy established. Superseded by the bounded development methods below |
| `sig.obfuscated_payload.v1` | PS | base64/hex blobs passed to `eval`/`exec` | `statistical` | |
| `sig.credential_exfil.v1` | PS | Reads a secret path and writes to a network sink | `statistical` | Semgrep ruleset |
| `sig.typosquat.v1` | PS | Package name within edit distance 1–2 of a top-N name | `statistical` | Offline snapshot; never queried at runtime |
| `sig.corpus_support.v1` | NF | Retrieval similarity above threshold against the attached local corpus | `behavioral` | Requires corpus |
| `sig.corpus_contradiction.v1` | FI | NLI contradiction against retrieved local passage | `behavioral` | Requires corpus |
| `presidio.entity.v1` | PII_REDACTED | Presidio entity recognition | n/a | Runs before any evaluation |

### Cost to defeat

Signals should be assessed by measured accuracy and by **cost to defeat** over time. One ladder, two
directions: a provenance signal is *forged*, a content signal is *evaded*. The question is the
same — what does an adversary have to spend?

| Class | Meaning |
|---|---|
| `statistical` | A distribution an adversary can learn, sample or tune around |
| `behavioral` | Requires simulating a whole session, not just an output |
| `structural` | Requires information the adversary does not possess |
| `cryptographic` | Requires breaking a signature or a clock |

These classes describe a proposed threat model, not measured durability or a guarantee
that one class remains accurate longer than another. Release notes must distinguish
measured performance from assumptions about evasion.

## Provenance signals

Specified by RFC-0001 and RFC-0002 to feed `PA` and `FA`. These methods are not implemented
in the current extension. Their proposed local processing and data-flow restrictions
must be verified when implemented; they are not current runtime guarantees.

| ID | Feeds | Method | Cost to defeat | Notes |
|---|---|---|---|---|
| `sig.keystroke_liveness.v1` | PA | Dwell and flight time distributions over the composition window | `statistical` | Scalar only. **Never a per-person template.** Suppressed entirely when assistive input is detected |
| `sig.revision_churn.v1` | PA | Deleted-and-rewritten characters over final length; count of non-adjacent edit positions | `behavioral` | Unvalidated revision-pattern hypothesis; both people and models can revise or emit monotonic text |
| `sig.compose_monotonicity.v1` | PA | Caret-position entropy across the window | `behavioral` | Caret movement may describe editing; it does not establish authorship or automation |
| `sig.outside_knowledge.v1` | PA | A revision introduces an entity, figure or claim not derivable from the captured session context | `structural` (proposed) | Unvalidated hypothesis. Both humans and models can introduce material absent from captured context; this does not establish human authorship |
| `sig.attention_shape.v1` | PA | Read-pause-write rhythm from `visibilitychange` and focus events | `behavioral` | Proposed focus/timing summary; disability compatibility and identifying/linking risk are unmeasured |
| `sig.paste_burst.v1` | FA | Insertion of ≥N characters with no preceding keystroke activity in the field | `behavioral` | Evidence of insertion, not of origin |
| `sig.c2pa_manifest.v1` | FA | Parses an attached C2PA manifest and reports its assertions | `cryptographic` | Signer identity, integrity and revocation are separate claims; no authenticity or truth follows from a manifest alone |
| `sig.assistive_input.v1` | *routing* | Detects switch access, voice dictation, on-screen keyboard, eye tracking, IME composition | n/a | **Suppresses timing signals; never scores.** **Corrected 2026-10-08:** this previously said it "routes to `IV`". It cannot &mdash; `IV` requires a person to attest and sign, and no detector may assign it (`X-11`). Suppression yields a result state, not an attestation |

### The governing rule

A provenance signal may raise toward `PA` or `FA`. **A provenance signal may never lower a tag
toward a human-negative verdict.** Absence of human signal produces `UNK`, never `FA`. We do not
get to call something machine-made because we failed to witness a person.

## Adding a signal

1. Open an RFC with the detection basis and a labeled fixture set.
2. Report precision and recall on held-out data.
3. Register the ID here with a `.v1` suffix. Never mutate an existing version.
4. State its **cost to defeat** class. A signal with no stated class is not conformant.

## Development methods awaiting conformance acceptance

These versioned IDs prevent a behavior change from being presented as v1. They are
implementation identifiers, not accepted conformance registrations: independent
held-out measurements required by the process above are still missing.

| ID | Current tag | Executed method | Limitations |
|---|---|---|---|
| `sig.piped_installer.v2` | PS | Case-insensitive lexical match for `curl` or `wget`, a pipe, optional `sudo`, and `sh` or `bash` | No shell parsing or execution; line comments and immediately preceding explicit warning phrases suppress a match. Other quoted/reporting contexts can still trigger. Misses unsupported syntax and obfuscation |
| `sig.obfuscated_payload.v2` | PS | Lexical match for `eval` or `exec` receiving `base64.b64decode`, `atob`, or `bytes.fromhex` | No payload decoding, execution, or intent inference; same narrow warning/comment suppression. Misses unsupported language forms |

These methods have `statistical` evasion class. The shared 24-example regression run
has TP=10, FP=0, FN=0, TN=14. It is a development check, not independent accuracy
evidence. The 95% Wilson lower bound for both precision and recall is about 0.722.
Scores (0.97 and 0.88) are uncalibrated heuristics and must not be read as probabilities.
Exact reproducibility uses the evaluator source hash recorded in each assertion;
the implementation source is `services/evaluator/app.py`.

### Substitution methods reconciled after live review

| ID | Current tag | Executed method | Limitations |
|---|---|---|---|
| `sig.remote_command_substitution.v2` | PS | Bounded direct curl/wget stdout substitution into a supported shell `-c`, interpreter `-c`/`-e`, or `eval`; includes a second shell evaluation layer for single-quoted shell arguments | No nested shell parser, remote fetching or execution. Download-to-file, literal Python single quotes, line comments, immediate warnings and recognized literal echo/printf display are excluded. Other reporting/quoting forms remain unvalidated |
| `sig.remote_process_substitution.v2` | PS | Bounded direct curl/wget stdout process substitution into supported shells/interpreters, `source` or `.` | Simple expressions only; output routing guard applies. No intent or scam inference |
| `sig.remote_backtick_substitution.v1` | PS | Same bounded stdout and execution-layer checks for backtick substitution | Does not parse nested substitutions, all languages or all quoting forms |

The earlier unregistered `remote_command_substitution.v1` and
`remote_process_substitution.v1` development implementations remain in historical
source/evidence and are inactive. The v2 forms consolidate the evaluation-layer and
context handling. `fetch_execute.v1` is inactive rather than silently narrowed.
These methods remain development identifiers awaiting independent measurement and
conformance acceptance. Their scores are uncalibrated 0.97 heuristics. Historical method
revision is `context-v4`; exact source SHA-256 is included in runtime assertions.
The current execution report is `runs/2026-10-08-live-gap-implementation.json`.
Historical `counterexamples_v1.jsonl` rows 2–3 have disputed negative labels:
local shell-layer execution shows substitution can run in a second shell.
`counterexamples_v2.jsonl` preserves and explicitly supersedes those labels for
regression checks; it is not independent ground truth.


### Routing and literal-display correction (context-v5)

The active PS methods are `sig.piped_installer.v3`,
`sig.remote_command_substitution.v3`, `sig.remote_process_substitution.v3`,
`sig.remote_backtick_substitution.v2`, and unchanged
`sig.obfuscated_payload.v2`. Earlier versions remain historical development
identifiers, not current implementations or accepted conformance registrations.

Piped downloads now use the same stdout-routing guard as substitutions. Curl
file output and wget's default file output do not establish a supported
network-to-shell flow. Recognized literal echo/printf display does not establish
execution; a separate command after a display is still evaluated. Option values
are consumed instead of reading letters inside headers as output flags.

This is bounded token recognition, not a shell or complete curl/wget parser.
Config files, multiple-transfer curl syntax, complex redirections, multiline
expressions and other unrecognized quoting need separate coverage. Conservative
non-matches on unsupported syntax are not safety clearances. No network payload
is fetched or executed during evaluation. Scores remain uncalibrated heuristics.

Five active development sets now contain 86 cases: TP=31, FP=0, FN=0, TN=55.
These were used in development, including detector-author additions, and are not
independent accuracy evidence. Exact source hashes identify the active method.
See `runs/2026-10-08-ps-routing-regressions.json` for per-set counts.

## Machine catalogue and reproducibility boundary

`spec/signal-registry.json` preserves every fully qualified ID and two historical
substitution v1 IDs. The legacy scope title says 22; the catalogue originally contained
33 distinct versions before the context-v6 additions. `python3 scripts/verify-signals.py --signal ID`
returns status, method and current implementation hashes without reading user
content. `--check` rejects a missing ID, changed active-code set or unsupported
registration claim. Proposed and historical methods have no current source
binding and cannot be used as active evidence.

IDs identify methods, not sufficient input for replay. Reproducing a PS observation
also requires the exact normalized, redacted text and evaluator source/dependencies.
PII reproduction requires the pre-redaction text and pinned recognizer; the current
assertion does not carry that recognizer identity. Do not publish private text to
fill this gap. F-003 remains open for complete per-assertion reproducibility.

### Bounded scanning correction (context-v6)

The active development IDs are `sig.piped_installer.v4`, `sig.remote_command_substitution.v4`, `sig.remote_process_substitution.v4`, `sig.remote_backtick_substitution.v3`, `sig.obfuscated_payload.v3`. Older versions remain historical. The exact prior source is archived at `eval/methods/context-v5.py` (SHA-256 `8eca778f68bc889e26be2fbbe5e6bc3cadad51a53c647a7f2669e8ec554e263a`).

Warning, comment and literal-display context is indexed once. Pipe candidates are scanned in disjoint command-delimiter windows; a fetch must occur on the same physical line as its pipe. Whitespace after the pipe may lead to its receiving shell on another line. Arbitrary multiline/continued commands remain unsupported. Source and behavior changes require fresh regressions and release evaluation; heuristic scores remain uncalibrated. The catalogue now retains 38 distinct versions.

Context-v6 command word boundaries use the explicit Unicode-15 word class in the evaluator source, not the host Python Unicode database. Post-15 assignments follow this frozen interpretation; surrounding prose is still outside a full shell parser. The generation record is `eval/methods/unicode15-word-class.json`.
