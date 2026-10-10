# Decisions

Machine source: [dated decision ledger](docs/decisions.json). The 15 existing open decisions were recorded at **2026-10-10T14:24:11.737441+00:00**. This is a recording date, not an invented historical decision or approval. Each proposal keeps its owner, reason and separate acceptance. No operating board is implied.

| ID | Status | Owner | Decision | Reason | Blocks |
|---|---|---|---|---|---|
| D1 | open | Michael | Current development allowlist: `PS` + `PII_REDACTED`. HP cannot assert. `UC` requires D18 acceptance before any rename. | PS/PII enforcement is implemented and tested; successor-code adoption stays open | Increment 0 close |
| D18 | open | Michael | Split `PS` into `UC` (unsafe command — observation) and `SC` (scam pattern — composite). See `rfcs/0004`. | Consider distinct command-risk and scam-pattern claims. Naming alone does not establish an accusation or measurement; adoption remains the owner’s decision. | Tag contract rename |
| D19 | open | Michael | Register `SC` (scam pattern) and `BT` (automation pattern) as new tags. | Accept. These are the two findings people most need and neither is in the taxonomy | Corpus work |
| D20 | open | Michael | Per-tag error budgets: `UC` precision-weighted, `SC` recall-weighted. | Accept. The false-positive cost is not uniform across audiences | `gates.yaml` adoption |
| D17 | open | Michael | Six result states distinct from overloaded `UNK`: pending, finding, no-finding, uncertain, unsupported and unavailable. Protocol adoption requires its own versioned decision. | Accept. A backend outage must not render as "evaluated, uncertain" | Schema RFC |
| D13 | open | Michael | Broader supported sites after the selected Chrome + ChatGPT adapter. | First route authorized by installation/use; further vendor support requires separate evidence | Additional vendor adapters |
| D16 | open | Michael | Who adjudicates `UC` ground truth independently of whoever drafts the fixtures. | Community reports are a candidate pipeline; adjudicators must not be the drafters | Evaluation |
| D3 | open | Michael | Publish the capture-integrity limitation prominently, or in an appendix. | Prominently. Reviewers will find it anyway; better in our words | — |
| D4 | open | Michael | Townhall venue: GitHub Discussions vs self-hosted. | Discussions first. Zero cost, moderation tools exist, migrates later | — |
| D5 | open | Michael + counsel | Certification mark vs ordinary trademark. [37 CFR 2.45](https://www.law.cornell.edu/cfr/text/37/2.45) requires a certification-mark applicant to state it is not producing or marketing the goods the mark certifies. | Counsel compares options before any filing. **Not a prerequisite for shipping a local tool** | — |
| D11 | open | Michael | Cut the registry container from 0.1. | Accept. Nothing writes to it; it adds a container and an attack surface for no user-visible outcome | — |
| D12 | open | Michael | Describe the subject hash as a correlation identifier, not an anonymisation. | Accept. A hash over short predictable text is dictionary-guessable | — |
| D14 | open | Michael | Defer behavioural provenance past 1.0 pending qualified legal review. | Defer pending qualified review. Scalar measurements can still reveal or link a person; non-identification is a proposed restriction, not a legal exemption. | — |
| D15 | open | Michael | No assertion signing in 0.1. | A signature authenticates signed bytes and their key association, not the truth of a verdict or content provenance. Keep the current unsigned profile explicit. | — |
| D21 | open | Michael | `SC` scope: model output only, or also content a person pastes in to check? | Pasting is more useful to someone being targeted, and is a different capture path. Decide before `SC` architecture | — |

Historic observations below retain their dates and limits. Later dated entries supersede earlier deployment/purchase status; they are not fresh runtime checks.

## Accepted

- **2026-10-08 — GitHub:** user authorized creation under `knwvmbrr`. Public empty repository `knwvmbrr/aitrust-id` created; HTTPS origin connected and account write permission verified. No code pushed. D10 resolved.
- **2026-10-08 — Brief explanations:** in-use tag dialogs show short descriptions; full definitions/testing stay in the site catalogue. Structured records are available through explicit local download.
- **2026-10-08 — Research data direction:** remotely hosted, open-source software, owner control and a free initial option required. N-011 preserves training/pattern/anomaly scope. Owner selected an existing remote server for self-hosted PostgreSQL. Connection details, collection/consent and retention remain unresolved; no forwarding enabled.

## Settled by evidence, not preference

These were not choices. They are what verification found, recorded so they are not re-argued.

| Date | Finding | Evidence |
|---|---|---|
| 2026-10-07 | A floor of `1.01` cannot be used to disable a tag. | `spec/assertion.schema.json` sets `"maximum": 1` on `floor` |
| 2026-10-07 | `UC`/`PS` precision is 10/12 = 0.833, Wilson 95% CI 0.552–0.953 on 12 predicted positives. The 24 fixtures are 10 positive + 14 adversarial negatives. | `PLAN.md` lines 85, 89–94 |
| 2026-10-07 | Gating on the point estimate would have passed an unmeasurable result. Gates test the lower bound. | Derived from the above |
| 2026-10-08 | `.DS_Store` is absent from the current committed tree at `c90bf99`. It remains in the parent commit `c921225`. No history was rewritten. | `git ls-tree -r HEAD --name-only \| grep -c DS_Store` → 0 |
| 2026-10-07 | A minimum abstention rate on a deterministic detector has no defensible rationale. | Rules-only evaluator; abstention rate is a property of the data |

## Adjudicated 2026-10-08 — settled by execution, between Claude and Codex

| # | Question | Resolution | How it was settled |
|---|---|---|---|
| A1 | Is `bash -c '$(curl …)'` a positive or a negative? | **Positive.** Codex was right, Claude was wrong. | `bash -c '$(echo echo X)'` prints `X`. Single quotes stop only the OUTER shell; `bash -c`/`sh -c` then execute the string as shell and the inner shell substitutes. `python3 -c '$(…)'` is a SyntaxError, so that one is correctly negative — the split is which interpreter receives the string, not the quoting. Claude's counterexample rows were relabelled. |
| A2 | Duplicate signals: `sig.fetch_execute.v1` vs Codex's substitution family | **Codex's family wins.** `fetch_execute.v1` withdrawn from runtime, retained in the registry as inactive. | Codex's split is finer-grained per shape; registry rule "never mutate a registered version" honoured by withdrawal rather than deletion. |
| A3 | Should a non-allowlisted candidate be an abstention? | **Depends on the code.** Adopted-but-disabled (HP, MT) → abstention with `floor: null`, reason `not_in_production_allowlist`. Unadopted or unknown (UC, SC, BT, UNKNOWN) → raise, an upstream contract failure. | Claude's V-01 recorded both as abstentions, producing schema-invalid assertions. Codex's split verified: 0 schema-invalid, HP still cannot assert but leaves a record. |
| A4 | Does a switched-off capability have a confidence floor? | **No — `floor: null`.** | Claude emitted `1.0`, which invents a threshold the candidate could notionally clear. Codex's schema conditional is correct. |

## Reversed

| Date | Was | Now | Why |
|---|---|---|---|
| 2026-10-07 | "Precision cannot be measured on 24 examples." | Report the point estimate with a Wilson interval and gate on the lower bound. | Too absolute. It can be measured; the uncertainty and coverage are poor, which is a different and statable problem |
| 2026-10-07 | Disable HP by setting its floor above 1. | Explicit production allowlist. | Schema-invalid, and it disguises release policy as calibration |
| 2026-10-07 | Ship at whatever lower bound the corpus supports, and publish the number. | If a gate fails: improve the detector, narrow the categories, continue as a research preview with no accuracy claim, or defer. | Converting an acceptance criterion into a disclosure is the exact pattern this project exists to oppose |
| 2026-10-07 | Commit raw transcripts, screenshots and browser recordings as evidence. | Sanitised public verification reports with commit and environment identifiers; raw evidence stays private; demonstrations use synthetic content. | A clean-clone transcript contains the bearer token; a capture recording contains real conversations. That is a privacy leak inside a privacy tool |
| 2026-10-07 | Commercial offerings must leave the foundation; certification is the only compatible revenue. | An open question for counsel. | A four-step inference presented as structural fact |
| 2026-10-07 | Labelling cannot be delegated or bought; budget 15–20 hours of Michael's time. | Ground truth must be independent of whoever drafts it. Michael decides the labelling policy; adjudication can be sourced. | The constraint is independence, not personal authorship |
| 2026-10-08 | Other tags "need something external," implying cost. | All needed tooling is free and open; the cost is labelling labour and revalidation time. | Conflated difficulty with money |
| 2026-10-08 | RFC-0004 said "five result states" above a six-row table. | Six: PENDING, FINDING, NO_FINDING, UNCERTAIN, UNSUPPORTED, UNAVAILABLE. | Counting error. Codex caught it |
| 2026-10-08 | `UNAVAILABLE` means "no check occurred". | `UNAVAILABLE` means no valid evaluation could be obtained; a partial internal step may have run. | The original wording is false in the partial-failure case — redaction succeeds, evaluator times out |
| 2026-10-08 | `BT`'s indicators (near-duplicate construction, templated variation, timing regularity) are positive evidence of automation. | Candidate indicators requiring validation. No threshold may be proposed until a corpus shows they separate automation from ordinary human repetition. | Humans produce all three constantly: form letters, boilerplate, support scripts, required formats, second-language writing from a learned pattern. If the corpus says they don't separate, `BT` does not ship |
| 2026-10-08 | `SC`'s two-family co-occurrence rule is a design. | A hypothesis with no measurement. Co-occurring weak indicators are not independent corroboration — in scam text they likely share a common cause. | Stated as design, which implied it was sound |
| 2026-10-08 | Added `UC`/`SC`/`BT` to `spec/taxonomy.md` and deprecated `PS`/`UNK` there. | Reverted. The taxonomy shows what is adopted; proposals live in RFC-0004 until Michael accepts D17/D18/D19. | I pre-empted acceptance in the same session that established R22 forbidding exactly that |
| 2026-10-08 | Rewrote `eval/gates.yaml` to a v2 structure. | v1 compatibility block restored alongside v2, plus `eval/gates.schema.json` as the contract. | I changed a config format without checking its consumer. `eval/harness.py` reads `gates["gates"][tag]` and `gates["abstention"]["min_rate"]`; both were gone. Same failure pattern as the hash and the denominator: changed a thing without reading what depended on it |

- **2026-10-08 — Dedicated research hosting:** owner prefers open-source software and an independent environment with no co-mingling. Supersedes the existing THT server reuse decision. AI Trust ID requires separate server/VM, database, credentials and backups; portable deployment and tested recovery. Provider and budget remain unselected; nothing provisioned or purchased.

- **2026-10-08 — Hosting research recommendation (proposed):** Debian 13, PostgreSQL 18, separate FastAPI intake, Caddy/private administration and pgBackRest >=2.59.3 with independent backups. Live OVHcloud US East VPS-2 no-commitment quote verified at $10/month before tax. Host choice/purchase, contribution policy and retention remain unaccepted; research is not deployment. Details: docs/open-source-hosting-plan.md.

- **2026-10-08 — Host purchased by owner:** supersedes the unselected-host status above. Owner paid for the recommended OVHcloud US East VPS-2 in Chrome. Provider payment validated; Debian 13 host Active with 4 vCores, 8 GB RAM and 75 GB disk. SSH port responds; authenticated login and PostgreSQL/application setup remain incomplete. Provider backup page shows a daily schedule with no restore points; independent recovery remains open. Collection and retention decisions remain unresolved. No additional purchase authorized.

- **2026-10-08 — Private host foundation executed:** owner installed the dedicated public key. Fresh key-only SSH, PostgreSQL 18.6 socket-only access, separate peer roles, firewall and 46 runtime checks pass after reboot into the patched kernel. Application authorization, independent recovery and public intake remain incomplete; this supersedes the initial-access status above. Evidence: runs/2026-10-08-private-host-foundation.json.

- **2026-10-08 — Public communication direction accepted:** owner wants live community messages visible to everyone and transparent company communication. F-136/F-137 now track safe public publication, moderation records and appeals. Private security reports, credentials and research contributions remain protected; public posting is not automatic training consent. Implementation remains pending; docs/public-community-and-private-data.md defines the boundary.

- **2026-10-08 — Independent backup option requested:** owner asked for an option to review. A separate Linux repository VPS and a lower-cost proprietary object-storage alternative are detailed in docs/backup-option-review.md. No backup destination selected, additional purchase made or restore claimed.

- **2026-10-08 — Independent backup host purchased:** owner reports payment completed for the available DigitalOcean Debian 13, 1 vCPU/2 GB/70 GB NYC3 plan at $16/month before tax. Provider reports Active. Provider console proves an existing local key was installed instead of the dedicated backup key; key-name selection was insufficient evidence. Owner console handoff is required to install the dedicated key. No password authentication enabled, server rebuilt or backup configured. Supersedes purchase-pending status; runs/2026-10-08-backup-provisioning-check.json records the checks.

- **2026-10-08 — Independent backup pilot executed:** owner installed the dedicated key; fresh login and provider-console host identity match. Backup-host root/password SSH disabled, distinct restricted service keys exchanged, encrypted repository/WAL and schedules enabled. Twenty host checks and both offline named synthetic restores pass after reboot. Protected copies resist repository-account deletion; corruption, wrong key, outage and local monitor faults are detected. Protected generations have no automatic expiry pending retention acceptance. Owner offline custody, provider MFA, external notifications and complete replacement-host recovery remain open; no real collection enabled. Evidence: runs/2026-10-08-independent-backup-result.json. This supersedes the initial access/purchase status, without claiming a released tag or deployed public site.

- **2026-10-08 — Private operational notifications approved and executed:** owner approved self-hosted ntfy at notify.aitrustid.com because the backup provider blocks SMTP. Verified HTTPS, default-deny ACLs, distinct publish-only host identities and a read-only owner identity are deployed; both host heartbeats observed and five-minute sender timers enabled. No attachments, signup or upstream forwarding. iCloud accepted a primary email test; its separate timer remains disabled pending owner inbox receipt. No subscription purchase. Recovery cipher and encoded administrator key saved in Apple Passwords; masked saved entries verified, retrieval and independent offline copy still open. Provider MFA configuration verified. This supersedes MFA/external-alert configuration pending in the backup pilot; it does not complete real-data, release, or full-host recovery gates.

- **2026-10-08 — Owned-domain development catalogue published:** owner requested closing launch gaps. Existing limited Pages grant created/deployed the allowlisted static build; registrar parking replaced with proxied apex/www aliases. Both domains active with exact reviewed HTML hashes. Automatic provider beacon injection failed the first own-domain verification; no-transform preserves the reviewed response and subsequent external checks pass. No broadened credential grant, public evaluator, research upload or tag release. Owner inbox screenshot resolves primary delivery confirmation; independent email timer enabled. Source push, independent accuracy, community/intake and full recovery remain separate gates. Evidence: runs/2026-10-08-site-live-result.json.

- **2026-10-08 — Open personal validation path authorized:** owner requests the best viable product, a working validated tag, and a downloadable public repository. Added a manual checker through the existing local endpoint; no new public evaluator, remote content upload or lowered accuracy gate. Enable public issues/discussions and private vulnerability reporting. Initial public source history will contain only the reviewed current snapshot with a GitHub no-reply author address; retain prior local audit history in a private local ref, never mirror-push it. Next PII tag receives a bounded procedural contract and invalid-redactor enforcement, without claiming recognizer accuracy. Independent review remains required before release.

- **2026-10-08 — Scope execution planning expanded at owner request:** 39 packages, 117 subtasks and all 202 preserved records now have an execution crosswalk. Removed 81 generic PS dependencies. Scope coverage is distinct from runtime/release evidence; UC/SC/BT registration, pricing, collection/retention and institutional decisions remain unaccepted unless separately recorded. `docs/scope-delivery.md` is the current execution plan; older `PLAN.md` is historical.

## 2026-10-09 — Completion ledger and brand credit

Owner requested per-item timestamped milestone completion, execution attribution and fixes; 100% requires functioning full acceptance. Retain all source IDs and completed history. Claude research code is reviewed as components, not a shipped validator or adopted tag policy. Owner superseded repeated personal publisher credits: current general site credit is AI Trust ID; product owner display is Michael. Real operator remains in Terms and archived versions remain intact. No GitHub account rename, organization creation, new endpoint, runtime tag registration or collection activation was performed.
