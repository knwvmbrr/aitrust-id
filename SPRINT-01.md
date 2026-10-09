# Sprint 01 — AITrust-ID — "Make it public"

**Archived initial board.** Current truth is in `docs/master-scope.json`,
`state.json`, and `docs/live-launch-status.md`. Historical point-estimate gates
and completed claims below do not override current evidence. The initial commit
was not amended: c90bf99 removes `.DS_Store` from the current tree; earlier main
history remains unchanged.

**Window:** 14 days · **Started:** 2026-10-06 · **Board owner:** Claude (Cowork)

> **CODEX — READ THIS FIRST (2026-10-07).** This file was split today. It previously carried a
> second, unrelated project's sprint. That lane now lives outside the repo and is tracked in a
> separate chat. **This repo is AITrust-ID only.** If a task is not about the protocol, the
> spec, the extension, the services or the eval harness, it is in the wrong file — stop and
> flag it rather than implementing it.

## Sprint goal

> The protocol is public, readable without cloning, and CI is green.

## Definition of done

- [ ] `github.com/knwvmbrr/aitrust-id` is public, Apache-2.0, README reads cold
- [ ] `aitrustid.com` serves the spec and taxonomy over HTTPS
- [ ] Spec browsable as a site, not raw markdown
- [ ] CI green on `main`
- [ ] `ps_v1.jsonl` precision ≥ 0.93, recall ≥ 0.75
- [ ] Lighthouse ≥ 95 performance and accessibility on the spec site
- [ ] No personal or portfolio content anywhere in the repo history
- [ ] Every item below checked, or deferred **in writing** in the audit log

## Roles

| | Owner | Scope |
|---|---|---|
| **Michael** | Human + money | Accounts, domains, DNS, payments, pushes, approvals, decisions |
| **Claude (Cowork)** | Design + verification | Specs, acceptance criteria, content, review of Codex output, nothing-left-behind audit |
| **Codex** | Implementation | Everything not above |

Rule: one writer per file at a time. `PLAN.md` is the architectural contract; this file is the board.

---

## Lane M — Michael (unblocks everyone)

| # | Task | Blocks | Done when |
|---|---|---|---|
| ~~M1~~ | ~~clear `.git/index.lock`~~ **DONE 2026-10-06 by Claude** | — | ✅ |
| ~~M1b~~ | ~~accept Xcode CLT licence so git runs~~ **DONE 2026-10-07** | M2 | ✅ |
| **M2** | Create **public** repo `knwvmbrr/aitrust-id` on GitHub. No README, no .gitignore, no licence — they exist here | M3, C8, C9 | Empty repo exists |
| **M3** | `git remote add origin … && git push -u origin main` | **everything** | Repo visible logged out |
| M4 | Add `aitrustid.com` to Cloudflare; nameservers pointed | C8 | Zone active |
| M5 | Connect Cloudflare Pages to the repo; custom domain `aitrustid.com` | Launch | `https://aitrustid.com` resolves |
| M6 | Cloudflare Email Routing: `security@`, `conduct@`, `abuse@` → inbox | Launch | Test mail received |
| M7 | Decide: is `PLAN.md` public, or `PLAN.internal.md` + gitignored? | M3 | Decision recorded below |

**Spend:** $0. Domain already owned; Cloudflare Pages and GitHub are free tiers.

---

## Lane X — Codex (implementation)

| # | Task | Depends | Acceptance (Claude verifies) |
|---|---|---|---|
| C8 | Static spec site rendering `spec/` + `rfcs/` with nav, deployed from this repo | M3, M4 | Spec and all RFCs readable at a URL, no clone, no JS required for first paint |
| C9 | Make `.github/workflows/ci.yml` green — lint, pytest, `python eval/harness.py` | M3 | CI badge green on `main`; the `|| true` fallbacks are gone |
| C10 | **PS use/mention discriminator.** Suppress matches inside comments, inside fenced blocks quoted in prose, or within N chars of a negation marker | C9 | `ps_v1.jsonl` precision ≥ 0.93 **with** recall ≥ 0.75 |
| C11 | Schema conformance test: `spec/examples/*.json` validate against `assertion.schema.json` in CI, including one `modality: "image"` example rendering as `UNK / unsupported_modality` per RFC-0003 | C9 | CI fails if an example stops validating |
| C12 | Repo hygiene: real verbatim Apache-2.0 text in `LICENSE` (currently a stub), `.editorconfig`, `Makefile` (`up`, `down`, `test`, `gates`) | — | `make test` runs from a clean clone |

