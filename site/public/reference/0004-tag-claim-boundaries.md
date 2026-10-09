# RFC 0004: Tag claim boundaries, error budgets, and result states

- Status: **proposed** — requires product-owner acceptance before any implementation
- Author: Claude
- Reviewer: Codex
- Supersedes: the `PS` row of `spec/taxonomy.md` v0.1.0
- Depends on: nothing. This RFC is specification only.

## Summary

Three changes, all consequences of one rule: **a tag makes the strongest claim its
evidence supports, and no stronger.**

1. `PS` is split. "Potential Scam / Risk" bundled an observation with an inference about
   intent. The observation ships now as `UC`; the inference becomes `SC`, which requires
   evidence we do not yet have.
2. Every tag declares an **error budget** — precision-weighted or recall-weighted — with
   a published reason. One uniform gate across nine tags was wrong.
3. `UNK` is split into **six** result states. A failed check must never render as a
   completed one.

It also registers two new tags, `SC` and `BT`, because the two findings people most need
are not in the current taxonomy.

## 1 · Why `PS` cannot ship as named

`PS` claims "Potential Scam / Risk". Its detectors match `curl … | sh` and base64 passed
to `eval`. The gap between those is an inference about a person's purpose, and we have no
evidence of purpose at all.

A maintainer publishing a one-line install command is not running a scam. Labelling that
response "Potential Scam" is a false accusation produced by our own taxonomy, not by a
detector bug — and no amount of precision tuning fixes a claim the evidence cannot reach.

### The split

| Code | Name | Claim | Evidence it needs |
|---|---|---|---|
| `UC` | Unsafe Command | This response contains an instruction that downloads remote content and executes it, or executes an encoded payload | Static pattern match plus use/mention context. **Already have it.** |
| `SC` | Scam Pattern | This response matches a pattern characteristic of fraud attempts | Composite: multiple independent indicators co-occurring. **Do not have it yet.** |

`PS` is deprecated as ambiguous. It is **not deleted** — the code remains reserved in the
registry, marked `split`, pointing at `UC` and `SC`, so an implementation reading an old
assertion still resolves it.

On acceptance, `docs/tags/PS-01.md` becomes `docs/tags/UC-01.md`. Its content stands as
written; only the code changes. The engineering lead owns that rename.

`UC` is the first tag to ship. Nothing in this RFC delays it.

## 2 · `SC` — Scam Pattern

Fraud detection does not work on single signals, and a single signal is why `PS` failed.
It works on **co-occurrence**. `SC` asserts only when indicators from two or more distinct
families appear together:

| Family | Indicator |
|---|---|
| Pressure | Deadline framing, consequence threat, secrecy instruction |
| Value transfer | Payment, gift card, wire, crypto address, credential request |
| Identity | Authority claim with no verifiable referent — "your bank's security team" |
| Channel | Instruction to move off-platform, or to avoid telling a named third party |

One family alone is not `SC`. A news article about a scam hits Pressure and Value transfer
by *describing* them, which is exactly the use/mention problem `UC` already has to solve —
so `SC` inherits that discriminator rather than reinventing it.

**The co-occurrence rule is a hypothesis, not a validated design.** Review was right to
label it that way. Requiring indicators from two families is a reasonable starting
structure borrowed from how fraud analysts describe the phenomenon; it has zero measurement
behind it here. Co-occurring weak indicators are not independent corroboration — they may
share a common cause, and in scam text they almost certainly do. The threshold, the family
boundaries, and whether two is the right number are all open until a corpus says
otherwise.

Every indicator is a local lexical or structural match. No model, no network, no cost.

## 3 · `BT` — Automation Pattern

`BT` would assert that text shows **positive evidence of automated generation at scale**.

**Corrected 2026-10-08 — the proposed indicators do not establish automation and are not
presented here as if they do.** Review was right: near-duplicate construction, templated
variation and timing regularity are each produced by humans constantly — form letters,
legal boilerplate, support scripts, anyone following a required format, anyone writing in
a second language from a learned pattern. They are **candidate indicators requiring
validation**, not evidence. No `BT` threshold, floor or detector may be proposed until a
labelled corpus shows which combination separates automation from ordinary human
repetition, and at what cost in false accusations.

If that corpus shows they do not separate, `BT` does not ship. That is an acceptable
outcome and better than the alternative.

Two constraints, both load-bearing:

