# AITrust-ID

AITrust-ID puts an identifiable tag beside content, with the evidence and limits of
what that tag establishes. Tags are the product. Detectors, capture, receipts,
verification, and organizational services support those tags.

The first development workflow checks text for two supported command-risk patterns:
a download piped into a shell, and recognized encoded-payload execution syntax. It
uses the existing `PS` code with a bounded command-risk explanation. `UC`, `SC`, and
`BT` remain proposals in RFC-0004; they have not replaced the adopted taxonomy.

**Development preview. No tag has passed release validation.**

The public tag catalogue is live at [aitrustid.com](https://aitrustid.com), with
Person/Enterprise views, compact tag tiles, a tag logo, Light/Dark/System appearance
and full tag-detail modals. Twenty [static tag reference pages](https://aitrustid.com/tags/)
and a [22-URL sitemap](https://aitrustid.com/sitemap.xml) expose the actual catalogue
to crawlers. Google indexing and Search Console ownership remain unverified.
HTTPS, public response hashes,
production security headers and all 20 modals pass external checks. Report and
community controls export drafts and link to public GitHub issues/discussions;
private vulnerabilities use a separate GitHub report channel. No research intake
is connected.
[Current launch gates and deployment evidence](docs/live-launch-status.md).

## Try the local checker

[Download the source](https://github.com/knwvmbrr/aitrust-id/archive/refs/heads/main.zip)
or clone this repository. Follow the [installation and verification guide](docs/open-validation-path.md).
PS checks bounded command-risk patterns in text you supply; it does not certify
the accuracy or safety of an AI answer. The complete personal workflow runs locally.

## What runs today

A Chrome extension captures individual assistant responses on the initial ChatGPT
adapter. It sends bounded text to an authenticated loopback gateway. A local
anonymizer redacts detected personal information before a local evaluator matches
supported patterns. The extension attaches the result to the same unchanged
response with small code-only tags in a wrapping row beneath the output. Each
distinct tag has its own control. Selecting a tag opens a short explanation in a
native dialog; Close or Escape returns focus to the tag. Recheck and a structured
record download are inside the dialog. The website holds full tag specifications
and testing information. No training database or automatic reporting is connected.

Default deployment starts three containers: gateway, anonymizer, evaluator. The
registry remains available under an optional Compose profile. The gateway has an
edge network for Docker Desktop loopback publishing; anonymizer and evaluator use
only the internal inspection network. Redaction can miss sensitive information.
The gateway receives the original text; the evaluator receives redactor output.
This is local processing, not a guarantee that every exfiltration path is blocked.

## Executed checks and remaining gates

| Capability | Evidence and limit |
|---|---|
| Runtime policy | Evaluator emits `PS` only; gateway suppresses unsupported detector candidates. `PII_REDACTED` comes from the redaction step |
| Command regression | TP=10, FP=0, FN=0, TN=14 on 24 development examples. Not an independent holdout; precision and recall lower bounds are about 0.722 and fail the candidate gates |
| Gateway | Executed authentication, origin rejection, upstream failure, redaction ordering, assertion schema, offsets, and oversized-body checks |
| Redaction | English assets provisioned during build; actual email redaction exercised with network creation blocked. Coverage is incomplete |
| Extension | Real unpacked extension exercised against real local services on a synthetic ChatGPT-origin page. Delayed/stale results, duplicate presentation, and injection checks pass on fixtures |
| Accessibility | Keyboard evidence checks and automated axe fixture checks pass. Human screen-reader evaluation is missing |
| Live ChatGPT | Installed Chrome extension verified on one existing Homebrew answer: finding, evidence and evaluator source hash. Broader live coverage remains open |
| Dependencies | Runtime packages and language-model artifact hash locked; package audit findings and exclusions recorded in `runs/`. This does not replace an application or OS-image security review |
| Semantic/provenance/media tags | Preserved in scope. Not implemented or validated by this workflow |

There are 101 passing Python checks, including live-review counterexamples, full-schema HTTP candidate-policy checks, and regression-manifest failures. All four active development fixture sets run through the dedicated CI regression job: 60 cases, zero classification errors locally. Historical corrected labels remain archived; these development cases are not independent accuracy evidence. Browser and container evidence is in `runs/`.
The public repository contains the runnable source. Engineering CI and the separate
statistical gate are configured. GitHub currently prevents every hosted job from
starting because of an account billing lock; the fresh public checkout passes
101 Python tests and 60 development regressions locally. Hosted execution remains
unverified. The gates are visible; a failing statistical gate prevents release approval,
not downloading or independently inspecting this development package. Statistical gates
currently fail and must continue to fail until their evidence exists. The harness
reports `evaluation_gate_pass`, not whole-product release approval.

A finding does not establish a scam, malicious intent, or authorship. No finding is
not a safety clearance. Heuristic scores are not measured probabilities. Pending,
finding, no finding, uncertain, unsupported, and unavailable have distinct meanings.

## Local setup

The remote Debian/PostgreSQL foundation also has an independent encrypted backup
pilot. Scheduled backups, protected recovery copies and two offline synthetic
restores passed after the backup host reboot. Provider MFA configuration and two
Apple Passwords recovery entries are verified. Private HTTPS operational alerts
are live, with both host heartbeats observed; iCloud accepted a primary test.
Inbox receipt and the primary email timer are now verified. Offline key custody,
desktop permission, full-host recovery,
real-data policies and application authorization remain incomplete.
No remote collection is enabled. See [backup operations](docs/backup-implementation.md)
and [operational alert evidence](docs/operational-alerts.md).

Use this checkout with Python 3.12, Node.js 22, and Docker. Follow
[development instructions](docs/development.md) to install verification tools.
Create a private environment file outside the repository containing a generated
`AITRUST_TOKEN` of at least 16 characters; the extension token must match it.

```sh
make deploy ENV_FILE=/absolute/path/to/private/runtime.env
make verify PYTHON=.venv/bin/python
make verify-runtime PYTHON=.venv/bin/python ENV_FILE=/absolute/path/to/private/runtime.env
make regressions PYTHON=.venv/bin/python
make gates PYTHON=.venv/bin/python
```

`deploy` starts the local containers. It does not publish a website. `gates` is
expected to fail on the current regression material. Load `extension/` unpacked in
a dedicated Chrome profile and configure its token through extension options.
Remove the token and unload the extension to remove access. Stop this project's
containers with `make down` and the same environment file.

## Scope and ownership

[Master scope](docs/master-scope.md) preserves 198 records across tag types, shared
capabilities, and personal/team/enterprise/proprietary applications. Preserving a
record does not mean it is implemented. The complete personal workflow remains
free; proposed organizational services must not weaken the personal standard.

[PS-01](docs/tags/PS-01.md) defines the first tag job, outcome, and acceptance packet.
[Independent review](docs/independent-review.md) defines the human evidence still
needed. Michael owns product acceptance; Claude owns claim and labeling review;
Codex owns implementation and executed engineering checks; independent human
reviewers provide ground truth and usability judgments.

## Layout and licensing

`spec/` contains the protocol and taxonomy; `rfcs/` proposals; `extension/` browser
code; `services/` local processing; `eval/` statistical checks; `tests/` engineering
checks; `docs/` scope and architecture; `runs/` executed evidence; `state.json` the
current status. Code is Apache-2.0 under `LICENSE`. The specification's stated
license is CC BY 4.0; see `CONTRIBUTING.md` for contribution requirements.

## Website preview

The website in `site/` follows the tag catalogue layout: AI TRUST ID, Person / Enterprise,
clickable tag details, and company/community information in the footer. It preserves 14 personal
tag records and six proposed organization offerings. Building Now and Coming Soon describe
progress; no catalogue entry claims a validated release. Reports, contributions and discussions
can be copied or downloaded as drafts. They are not delivered to a remote team.

With Node.js 22 or newer:

```sh
npm ci
npm ci --prefix site
npm run build:site
npm run dev:site
```

The local preview uses `http://127.0.0.1:5173/`. For built-site checks, serve `site/dist`
on loopback port 5174, then run `npm run verify:site`. The CI site job performs this sequence.
See [website architecture and publishing](docs/website.md) for the verified behavior, remaining
connections, and deployment steps. The reviewed catalogue is deployed on the owned
domain with verified security headers. The website does not run a detector or change
tag release gates.


The live-review gap pass adds bounded substitution detection, explicit disabled
candidate abstentions, and semantic assistant capture with response-identity race
protection. The current implementation evidence is in
`runs/2026-10-08-live-gap-implementation.json`. Historical measurements remain
regression evidence. The installed Chrome extension has now displayed a finding and source-bound
evidence on one live Homebrew answer. Broader live compatibility and independent
accuracy remain separate release requirements.

The proposed remote research store and its cost/security/recovery tradeoffs are
in [independent hosting research](docs/open-source-hosting-plan.md). The owner has
purchased the separate VPS. Key-only SSH and native PostgreSQL 18.6 are now
verified after reboot on the patched kernel; PostgreSQL accepts local sockets
only. All 46 [host checks](runs/2026-10-08-private-host-checks.json) pass.
Independent encrypted backup and synthetic restoration checks now pass. Public
intake, application authorization, full-host recovery and collection policy remain
incomplete. Local tags remain independent of research submissions.
See [host operations](docs/private-host-operations.md),
[public communication and protected data](docs/public-community-and-private-data.md)
and [backup options](docs/backup-option-review.md).
