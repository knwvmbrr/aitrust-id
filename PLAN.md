# PLAN.md — the shared contract

Both Claude Work and Claude Code read this file first. It is the only file that says
what is next. Update it at the end of every session, before you close the laptop.

---

## Current state

| Layer | State |
|---|---|
| Spec + taxonomy | Written, v0.1.0, in `spec/` |
| Extension | Scaffolded. **Capture UNPROVEN.** |
| Services | Skeleton runs. PS rules live, semantic tags stubbed. |
| Eval | Gates written. **Fixtures empty.** |
| Agent identity | Not started. Spec-first, no code. |
| Newsroom | Not started. |
| Town Hall | **Blocked** on moderators. Not before day 90. |

## NEXT ACTION

**B2 — prove MV3 capture on one real site.** Everything downstream depends on it.
If it fails, the product changes shape and we need to know in week one, not month three.

---

## The five invariants

Check every change against these. They are also in CONTRIBUTING.md.

1. **No paid dependencies.** A metered API is a rejected PR.
2. **No network egress at inference.** Docker topology enforces it; CI runs with networking off.
3. **No content in transit or at rest.** Hashes and character offsets only.
4. **Accessibility is a release gate.** A serious axe violation fails the build.
5. **No label claims more confidence than its evidence.** Publish the human agreement
   figure; set the floor beneath it.

## Three things we will not build

Decided 27 Aug 2026, after adversarial review. Recorded so they do not creep back in.

- **No automated AI content network.** A bot network promoting a bot-detection standard
  is self-refuting; our own `FA` tag would fire on it. The newsroom is human-edited with
  AI assist, and every post carries its own label.
- **No child-safety report hosting.** Mandatory-reporting law, COPPA, and the certainty of
  receiving illegal material. We label the harm where a child meets it, and route reports
  to NCMEC / IWF untouched.
- **No "rogue AI detection."** Unachievable from output alone. We ship agent identity for
  cooperating agents, and the spec states plainly that absence of an ID is not evidence
  of malice.

## Sequencing

1. Prove MV3 capture (B2) ← **gate for everything**
2. PS alone, shipped well
3. Reporting intake — policy first (A6 blocks B8)
4. Datasets and calibration, then HP
5. Newsroom
6. Town Hall, when moderators exist
7. MT last — hardest, most damaging to get wrong

## Track split

- **Claude Work** — research, spec prose, RFCs, policy, grants, trademark prep, site,
  design, newsroom, outreach.
- **Claude Code** — implementation, tests, CI, adapters, ONNX, release engineering,
  review against the five invariants.

Prose is drafted in Work and lands here as Markdown. Code is written and reviewed in Code.
Never paste code between them.

## Session log

Append one line per session: date, track, what moved, what is next.

- 2026-08-27 · Work · Repo scaffolded (38 files), site + master plan published. Next: B2.

---

## Session log — 2026-10-05 (Claude, Cowork)

**State changes**
- Repo placed under version control for the first time. `v0.1.0` committed as `c921225` on `main`, 40 files. No remote yet.
- README clone URL corrected from `github.com/USER/...` to `github.com/knwvmbrr/...`.
- `eval/datasets/unsafe_code/ps_v1.jsonl` written: 24 fixtures — 10 positive, 14 adversarial negatives.

**Finding — PS fails its own gate**
Running the current evaluator regexes over the new fixtures:
- 10/10 true positives matched. No misses.
- **2 false positives.** Both are context failures, not pattern failures:
  1. `"Never run \`curl ... | sh\`. Download the script, read it..."` — prose *warning against* the pattern.
  2. `"# bash history shows: curl https://example.com | sh"` — the pattern quoted inside a comment.

Precision = 10/12 = **0.833** against a gate of **0.93**. CI fails today.

This is the exact failure `eval/datasets/README.md` predicted: a PS detector that flags every `curl`
is useless. The rules match the string; they do not yet model whether the string is being
*used* or *mentioned*.

