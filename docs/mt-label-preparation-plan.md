# MT label preparation · architecture before implementation

Codex / web_camo, 2026-11-22. Isolated `codex/mt-label-preparation` from frozen
8391161a354f3af1aa8fa8a5bc92c63bb0fc9aa8. JPEG remains untouched. Existing scope:
TAG-MT-A01, T-MT, F-019a/b/c, F-056. This delivers preparation software and a
candidate annotation guide, not independent human labels, an adopted protocol,
a released MT detector or full completion of those originals.

## Actual gap and reusable foundations

`mt_workflow.py` supplies literal observations; it performs no annotation.
`prepare-ps-review.py` freezes PS-only forms bound to a PS evaluator/gates recipe;
relabeling that packet MT would be incorrect. `reviewer-agreement.md` explicitly
says the MT guide and collection remain unfinished. Reuse the unchanged
`reviewer_agreement.nominal_agreement` separately for four axes and the frozen
Unicode15 NFC implementation. Do not run or import any detector, SDK or model.

The current `blind_review_io.py` provides useful private-file rules but lacks
this new multi-file publisher's explicit late-close/publication-uncertainty
contract. Its raw `fdopen` ownership and generic post-publication errors are not
a suitable dependency for the new route. Add MT-owned I/O adapted from the
existing foundational migration Capture's close-once/no-replace/typed uncertainty
pattern. Preserve all old sources; no dependency on another tag's availability.

## Owned files and workflow

New `tools/mt_label_preparation.py`, `tools/mt_label_io.py`,
`scripts/mt-label-preparation.py`, `scripts/verify-mt-label-preparation.py`,
`tests/test_mt_label_preparation.py`, `docs/mt-annotation-guide.md`, this plan,
`docs/mt-label-preparation.md`, result/evidence and own attributed changelog.
No shared state, scope, catalogue, evaluator, method, SDK, endpoint or CI change.

`prepare` reads one explicitly selected private JSON input: language en and
1–256 items, each opaque source ID, text and caller-selected unverified context.
Each text/context is at most8000 raw/NFC codepoints; whole input at most2MiB.
Strip original IDs from reviewer forms, assign neutral Unit ordinals, shuffle
blank forms independently, include fixed candidate rubric and no predictions,
source/category hints or filled labels. Display NFC text; retain exact rawUTF8
and normalized identities privately. Spans use NFC Unicode codepoints, never
UTF16 offsets. Original IDs are not evidence of reviewer identity.

Four candidate axes cover pressure/legitimate urgency/persuasion; binary choice
and feasible alternatives; authority/source attribution; use vs quotation/mention.
Every axis includes uncertain and insufficient_context. Require complete fixed
labels/reasons and bounded subject/context evidence for substantive judgments;
constrained-choice alternatives require an explicit context anchor. No writer
intent, correctness or real-world truth follows from a label or selected context.
Multiple cues/quoted uses are explicit; no single combined MT label or score.

`validate` checks one complete supplied response against the explicit original
input plus packet. `compare` requires that original input again and both explicit
responses. Reconstruct the complete packet/blank forms from current fixed rubric,
raw input and source identities; hashes in a mutable colocated manifest alone
are not trusted. Changed raw canonically equivalent inputs, unknown fields,
changed examples/identities, duplicate/missing units/axes, incomplete reasons,
invalid evidence or wrong slots refuse. A coherently changed original explicitly
selected by the operator is a new input, not authenticated prior evidence.

`compare` emits separate nominal matrices and summaries per axis, plus a private
queue for disagreements and any uncertain/insufficient judgment. Preserve those
categories as actual ratings, never negative or missing. Report uncertainty,
insufficient-context and decisive coverage separately per axis. A high alpha
without useful decisive coverage is not validation. Constant categories retain
the original helper's Unavailable alpha. Candidate0.55/candidate_met are labeled
unadopted; no wrapper MTpass, accuracy, category-error or calibration assessment.

## Privacy, integrity and publication risks

All private input/response files must be owner-held0600 beneath a private0700
parent outside any Git checkout. No-follow/nonblocking regular-file descriptors,
pre-read byte caps, held path/snapshot checks and fixed diagnostics protect file
selection. Bounded JSON rejects duplicates, nonfinite/deep/oversized values.
No CSV/HTML, input execution, fetch, uploads, text/reasons/IDs/hashes in default
console summaries, account, telemetry or background job. Aggregate counts can
still reveal small-set distributions; sharing is always deliberate.

Validate and serialize everything before exclusively creating a new0700 output
directory; members0600, aggregate at most8MiB. Never overwrite/adopt an existing
destination. Retain all owned raw descriptors before fdopen(closefd=False), close
once and attempt all closes. Recheck inputs/source before completion. After any
possible directory/file publication or uncertain cleanup/close, typed uncertainty
warns that private output may remain and must not be treated as accepted evidence.
Never delete a replaced inode or promise crash-atomic rollback. Missing/invalid
responses expose refusal, never zero findings/labels. No imported packet can
claim human independence, protocol adoption, accuracy or release authority.

## Verification and limits

Focused stdlib tests: full prepare→two synthetic supplied responses→validate→
compare, all categories/coverage/constant-alpha cases, rawNFC and source rebind,
span boundaries, unknown/private fields, incomplete/duplicate ratings, nofollow,
size/permissions/nooverwrite, pre/post-publication and constructor/close faults.
Actual public CLI exercise uses authored synthetic examples and two explicitly
synthetic rater files (not two people), with altered-source/form/refusal/recovery.
Capture source before/after and source-bound receipt; separate peer review before
handoff. No local native/browser/build/install or disk-heavy job. Numeric gates,
independent multiple humans, adjudication, sampling, error study, calibration and
owner/protocol acceptance stay pending. Other tags never consume this agreement
as a release gate.

Implementation pre-freeze correction: an authored boundary control reproduced
Python's bool/int equality allowing false instead of a frozen integer zero in
response identity facts. Canonical typed JSON-byte equality now validates those
facts; original failure is retained and bool/float regressions refuse. Cap held
descriptors at256 before each open and fail closed where POSIX no-follow support
is absent. These are preparation integrity/resource controls, not human evidence.

Peer pre-freeze counterexample: after output creation a private held ancestor
could acquire a .git marker without changing its inode/mode. The prior final
check accepted that path. Retain the actual synthetic counter and amend only
MT-owned IO: remember held private-directory descriptors, recheck marker absence
at every check and successful context exit, reject a reserved .git destination
before mutation, and clear captured descriptor references before one close. A
post-publication marker/check/close refusal is OutputUncertain, never accepted
evidence or a rollback promise. Source/module/evaluator behavior is otherwise
unchanged; replay affected counter/positive and fresh actual CLI once.
The same final integrity amendment uses bounded directory iteration (at most the
fixed member count plus one) and refuses extra packet members before response
validation. Blank/returned forms remain separate explicitly selected data; the
validator does not open the other rater's form to inspect their answers. Output
membership checks use the same bounded iterator rather than unbounded listdir.