**`BT` may never be asserted from the absence of human evidence.** This is the governing
rule of `spec/signals.md` applied to a new tag: absence of human signal produces a result
state, never an accusation. Calling a real person a bot is a harm we inflict, and the
people most likely to be miscalled are those who write in a second language, use assistive
input, or follow a template because their job requires it.

**`BT` describes text, not a person.** It is not an identity claim and may not be presented
as one. `N-009` already refuses rogue-AI verdicts inferred from output; `BT` sits under the
same refusal.

## 4 · Error budgets

The cost of being wrong is not the same for every tag, so the gate cannot be either. Each
tag declares a posture and the reason for it, published alongside its numbers.

| Tag | Posture | Why |
|---|---|---|
| `UC` | **Precision-weighted** | The audience is technical and can disable the tool. A false alarm on a legitimate install command teaches a developer to ignore every badge, and an ignored trust tool is worse than none. |
| `SC` | **Recall-weighted** | The audience includes people being actively targeted. A false alarm costs a few seconds and a dismissal. A miss can cost someone their savings. The asymmetry is enormous and it runs the other way. |
| `BT` | **Precision-weighted** | A false `BT` is an accusation against a person. Recall is not worth that. |
| `MT` | **Precision-weighted** | Annotators disagree about manipulation; a classifier may not claim more confidence than its labellers had. |
| `HP` `FI` `NF` | Undetermined | No corpus exists. Posture is set when the corpus is designed, not now. |

A recall-weighted tag carries obligations that a precision-weighted one does not, and they
are part of the gate:

- The wording says **possible**, never asserts fact.
- The evidence panel shows every indicator that fired, so the person can judge it themselves.
- Dismissal is one action and the tag does not return for that response.
- The measured false-positive rate is published on the public status page in plain language.

Trading precision for recall is legitimate. Hiding that you did it is not.

## 5 · Result states

`UNK` currently absorbs every outcome that is not a finding. That makes a backend outage
indistinguishable from a completed evaluation that found nothing — the tool reporting "we
looked and we're unsure" when it never looked at all.

Six states. (Corrected 2026-10-08: an earlier draft of this RFC said "five" above the
same six-row table, corrected in review.)

| State | Means | Must not be read as |
|---|---|---|
| `FINDING` | Evidence cleared the tag's floor | — |
| `NO_FINDING` | Checks ran; nothing they detect was present | **Safe.** Four detectors finding nothing is not a safety verdict |
| `UNCERTAIN` | Checks ran; evidence was insufficient to clear a floor | Any state below |
| `UNSUPPORTED` | This capability does not apply here — reserved modality, unsupported site | `UNCERTAIN` |
| `UNAVAILABLE` | **No valid evaluation could be obtained** — service down, invalid token, unreachable, upstream malformed. A partial internal step may have run; this state does not assert that nothing happened | `UNCERTAIN`. This is the dangerous conflation |
| `PENDING` | Evaluation in progress | Any completed state |

`UNK` is retained as a deprecated alias for `UNCERTAIN` so existing assertions resolve.
Adding these requires a schema change; `N-001` (protocol compatibility and migration)
covers it.

These five may not be collapsed for visual simplicity. `NO_FINDING` in particular needs
wording that does not imply clearance — a reader who takes "no findings" as "this is safe"
has been misled by us, not by the model.

## 6 · What this RFC does not do

- Does not claim `SC` or `BT` are implementable at a given accuracy. Both need corpora and
  measurement before any gate number is proposed.
- Does not set `UC`'s thresholds. `docs/tags/UC-01.md` holds them as candidates pending a
  frozen independent evaluation set.
- Does not touch provenance, authorship, or biometric scope. `X-04` stands: no per-person
  template, ever.
- Does not authorise any new endpoint, dependency, or network access.

## 7 · Open questions

1. `SC` needs a labelled corpus. Public consumer-protection complaint data is a candidate
   source; licence and representativeness both need checking before use.
2. Does `SC` apply to a model's own output only, or also to content a person pastes in for
   checking? The second is more useful to the person being targeted and is a different
   capture path.
3. `BT`'s scale indicators need more than one instance to compare against. A purely local
   tool sees one response at a time. This may be the first tag that cannot be fully local,
   which would make it the first tag with a real architectural cost — flag before building.
4. Wording for `NO_FINDING` that is honest and still useful to a non-technical reader.

## 8 · Acceptance

The product owner accepts or rejects each of the three changes independently. The
engineering lead reviews the architecture implications of §5 and §3's question 3.