---

## Lane C — Claude (design, content, verification)

| # | Task | Output |
|---|---|---|
| ~~D1~~ | ~~Acceptance criteria for every C-task~~ **DONE** — the table above | this file |
| ~~D7~~ | ~~`README.md` rewrite for a cold reader~~ **DONE 2026-10-06** | `README.md` |
| ~~D8~~ | ~~RFC-0003 modality coverage~~ **DONE 2026-10-06** | `rfcs/0003-modality-coverage.md` |
| ~~D9~~ | ~~Split unrelated project content out of this repo~~ **DONE 2026-10-07** | separate project workspace, outside this repository |
| D10 | Spec-site copy: landing, taxonomy reference, how-to-read-an-assertion | `site/content/*.md` |
| ~~D11~~ | ~~Pre-push privacy audit~~ **DONE 2026-10-07 — PASSED** | audit note below |
| D12 | Review every Codex deliverable against its acceptance row before Michael merges | PR comments |
| D13 | Nothing-left-behind audit at day 12 — walk the Definition of Done line by line | audit note below |

---

## Sequence

```
Day 1       M2 M3                  repo public         ← CRITICAL PATH
Days 1–2    D11                    privacy audit BEFORE the push
Days 2–4    C12 C9  ·  D10         hygiene, CI green, spec-site copy
Days 3–6    M4 M5 → C8             aitrustid.com serving the spec
Days 5–8    C10 C11  ·  D12        PS precision, schema conformance
Day 6       M6                     the three promised email addresses exist
Days 9–12   buffer                 overflow, review
Day 12      D13                    nothing-left-behind audit
Days 13–14  launch                 announcement
```

**Critical path is D11 → M2 → M3.** The privacy audit runs *before* the push, not after —
a repo's history is public forever once it is.

---

## Decisions

- **2026-10-07 — Spec site goes to `aitrustid.com`, not GitHub Pages.** A standard hosted on an
  individual's personal domain reads as one person's project. Institutions adopt things that have
  their own address.
- **2026-10-07 — This repo is AITrust-ID only.** Unrelated work lives in its own repo and board.
- **M7 open:** is `PLAN.md` public? It contains the five invariants and the three
  deliberate non-goals. Claude's view: **publish it.** Stating what you refuse to build is a
  credibility asset, and nothing in it is personal.

## Backlog (Sprint 02+)

- **B2** — prove MV3 capture on one real site. Still the thesis blocker.
- **B5** — receipt issuance + offline verification against a public RFC 3161 TSA (RFC-0002).
  Buildable now, no browser needed. Strongest candidate for Sprint 02's goal.
- **B6** — key custody for non-technical authors. Unsolved.
- **PII_OUTBOUND** — pre-send check. Presidio is already in the stack.
- Behavioral signal implementation (RFC-0001).
- `document` modality — may deserve to jump ahead of `image` (RFC-0003, open question 1).

## Audit log

### 2026-10-06 — Claude
- **M1 cleared.** Stale `.git/index.lock` removed; git unblocked.
- **D7 done.** README rewritten for a cold reader; honest status table names what does NOT ship.
- **D8 done.** RFC-0003 drafted — reserves image/audio/video/document with normative subject-hash
  definitions. No detector proposed, no accuracy claimed.
- **Schema updated** per RFC-0003: `modality` enum now six values. Parses clean.
- **Invariant 6 added** to `CONTRIBUTING.md` — no capability withheld from an individual — plus
  the "nothing half-built ships" rule.

### 2026-10-07 — Claude
- **M1b confirmed.** Xcode CLT licence accepted; git runs.
- **D9 done — scope split.** This board previously carried a second, unrelated project's tasks.
  The file was **untracked**, so `git add -A` would have published them here. That lane was moved
  outside the repo. This repo is now single-purpose.
- **D11 DONE — privacy audit passed.** Scanned the full tree and the complete git history before
  any push.
  - Secrets / API keys / private keys: **clean**
  - Personal contact data (phone, email, addresses): **clean**
  - Committed `.env`: **clean** — only `.env.example`, which contains no secret
  - **One finding, fixed:** `.DS_Store` was in the initial commit. Removed from the index and the
    commit amended. It is unpushed, so history is clean rather than rewritten-after-the-fact.
  - **Verdict: SAFE TO PUSH PUBLIC.**
