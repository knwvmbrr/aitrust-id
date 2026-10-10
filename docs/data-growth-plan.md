# Brief tag explanations and data growth — 2026-10-08

User direction: ordinary users see a short explanation; the website catalogue
holds the full tag specification and testing details. Organized results should
support an in-house training, pattern and anomaly database.

## Implementation boundary

The extension keeps tiny code-only controls. Opening one shows its bounded meaning
and next action in a few sentences. The technical record remains available as a
user-initiated JSON download, without embedding source response text. The website
continues to expose full method, testing, evidence and limitation descriptions.
Do not link to a public catalogue until its deployment is verified.

First implement and verify the concise explanation and structured local export.
No endpoint is introduced and no automatic transmission is enabled in this pass.
The dedicated database host is selected and its private foundation is deployed;
application authorization, collection choice and retention remain unresolved.
The owner requires remote hosting, low cost, open-source software,
control over data and a reviewed security boundary. Local-only production storage
is excluded; development verification may use isolated synthetic fixtures.

## Organized record contract

A versioned export holds record ID, selected code, result state, artifact binding,
method/source version, selected findings, supported signal identifiers/scores/spans,
redaction category/count metadata, and abstentions. Export time is separate from
capture time. Scores are heuristic; detector output is a prediction, not a training
label. Source text and arbitrary upstream detail are excluded. Local exports are
not anonymized merely because they omit text; hashes and times can be identifying.

## Database architecture to agree before implementation

| Component | Job | Required boundary |
|---|---|---|
| Submission/outbox | Explicitly approved records enter a bounded retry queue | Separate from local evaluation; no reporting outage blocks tags |
| Intake/store | Validate version, deduplicate, authenticate and persist records | Destination and endpoint require acceptance; encrypted transport for remote intake |
| Reviewed examples | Keep approved redacted examples and consent provenance | Text is a separate optional object; redaction is not a complete privacy guarantee |
| Labels/corrections | Independent label, reviewer, disagreement and supersession | Never silently replace a prediction with a verified label |
| Analysis | Track versioned errors and unusual signal/category changes | Alerts are hypotheses, not accusations or new origin verdicts |
| Dataset release | Freeze dataset manifests and split development/holdout data | No holdout tuning, provenance records, sampling and coverage accepted first |
| Retention/deletion | Expire records, revoke examples and remove derived dataset inclusion | Retention period and backup/deletion process must be accepted |

The owner's latest decision supersedes reuse of the existing THT server: AI Trust
ID requires a separate remotely hosted environment, open-source application and
database software, owner-controlled access and provider-portable recovery. THT
workloads, databases, credentials and backups must not share the AI Trust ID
environment. The owner purchased the recommended OVHcloud US East VPS; the provider
reports Debian 13 Active. Key-only access and PostgreSQL 18.6 with socket-only
connections are verified after reboot. No research intake is connected.

Use a separate AI Trust ID server/VM, database, application roles, secrets and
backup namespace. Do not expose PostgreSQL directly to the public internet. Use
private application access and separate migration-owner and runtime roles. Verify
encrypted transport where traffic crosses hosts, backup encryption/restoration,
updates and capacity. Collection and retention remain unresolved; forwarding is
disabled. A dedicated VM isolates the project logically, but does not imply
exclusive physical hardware at a hosting provider.

Shared storage requires roles for submitters, reviewers and administrators,
audit events, limits and authenticated access. Plain local SQLite would not by
itself establish encrypted storage or a multi-user team service.

## Scope change and owners

Optional, specifically consented private research contributions are separate from
mandatory central storage or automatic telemetry. Preserve X-03, X-06 and F-086;
do not interpret the database direction as permission to capture all users.
The owner accepted a metadata-only first pilot on 2026-10-10: tag result, method
version, failure category and structured feedback. Examples require a separate
preview, redaction review and permission. Retention and intake remain unselected. Local evaluation remains useful without
submission. Individual users must control contribution of their own content.
No paid gate is added to tag explanations or evidence.

Product owner: destination, permitted collection, retention and release acceptance.
Codex: record format, concise UI, storage implementation and executed checks.
Claude/reviewers: claim boundaries, collection review and independent labeling.
Existing scope is retained; the database direction is recorded here while its
collection boundary is being resolved.

## Acceptance

Brief explanation does not show hashes, scores or offsets. Code-only controls,
multi-tag wrapping, keyboard dismissal, stale-result handling and mobile layout
still pass. Exported records bind to the selected tag, contain reproducibility
metadata and exclude response text and arbitrary upstream details. Database work
must later demonstrate authentication, duplicate handling, queue limits,
consent/revocation, deletion, retry isolation and independently reviewed labels.

## Hosting decision update

Dedicated AI Trust ID hosting replaces the previous THT-first recommendation.
The earlier existing-server choice and Oracle exploration remain decision history,
not permission to connect to or reuse THT. The owner subsequently completed the
separate OVHcloud VPS purchase; that does not authorize additional purchases.

The application stack must be open source and self-hosted, with PostgreSQL as the
portable database. Keep deployment definitions and migrations in the project and
avoid requiring a provider-specific database API. The hosting provider's control
plane may be proprietary; open-source software alone does not make a cloud
provider open source or remove reliance on its hardware/network. Select the host
against cost, region, isolation, support and recovery needs before provisioning.

Recovery requires encrypted PostgreSQL-consistent backups stored outside the
primary host, separate access credentials and a successful restoration on a fresh
machine. Provider snapshots supplement this and do not establish database recovery
by themselves. Storage for records and metadata needs no GPU; future model training
capacity must be sized separately. PostgreSQL and the independent encrypted
pgBackRest repository are installed. WAL archiving, backup and protected-copy
schedules run. Two named synthetic restores passed with networking disabled on
the backup host after reboot; the source's runtime permissions were preserved.
Owner-held offline key custody, MFA, retention, external alerts and complete
replacement-host recovery remain open. No collection or forwarding is enabled.
See [executed result](../runs/2026-10-08-independent-backup-result.json).

## Researched stack recommendation

See [independent hosting research and execution plan](open-source-hosting-plan.md).
The recommendation is a separate Debian 13/PostgreSQL 18 server, a bounded
FastAPI submission service, Caddy, private administration and patched pgBackRest
with backups at another provider. OVHcloud's live US East VPS-2 quote is $10/month
before tax without a long-term commitment (4 vCores, 8 GB RAM, 75 GB disk).
The owner purchased this host; its provider status is Active. The plan defines
outage isolation, direct SQL/export access, security risks and executed acceptance
checks required before real collection. Recovery targets remain unverified.

The owner also requires public live community communication. Public posts and
private research contributions have separate audiences and consent; publication
does not authorize training. See [communication and data boundaries](public-community-and-private-data.md).
No public forum, streaming route or automatic contribution is implemented.