**NEXT ACTIONS**

- **B2 (unchanged, needs a real browser)** — prove MV3 capture on one real site. Blocks everything downstream. Owner: whoever is at the Mac.
- **B3 (new, no browser needed)** — give PS a use/mention discriminator before scoring: suppress when the match falls inside a comment, a fenced code block quoted in prose, or within N characters of a negation marker (`never`, `do not`, `avoid`, `instead of`). Re-run fixtures until precision clears 0.93 without dropping recall below 0.75.
- **B4** — extend fixtures to `unsourced/` (HP) and `persuasion/` (MT). MT needs ≥3 annotators per the README; it cannot be authored by one party alone.

**Handoff protocol**
One writer at a time. Whoever works updates this section before stopping. Claude (Cowork) can
read the whole repo, write files and commit, but **cannot delete files** — a stale
`.git/index.lock` currently blocks further commits and must be removed from the Mac.
Terminal-side agents own: deletes, `git push`, dependency installs, Docker, and the browser loop.

---

## Session log — 2026-10-06 (Claude, Cowork)

**Added**
- `rfcs/0001-behavioral-provenance.md` — registers six provenance signals for `PA`/`FA`, the two
  tags with the highest floors and, until now, zero detectors. Establishes the governing rule:
  a provenance signal may raise toward human, never lower toward machine.
- `rfcs/0002-authorship-receipts.md` — inverts the customer. Signed, timestamped, offline-verifiable
  receipts held by the author. Adds the calibration ledger and the licensing policy.
- `spec/signals.md` — every signal now carries a **cost to defeat** class
  (`statistical` / `behavioral` / `structural` / `cryptographic`). New provenance signal section.
  A signal with no stated class is non-conformant.

**The argument that drove it**

Detection degrades; attestation does not. A statistical signal will eventually be forged — cadence
is a distribution, and distributions can be sampled. A receipt signed and timestamped at composition
time cannot be forged later, because the fraud would have to be in the clock rather than the text.
Time is the only adversarial asymmetry that does not erode. This is why the defensive product is
also the durable architecture.

Consequence for ranking: **sort signals by cost to defeat, not by accuracy.** A 70%-accurate
`structural` signal outranks a 95%-accurate `statistical` one, because only one of them still
works in five years. `sig.outside_knowledge.v1` is the strongest behavioral signal in the system
for exactly this reason — a model cannot inject information it does not have, however well it is
trained to imitate a person.

**Policy adopted (RFC-0002)**

Spec, reference implementation, fixtures, calibration ledger, receipt issuance and receipt
verification are open and free, permanently. Only tooling that performs capture requiring explicit
human consent may sit behind a commercial gate, and a free path to issue and verify a receipt must
always exist. A person defending their own authorship never pays; an organization administering
capture across other people's machines does.

**NEXT ACTIONS**

- **B2** — prove MV3 capture on one real site. Still blocking. Needs a browser. Owner: whoever is at the Mac.
- **B3** — PS use/mention discriminator. Precision is 0.833 against a 0.93 gate. No browser needed.
- **B5 (new)** — prototype receipt issuance and offline verification against a public RFC 3161 TSA. Independent of B2; proves the cryptographic layer before the behavioral layer exists.
- **B6 (new)** — resolve key custody for non-technical authors. Open question 1 in RFC-0002 and the hardest unsolved problem in the design: every recovery mechanism reintroduces the central authority the architecture exists to avoid.

**Still blocked on the Mac**

Stale `.git/index.lock` prevents commits from this side. From Terminal:
`cd ~/Downloads/aitrust-id && rm -f .git/index.lock` — then create the GitHub repo and push.
- 2026-10-06 · Work · M1 lock cleared. D7 README + D8 RFC-0003 done. Schema modality enum expanded, Invariant 6 added. **Next: M2/M3 — push the repo public.**
