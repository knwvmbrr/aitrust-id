# Independent hosting and research data plan

Research date: 2026-10-08. Status: owner purchased the recommended VPS; payment
validated and Debian 13 host Active. Key-only SSH, PostgreSQL 18.6 and the
socket-only database foundation now pass 46 checks after a patched-kernel reboot.
The independent DigitalOcean Debian backup host is now configured and verified:
encrypted pgBackRest/WAL, protected generations, scheduled jobs and two offline
synthetic restores after reboot. Application deployment, owner offline key
custody, MFA, external alerts and full replacement-host recovery remain incomplete.
Scope: N-011; no tag capabilities are added or removed.

Provider backup page shows a daily schedule with no restore points yet. Its
dashboard summary says Disabled; rely on executed backup/restore evidence, not
either label. Renewal shows Manual renewal and an invalid next-payment date;
recheck the billing schedule. Sensitive inventory and first-login instructions
are stored outside this public repository. Current evidence:
[host verification](../runs/2026-10-08-private-host-checks.json),
[operations](private-host-operations.md), [backup execution](backup-implementation.md),
[executed result](../runs/2026-10-08-independent-backup-result.json).

## Recommendation

Use a separate OVHcloud US East VPS running Debian 13, PostgreSQL 18, Caddy,
the project's Python/FastAPI stack, and pgBackRest 2.59.3 or newer. Keep tag
evaluation on the user's local pipeline. Connect optional research submission
through a separate service, never through the evaluator's critical path.

The live configurator showed VPS-2 2027 in Vint Hill, Virginia, available now:
4 vCores, 8 GB RAM, 75 GB NVMe, Debian 13, no commitment, $10/month before tax,
with standard daily provider backup included. This is a public quote, not an order
or a measured performance result. Recheck price, renewal, available capacity and
terms before purchasing. The advertised $8.50/month selects a 12-month commitment;
it is not the monthly price used in this recommendation.

