# AITrust-ID

AITrust-ID puts an identifiable tag beside content, with the evidence and limits of
what that tag establishes. Tags are the product. Detectors, capture, receipts,
verification, and organizational services support those tags.

The first development workflow checks five bounded command-risk signal types:
downloads piped into a shell; supported command, process and backtick substitution;
and recognized encoded-code execution syntax. It
uses the existing `PS` code with a bounded command-risk explanation. `UC`, `SC`, and
`BT` remain proposals in RFC-0004; they have not replaced the adopted taxonomy.

**Development preview. No tag has passed release validation.**

The public tag catalogue is live at [aitrustid.com](https://aitrustid.com), with
Person/Enterprise views, compact tag tiles, a tag logo, Light/Dark/System appearance
and compact tag-detail modals with a plain-language purpose, limitation and visible
validation status. Each panel starts with an everyday example and a clear next action. Deeper methods, testing and feature details expand on request. Catalogue downloads identify themselves as descriptions; PS result exports remain a separate workflow. Enterprise plans describe their own scope without presenting reviewable designs as running services. Twenty [static tag reference pages](https://aitrustid.com/tags/)
and a [32-URL sitemap](https://aitrustid.com/sitemap.xml) expose the actual catalogue
to crawlers. Google indexing and Search Console ownership remain unverified.
HTTPS, public response hashes,
production security headers and all 20 modals pass external checks. Report and
community controls export drafts and link to public GitHub issues/discussions;
private vulnerabilities use a separate GitHub report channel. No research intake
is connected.
[Current launch gates and deployment evidence](docs/live-launch-status.md).
[Market landscape and first-tag delivery priorities](docs/competitive-landscape.md)
distinguish related products from full product equivalence; business viability and
comparative superiority are not established.

## Which personal tags can run today?

Of 14 personal catalogue entries, **PS runs on this website**, **PII_REDACTED runs only in the local service**, and **12 are planned or proposed**. A working catalogue panel is not a working detector. Each tag retains its own job and acceptance gate.

PS reports the matched command text, a plain explanation and a next step. A negative result means no supported command pattern was found; it does not validate the rest of the answer. Matched text stays on the page and is excluded from the default summary export.

## Try PS on a phone or computer

Open [PS](https://aitrustid.com/#person/PS) → **Check on this device**.
Copy an AI answer, paste, and check. No account, extension or Docker required.
The unchanged PS Python rules run in a self-hosted WebAssembly worker. Nothing
in the answer executes. This preview performs no redaction and uploads no text.
A finding identifies a supported command-risk pattern; no finding is not “safe.”
UNAVAILABLE means no valid result was obtained. Metadata export contains no answer
text, but its subject hash can correlate matching text; it is not anonymization.

Use **Save for offline use** while online, then add the site to your home screen.
The public app files are about 15 MB. Your browser can evict them. To update, save again online, close all AI Trust ID
tabs and reopen. Each cached release keeps its own method identity. Clear removes page input and terminates its worker. Remove
offline files unregisters this app’s worker/cache; close and reopen to finish.
Android Chromium and iPhone WebKit engine checks are automated emulations;
physical phones and human screen-reader testing remain open.

Two reviewers can use **Review test examples** on the same PS page. This is a
separate blind file form with no predictions. See [reviewer instructions](docs/PS-reviewer-start.md).
Native iPhone/Android sharing interfaces are tracked future work, not shipped apps.
[Architecture, privacy boundaries and acceptance](docs/handheld-delivery.md).

## Try the local checker

[Download the source](https://github.com/knwvmbrr/aitrust-id/archive/refs/heads/main.zip)
or clone this repository. Follow the [installation and verification guide](docs/open-validation-path.md).
PS checks bounded command-risk patterns in text you supply; it does not certify
the accuracy or safety of an AI answer. The complete personal workflow runs locally.

## Attach your own references

The [local corpus tool](docs/local-reference-corpus.md) imports plain-text or
Markdown documents into an owner-held, versioned file. It checks source integrity
and returns exact reference passages with Unicode spans, entirely offline.
Run `python3 scripts/corpus.py --help`. A literal match is not an NF/FI verdict;
those tags remain planned. No attached document is automatically uploaded.

## What runs today

After explicit opt-in in settings, the Chrome extension captures individual
assistant responses on the initial ChatGPT adapter. It starts paused. It sends bounded text to an authenticated loopback gateway. A local
anonymizer redacts detected personal information before a local evaluator matches
supported patterns. The extension attaches the result to the same unchanged
response with small code-only tags in a wrapping row beneath the output. Each
distinct tag has its own control. Selecting a tag opens a short explanation in a
native dialog; Close or Escape returns focus to the tag. Recheck and a structured
record download are inside the dialog. Matched positions are collapsed by default and refer to evaluated redacted text, which can differ from the visible answer. Exported fingerprints and positions may link or reveal information; review before sharing. The website holds full tag specifications
and testing information. No training database or automatic reporting is connected.

Default deployment starts three containers: gateway, anonymizer, evaluator. The
registry remains a deferred proposal. Its optional Compose profile is an explicit
refusal launcher: it exits before network or storage starts. The inactive prototype
is retained for inspection, with no implemented retention or intake.
The preserved prototype’s dependencies are not locked, so it is excluded from the selected preview's
verified dependency inventory. The gateway has an
edge network for Docker Desktop loopback publishing; anonymizer and evaluator use
only the internal inspection network. Redaction can miss sensitive information.
The gateway receives the original text; the evaluator receives redactor output.
This is local processing, not a guarantee that every exfiltration path is blocked.

## Executed checks and remaining gates

| Capability | Evidence and limit |
|---|---|
| Runtime policy | Evaluator emits `PS` only; gateway suppresses unsupported detector candidates. `PII_REDACTED` comes from the redaction step |
| Command regression | TP=31, FP=0, FN=0, TN=55 across 86 active development examples. Not an independent holdout; precision/recall lower bounds are about 0.890. Precision, holdout and calibration release gates remain unmet |
| Gateway | Executed authentication, origin rejection, upstream failure, redaction ordering, assertion schema, offsets, and oversized-body checks |
| Redaction | English assets provisioned during build; actual email redaction exercised with network creation blocked. Coverage is incomplete |
| Extension | Real unpacked extension exercised against real local services on a synthetic ChatGPT-origin page. Delayed/stale results, duplicate presentation, and injection checks pass on fixtures |
| Accessibility | Keyboard evidence checks and automated axe fixture checks pass. Human screen-reader evaluation is missing |
| Live ChatGPT | Installed Chrome extension verified on one existing Homebrew answer: finding, evidence and evaluator source hash. Broader live coverage remains open |
| Dependencies | Runtime packages and language-model artifact hash locked; package audit findings and exclusions recorded in `runs/`. This does not replace an application or OS-image security review |
| Semantic/provenance/media tags | Preserved in scope. Not implemented or validated by this workflow |

The observed Linux image inventories are public in `sbom/runtime/`. With the
hash-locked verification environment installed, run
`python3 scripts/verify-runtime-sbom-standard.py` to check their image/source
bindings, the pinned official SPDX 2.3.1 JSON schema and local consistency.
It works offline and recomputes package verification codes. This does not clear
licenses, authenticate inventoried source files or sign a release. See
[dependency evidence and remaining work](docs/spdx-inventory-validation.md).

The optional [development source provenance workflow](docs/source-provenance.md)
builds a committed-source snapshot with a file inventory. Its signing job is
restricted to protected main after the required engineering checks. Actual
signing evidence is required before claiming a particular download authenticated;
this does not release a tag or clear every dependency license.

The current complete local suite passed 1,179 Python checks; source-bound execution
is recorded in `runs/2026-10-10-target25-source-checks-repaired.json`. All five active development fixture
sets are selected by CI: 86 cases with no classification errors. These examples
are not independent accuracy evidence. Historical corrected labels remain archived.
The public repository contains runnable source, separate engineering checks and
statistical/accessibility release gates. Main requires eleven passing engineering checks from GitHub Actions, with
up-to-date branches, administrator enforcement and resolved review conversations.
Normal protected merges and a blocked failing control PR have been exercised;
see `docs/required-ci-result.md` and `docs/dependency-automation-result.md`.
CODEOWNERS is accepted and all ten actual Dependabot jobs have succeeded.
Dependency proposals remain subject to protected checks and reviewed locked inputs.
Release gates remain unmet and must continue to refuse release until their
independent evidence exists. A statistical refusal does not prevent downloading
or inspecting this development package; `evaluation_gate_pass` is not whole-product
release approval.

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
Checks start paused, including upgrades without saved consent. Explicitly enable
ChatGPT checks in settings; saving a token is not consent. Pause cancels pending
checks and removes tags. Reset removes the local token and consent, not the server
credential or a ChatGPT conversation.
Remove the token and unload the extension to remove access. Stop this project's
containers with `make down` and the same environment file.

## Scope and ownership

[Master scope](docs/master-scope.md) preserves 202 records across tag types, shared
capabilities, and personal/team/enterprise/proprietary applications. Preserving a
record does not mean it is implemented. The complete personal workflow remains
free; proposed organizational services must not weaken the personal standard.

[Scope delivery plan](docs/scope-delivery.md) expands the full scope into 39 work packages, 117 subtasks and an exhaustive [202-record task index](docs/scope-task-index.md), with independent tag gates and scoped prerequisites. Twelve additional tag planning contracts supplement PS and PII; proposals remain proposals.

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
progress; each tag must pass its own published validation gate before release. Each footer workflow has its own
purpose and deep link: report a reproducible issue, propose a contribution, read public
discussions, find owners and open needs, follow a tag, search all 202 scope records,
learn about the project, or inspect rights and data handling. Report/contribution drafts
can be downloaded; posting to GitHub is an explicit user action. Townhall shows a dated
public snapshot and links to live GitHub discussions. It does not simulate live in-site
posting or a self-hosted community. See [footer workflows](docs/footer-workflows.md).

[Public terms and policies](https://aitrustid.com/policies/) cover use, privacy, validation,
community, security, governance, contribution/accessibility, licenses and access.
Versioned no-script pages and text downloads describe actual operating behavior.
See [policy architecture](docs/public-policies.md) and
[product differentiation](docs/product-differentiation.md) for current versus planned scope.

With Node.js 22 or newer:

```sh
npm ci
npm ci --prefix site
npm run build:site
npm run dev:site
```

The local preview uses `http://127.0.0.1:5173/`. For built-site checks, serve `site/dist`
on loopback port 5174, then run `npm run verify:site`, `npm run verify:workflows` and `npm run verify:policies`. Run `npm run verify:a11y-probes` and
`npm run verify:site-a11y` for the actual-site keyboard, spacing and target checks.
`npm run verify:bundle` verifies a fresh device build against the committed engineering reference;
repeat `--python` arguments to its script to compare installed builder versions.
See the [accessibility test record](docs/accessibility-conformance-report.md) for
coverage and human-review limits. Hosted CI now starts; inspect the recorded
engineering results and separate release refusals rather than infer approval
from configured checks.
See [website architecture and publishing](docs/website.md) for the verified behavior, remaining
connections, and deployment steps. The reviewed catalogue is deployed on the owned
domain with verified security headers. The PS device checker runs the bounded method
in a self-hosted browser worker; pasted text is not uploaded. It does not change tag
release gates.


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


### First PS validation pass

The current context-v6 detector uses bounded command windows and indexed context
to avoid repeated rescanning, with a frozen Unicode-15 word class shared by server
and device. Exact context-v5 source is retained in eval/methods/. It also retains
the prior file-routing, literal-display and option-value corrections. Five development datasets now have
86 cases (TP 31, FP 0, FN 0, TN 55). These are development results, not an accuracy
certification. The 95% precision lower bound is 0.890 on this corpus; the candidate
0.93 threshold fails, and an independent holdout and calibration are missing.

The site includes use/setup instructions in every tag's modal and static reference.
PS is also available in a phone/device browser without an account, Docker or extension.
PII remains a local service preview; other tags clearly state availability. Local service
setup still requires technical Linux/macOS steps. Rebuild services after updating the source;
the CLI rejects an evaluator whose hash differs from this checkout. The latest
pass ran HTTP/unit checks, not a restarted full container pipeline.

Independent reviewers can use the blind packet tool described in
[Independent review](docs/independent-review.md). It never supplies predictions,
labels, or a claim that two files establish two independent reviewers.

The site credits AI Trust ID; Terms identify the current legal operator. Policies offer versioned plain-text
downloads. Checker summaries omit answer fingerprints/positions by default; detailed
reproduction records require an explicit choice. [Architecture and limits](docs/tag-system-upgrade.md).

[Timestamped scope completion ledger](docs/scope-progress.md) records per-item milestones, credits, evidence and next fixes; 100% requires full functioning acceptance. Research adjudication components are tested supplied-input mappings, not a released media validator.

Each tag modal now has its own performance panel. PS publishes development counts,
Wilson ranges and emulated mobile parity; other tags show what is unmeasured and
their next test. [Lean validation and data collection](docs/tag-performance-plan.md)
keeps user research consent separate from engineering test logs. To refresh evidence,
run regressions and the device suite, then `python scripts/build-tag-performance.py`
using the verification environment. `npm run build:site` rejects stale method-bound
reports; `npm run verify:performance` checks all panels, static pages and empty states.

## Change accountability

Every source, public copy, policy, scope or operational-evidence change needs a
new attributed record before build/deploy/commit. [Changelog](CHANGELOG.md),
[policy and commands](docs/changelog-policy.md) and [scope completion ledger](docs/scope-progress.md)
have separate jobs: history, enforcement, and acceptance.
Use `npm run changelog -- --help`, then `npm run verify:changelog`; contributor
is required. Engineering passes never substitute for independent tag validation.

### Provenance bridge research

`python3 scripts/demo-tag-bridge.py` demonstrates explicit subject-bound PA/FA
research candidates, missing evidence and conflicts. A valid credential alone
does not imply AI participation. This is synthetic input processing, not a live
tag or media verifier. See [the boundary contract](docs/adjudication-spec.md#experimental-provenance-to-tag-bridge--020-research).

## Current engineering increment — 2026-10-10

The current context-v6 pipeline passed 32 synthetic HTTP checks on the dedicated
Linux staging host, with source hashes, loopback binding, real redacted subject
identity, read-only non-root execution, zero Linux capabilities, bounded network
probes, stdout/stderr canaries and both dependency stop/recovery cycles. No local
Docker was started. [Executed service evidence](runs/2026-10-10-current-service-conformance.json)
is separate from independent tag accuracy and human/device acceptance.

[Maintainer lanes](MAINTAINERS.md), [subject contract](docs/subject-contract.md) and
[executable vocabulary](spec/vocabulary.json) provide reproducible shared contracts.
The [scope target](docs/scope-100-execution.md) preserves all 202 requirements;
completed jobs leave the open queue without disappearing from history.

## Versioned text identity and model loading

Current reference text primitives and runtime checks freeze NFC at Unicode 15.0.0,
so device and gateway hashes/positions do not depend on the host Unicode version.
[Migration and checks](docs/normalization-contract.md) preserve the old vectors;
[subject contracts](docs/subject-contract.md) distinguish text v2 from exact code
bytes v1. Run `python3 scripts/verify-normalization.py` and
`python3 scripts/verify-subjects.py` with Node available.

The redactor verifies every sealed English model asset before importing/loading
the model and refuses changed, missing or extra assets.
[Model integrity](docs/model-asset-integrity.md) describes the trusted-image
boundary and an executable positive/corruption test. These checks verify integrity
and interoperability, not independently measured tag accuracy.

### Reproduce published development measurements

Run `python scripts/verify-measurements.py` in a downloaded checkout. It recomputes
all five development datasets, category denominators/Wilson ranges, mathematical
sample-size minima and recorded browser-timing quantiles. Missing calibration is
explicitly unmeasured. Timing observations describe their recorded desktop host;
a fresh run can differ. No account, network call or service startup is required.

`python scripts/verify-dataset-provenance.py` checks all 101 versioned example
records (86 active, 15 historical). Add `--verify-history` in a full Git clone to
verify exact source commits; ZIP users can still verify every file and row hash.
Unknown original authorship remains unknown. These are development examples,
not a frozen independent accuracy study. See [measurement provenance](docs/measurement-provenance-plan.md).

## Future modality subject contracts

Image, audio, video and document have [bounded prepared-artifact reference contracts](docs/reserved-subject-contract.md), matching Python/Node primitives and runnable vectors. They establish exactly what is hashed, not file decoding or tag support. Run `python3 scripts/verify-reserved-subjects.py` or hash explicitly prepared JSON with `python3 scripts/hash-reserved-artifact.py`. The gateway still evaluates text only.

Source-bound engineering checks are available through `python3 scripts/revalidate.py CAPABILITY`. Website checks build fresh source on an owned temporary server. The shared `npm run verify:release-a11y` gate refuses absent real manual reviews; this is separate from statistical tag acceptance. See [executed controls](docs/reproducibility-controls-result.md). The [dated decision ledger](docs/decisions.json) records proposals without accepting them.

### Measured evidence resistance

Eight synthetic shell spelling trials bypass the bounded matcher with one or two
inserted characters, despite passing syntax-only and shlex token controls. No
command was executed. This is measured weakness, not a population evasion rate.
See [Evidence resistance](docs/evidence-resistance.md). New syntactic coverage
needs its own error checks; a source hash or heuristic cost class is not proof
of resistance. Large-input stress timings also publish exceedances of the
proposed 100 ms target rather than labeling that target met.

### Current personal workflow boundaries

The site deploy hook runs a [source-bound route guard](docs/current-route-boundaries.md).
`AITRUST_VERIFY_PYTHON=/path/to/your/verification-venv/bin/python npm run verify:boundaries`
checks the reviewed source, extension permissions, service endpoints and active
containers, plus matching executed browser/service evidence. The verification
environment needs the locked gateway and evaluation dependencies; build the site
first to prepare its checked device assets. The guard refuses changed or missing
evidence. It does not certify future code, third-party hosting or independent
accuracy, and it does not activate research collection or the registry proposal.

## Offline research components

The [editing observation tool](docs/composition-observations.md) runs as a standalone
HTML file, with opt-in measurement, timing suppression and local exports. The
[optional receipt tool](docs/offline-receipts.md) signs artifact-bound records and
verifies them without contacting us. Signature integrity is separate from truth,
authorship and unchecked revocation. These are functioning development components;
PA, FA, HP, MT and IV remain unavailable. `npm run verify:offline-components`
executes their controls; `npm run verify:composition` exercises both browser engines.
The new HP/MT/FI fixtures are synthetic development scenarios, not release evidence.

Owner-first practice: [Start with PS](https://aitrustid.com/reference/operate/).
Optional feedback previews and downloads a local metadata file; it sends nothing.
[Legal draft register](docs/legal/README.md) separates effective policies, proposed
corrections, restricted records and the remaining full-package review.

### Reproduce your local-service record

The extension offers a separate **Reproduce this check** download for new records.
It contains all findings and the selected pipeline identities, with no response
text. Follow the [local replay guide](docs/assertion-replay.md) to compare it against
your original text through your authenticated loopback service. The command reports
matching findings, changed input, differences or unavailable history. Matching is
repeatability, not an accuracy score. It does not send research data to us.

Optional development components: [independent file timestamps](docs/independent-timestamps.md) and a [verified no-account source download](docs/source-provenance.md). They do not issue authorship tags or establish tag accuracy.