Evidence: [public configurator](https://us.ovhcloud.com/vps/configurator/),
[quote screenshot](../runs/hosting-research/ovh-debian-monthly-quote.png).

Store encrypted PostgreSQL backups with a different provider and a separate
account. Backblaze B2 is the inexpensive first candidate for S3-compatible storage.
It is a proprietary storage service, not an open-source database dependency.
If the requirement extends to operating the backup storage software ourselves,
use a dedicated Linux backup VM at another provider instead; pgBackRest supports
remote repositories over SSH/TLS. That adds another server to maintain and pay for.

The owner's direct SQL access, exports and recovery do not depend on an application
vendor. No THT workload, user, credential, database or backup namespace is reused.
A project-exclusive VM does not imply exclusive physical hardware. Providers,
their networks and their control panels remain external dependencies.

## Why this stack fits

| Component | Baseline job | Outcome | Boundary |
|---|---|---|---|
| Debian 13 | Maintain a supported Linux host | Predictable service and patch operation | Separate AI Trust ID host; staging uses synthetic data |
| PostgreSQL 18 | Store records, versions, consent and independent labels | Owner can query, export and restore the complete database | Private socket/loopback access; no public database port |
| FastAPI/Python | Validate and authorize submissions and review operations | Durable receipt only after a successful database transaction | Separate remote service; existing loopback gateway is not exposed |
| Caddy | Terminate HTTPS and proxy allowed application traffic | Encrypted public access with managed certificate renewal | Private admin interface; application limits still required |
| systemd | Supervise dedicated unprivileged services | Explicit startup, restart, resource limits and logs | Restricted users and file access; no remote-input shell execution |
| WireGuard + SSH | Give owner/admins private operational access | SQL access and maintenance without a public admin dashboard | Per-device keys, revocation and tested rescue access |
| pgBackRest | Produce encrypted database-consistent backups and archive WAL | Restore a database or recover to a selected point | Separate repository credentials, keys and restore evidence |
| Separate backup destination | Survive primary host/provider loss | Recovery remains possible after losing the main account | Backup administration and recovery secrets kept separately |

Debian 13 is the current stable distribution. PostgreSQL 18 is a supported stable
major, with support listed through November 2030; its official APT repository
supports Debian 13. Pin the major and install the current security-maintained
minor at implementation time. PostgreSQL uses the PostgreSQL open-source license.
[Debian releases](https://www.debian.org/releases/),
[PostgreSQL support](https://www.postgresql.org/support/versioning/),
[Debian packages](https://www.postgresql.org/download/linux/debian/),
[PostgreSQL license](https://www.postgresql.org/about/licence/).

FastAPI and pgBackRest are MIT-licensed; Caddy is Apache-2.0. These are component
checks, not a complete dependency/license audit. pgBackRest supports PostgreSQL 18,
encrypted repositories, WAL archiving and restore. Caddy supports automatic HTTPS.
[FastAPI license](https://github.com/fastapi/fastapi/blob/master/LICENSE),
[pgBackRest license](https://github.com/pgbackrest/pgbackrest/blob/main/LICENSE),
[pgBackRest releases](https://pgbackrest.org/release.html),
[pgBackRest guide](https://pgbackrest.org/user-guide.html),
[Caddy source](https://github.com/caddyserver/caddy),
[Caddy HTTPS](https://caddyserver.com/docs/automatic-https).

Native PostgreSQL and systemd are the first operational choice because the owner
already operates Linux and SQL. Use versioned application releases with locked
dependencies. OCI application images remain a portable alternative; existing local
Docker verification is preserved. Rootless Podman is viable but would introduce a
new network/runtime verification pass. Rootless mode alone does not establish
egress isolation. Kubernetes, a container management dashboard and a new platform
control plane are not required for this initial data service.
[Podman rootless operation](https://github.com/podman-container-tools/podman),
[Podman networking](https://docs.podman.io/en/stable/markdown/podman-network.1.html).

## Alternatives and current price evidence

| Route | Verified public evidence | Fit and limitation |
|---|---|---|
| OVHcloud US VPS-2 | Live monthly quote: $10; 4 vCores, 8 GB, 75 GB | Recommended pilot candidate; provider lists anti-DDoS and daily backup, neither proves application security or database recovery |
| DigitalOcean Basic | $24/month; 2 vCPUs, 4 GiB, 80 GiB | Straightforward alternative; same open-source stack, higher published base price for this size |
| Hetzner EU CX23 | Published $6.49 + $0.60 IPv4/month before tax; 2 vCPUs, 4 GB, 40 GB | Lower-cost EU candidate; public page showed unavailable and live console inventory was not verified |
| Oracle Always Free | Eligible resources can be free | Useful for disposable development/pilots; capacity and idle-instance reclamation make it a weaker primary-store choice |
| Self-hosted Supabase | Self-hosting is supported; infrastructure still paid | Valid route if its bundled auth/storage/realtime services are needed; self-hosting does not provide managed backups or remove operations work |
| Owned hardware/colocation | No quote obtained | Greater hardware control, but adds procurement, physical redundancy and remote recovery responsibilities |

Sources: [OVH VPS](https://us.ovhcloud.com/vps/),
[OVH billing](https://support.us.ovhcloud.com/hc/en-us/articles/360002306224-Overview-of-Billing-with-OVHcloud-US),
[DigitalOcean pricing](https://www.digitalocean.com/pricing/droplets),
[Hetzner current price adjustment](https://docs.hetzner.com/general/infrastructure-and-availability/price-adjustment/),
[Hetzner IPv4](https://docs.hetzner.com/cloud/servers/primary-ips/overview/),
[Hetzner plan page](https://www.hetzner.com/cloud/cost-optimized/),
[Oracle free-resource conditions](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm),
[Supabase self-hosting](https://supabase.com/docs/guides/self-hosting).

Backblaze publishes $6.95/TB/month, with the first 10 GB free. At 100 GB total
average backup storage, that implies roughly $0.63/month for the remaining 90 GB,
before billable transactions, transfer overages and tax. Retained full/incremental
backups, WAL and protected versions all count toward stored bytes. Allow a working
pilot budget of $15/month before tax for the recommended route; this is an estimate,
not a cap or a purchase authorization. Temporary staging/recovery machines and
future model-training compute are additional costs.
[Backblaze pricing](https://www.backblaze.com/cloud-storage/pricing).

## Three operational layers

### 1. Local tag operation

The current extension, loopback gateway, redactor and evaluator continue to issue
bounded local results. Research connectivity never changes tag claim boundaries,
allowlists or confidence gates. Existing result downloads remain available.
Remote contribution credentials must be distinct from the local gateway token.

Introduce an explicit contribution choice and a bounded outbox only after collection
policy acceptance. Retry with delay/jitter and an expiry; display queued, received,
failed and expired states truthfully. A central outage must not delay evaluation.
An expired unsent record must not be uploaded later without the accepted policy.

### 2. Remote intake and reviewed data

Receive only allowed versioned records; authenticate the submitter and authorize
each object. Reject unknown fields, oversized payloads and unsupported versions.
Separate submitted observations from server validation and independently reviewed
labels. A client-supplied hash or method identifier is a claim, not verified execution
provenance. Rate limits, quotas, idempotent per-submitter deduplication and transaction
boundaries prevent accidental retry duplication and limit abusive submissions.

Initial logical entities: submissions, method versions, tag findings, consent
events, review decisions, corrections/supersession, dataset manifests, deletion
tombstones and operational audit events. Use relational constraints for identity,
ownership and review status; bounded JSONB for versioned evidence fields. SQL and
JSONL/CSV exports are part of the delivery, not paid features.

Start with approved metadata only as the proposed conservative policy. Source text
and optional redacted examples require separate consent, permissions and retention
before activation. Hashes and timestamps can still identify activity. Define online
retention, backup expiry and deletion behavior together; no indefinite training
collection is enabled by choosing a host.

Use separate migration-owner, intake-writer, reviewer, analysis-reader and backup
roles. Application authorization is mandatory; RLS can add tenant isolation, but
table owners/superusers can bypass it. Test policies using the actual runtime role,
including connection-pool reuse between tenants. Keep reviewer/admin SQL access
behind private connectivity. Public clients never receive database credentials.
[PostgreSQL row security](https://www.postgresql.org/docs/18/ddl-rowsecurity.html).

### 3. Recovery and analysis

WAL archiving plus base backups enables point-in-time recovery. Archive to the
separate destination; supplement it with scheduled full/differential backups and
verified logical exports for long-term migration. A physical restore must use a
compatible PostgreSQL major; major upgrades need a separate tested migration.
[PostgreSQL recovery](https://www.postgresql.org/docs/18/continuous-archiving.html).

Run analysis against bounded read-only queries or extracted datasets, with separate
resource limits. Detector predictions do not become labels automatically. Freeze
holdout data before evaluation, record adjudicator provenance, and prevent suspect
or adversarial submissions from contaminating accuracy claims. Heavy training jobs
must not run on the ingestion/database VM.

## Security and disruption risks to resolve before collection

| Risk | Control to implement | Evidence required |
|---|---|---|
| One VM is a single failure point | Independent backups, reproducible rebuild, bounded client queue | Recover on a fresh provider host; local tags still work during outage |
| Root/account compromise | Least privilege, provider MFA, separate recovery account and restricted backup authority | Compromised intake credential cannot read/delete protected recovery copies |
| Sensitive or identifying data | Field allowlist, consent, separate text handling, retention/deletion | Canary private text absent from requests/logs when metadata-only mode is selected |
| Poisoned labels/corpus | Separate predictions and review; provenance and holdout separation | Submitter cannot grant reviewed status or alter frozen manifests |
| Public API abuse | Auth, object permissions, size/rate/concurrency limits | Unauthorized, cross-owner, injection and exhaustion checks fail safely |
| Disk or WAL exhaustion | Capacity alerts and backpressure | Archive outage/disk-fill test preserves existing records and returns honest failure |
| Deployment error | Separate staging, compatible migrations, recorded rollback | Previous application release works with the migrated schema or explicit restore plan |
| Provider/DNS disruption | Exportable deploy/config, off-provider backup, DNS recovery procedure | Alternate host serves the recovered data; keys and access remain available |

Keep PostgreSQL and admin surfaces private. Restrict public traffic to required
HTTPS/certificate traffic; allow maintenance only through accepted private/admin
access, with a tested rescue procedure. Trust forwarded headers only from the
configured proxy. Parameterize SQL; reject client-supplied reviewed/owner fields.
Disable debug and public administrative documentation. Audit access and critical
changes without logging tokens, response content or sensitive SQL parameters.

Do not describe backups as ransomware-resistant solely because they are encrypted.
The primary process must not possess authority to purge protected recovery copies.
Evaluate versioning/object retention against pgBackRest expiration and the accepted
privacy policy in staging. Backblaze Object Lock cannot be disabled once enabled
on a bucket; compliance-mode retention cannot be removed. Do not activate it
without a concrete retention/deletion decision and tested repository operation.
[Object Lock behavior](https://www.backblaze.com/docs/cloud-storage-object-lock).

**Current package condition:** pgBackRest disclosed a weak encryption subkey/salt
failure on October 4, 2026. Require 2.59.3 or later, confirm operating-system random
access works, and create the new repository/stanza with the patched version.
Upgrading alone would not replace a pre-existing weak stanza subkey. No such
repository has been provisioned in this project.
[Security disclosure and remediation](https://pgbackrest.org/news.html).

An open-source license does not establish safety. Before collection, record package
sources/versions, scan dependencies, verify OS/application hardening and execute the
failure tests. Full-disk encryption can complicate remote reboot recovery and does
not stop a running compromised process; choose and test the live-data encryption
method rather than claiming provider disk encryption means the provider cannot
access live data.

## Measurable pilot targets

These are proposed acceptance targets, not measured guarantees or service promises:

- Recoverable-data lag at most 15 minutes, monitored from successfully archived WAL.
- Restore service on a fresh host within 4 hours, including secrets and access checks.
- External failure detection within 5 minutes; route alerts to an accepted destination.
- Warn at 70% disk usage; critical at 85%; test controlled rejection before exhaustion.
- No central outage adds a network dependency to local tag evaluation.
- Acknowledged submission is durable; duplicate retry does not create another record.
- Resource/load budget declared and measured before public onboarding.

Start with weekly full and daily differential backups plus WAL archiving; measure
backup space and timings before selecting retention. Check archive/backup health
daily, run restoration monthly and after material backup/version changes. Hold a
deletion ledger separately and reapply deletions before exposing a restored copy.
RPO/RTO targets hold only while archives, keys and recovery procedures are available.
Meeting an availability target for the research service would require further
redundancy; this one-VM pilot is recoverable, not high availability. Add a separately
hosted standby/API node only after a service-level requirement justifies its cost;
replication does not replace backups or prevent malicious deletion propagation.

## Execution order, outcomes and owners

| Increment | Concrete outcome and exit gate | Owner |
|---|---|---|
| H0 — choice | Approve exact host/region/monthly total and backup destination; settle contribution/retention policy before real data | Product owner; Codex prepares reviewable configuration |
| H1 — data contract | Strict record schema, consent/review roles, migrations and bounded outbox pass synthetic PostgreSQL tests | Codex implements; Claude/reviewers review claim/data boundaries |
| H2 — staging | Reproducible Debian/PostgreSQL/API deployment, private access, health/build/verify/deploy checks and rollback pass | Codex; owner holds hosting account and recovery keys |
| H3 — recovery | Encrypted backup, WAL, restore and deletion replay verified on a fresh machine; record timings/counts/hashes | Codex executes; owner witnesses access/recovery |
| H4 — abuse/outage | Cross-owner access, malformed input, retries, archive outage and disk-fill simulations pass; local tagging unaffected | Codex plus independent security reviewer |
| H5 — controlled pilot | Explicit opt-in contribution reaches durable storage; SQL/export/deletion work; no unreviewed data becomes ground truth | Owner accepts policy; Codex connects and verifies |
| H6 — expansion | Additional tags and analysis jobs use versioned records and independent evidence, with measured capacity and retention | Codex implements; independent adjudicators own labels |

No cloud project, server, account or paid service was created during this research.
No endpoint URL is invented here; naming/access must be accepted before remote
publication. Hosting is independent of whether PS meets its release gate.

Repo evidence: `extension/src/content/badge.js` exports local unreviewed metadata;
`deploy/docker-compose.yml` preserves loopback-only evaluation; the optional
`services/registry/app.py` is a SQLite display prototype with no implemented
retention deletion path or contribution intake. Its displayed 30-day default is
not enforcement. It must not be used as the production training store.

This plan preserves the 198-record master scope. It does not declare the database,
security boundaries, backup compatibility or recovery targets implemented.
