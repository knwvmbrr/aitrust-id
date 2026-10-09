# Private Linux/PostgreSQL host

Scope: N-011. This is the remote database foundation. It does not expose the local
evaluator or deploy a public submission endpoint. Collection stays disabled.

Executed 2026-10-08: PostgreSQL 18.6, pgBackRest 2.59.3 and kernel
6.12.111+deb13-amd64. Fresh key-only login and all 46 checks pass after reboot;
SSH, firewall, database, resolver and update timers remain active. Public TCP
5432 attempts time out. IPv6 administration could not be reached from this client,
so the IPv6 external negative probe does not independently prove its firewall.
The loaded firewall covers both address families; PostgreSQL has no TCP listener.
Evidence: [executed checks](../runs/2026-10-08-private-host-checks.json) and
[deployment record](../runs/2026-10-08-private-host-foundation.json).

## Architecture and deployment boundary

The approved host is a project-exclusive Debian 13 VPS. PostgreSQL 18 runs natively
under its distribution systemd unit. It accepts Unix-socket connections only;
there is no TCP database listener, public database password or remote SQL port.
SSH administrative access uses the owner's dedicated key. A dual-stack nftables
policy allows SSH, established traffic, loopback, DHCP renewal and ICMP; new web
traffic stays blocked until a named HTTPS service is separately implemented.
Outbound traffic is permitted for package maintenance. This host does not inherit
the local evaluator's no-egress property.

Signed PGDG packages supply the supported PostgreSQL major and patched pgBackRest.
The PGDG signing-key fingerprint is checked before the repository is used.
Native data checksums, fsync, full-page writes and synchronous commit are enabled.
OS/security and PGDG package update timers run without automatic reboot. Kernel
updates require a controlled reboot and a new verification run.

The migration owner cannot log in. Separate intake, review and analysis identities
use kernel-enforced peer authentication. Runtime roles cannot own the database,
create roles/databases, become the migration owner, or bypass row security. The
owner's default SQL role is read-only; sudo remains the administrative trust
boundary. There are no application data tables yet: migrations must explicitly
grant per-table rights and implement/test tenant authorization. Role separation
alone does not establish application security or tenant isolation.

## Execute and verify

Set `AITRUST_HOST` to the approved host and `AITRUST_SSH_KEY` to the dedicated key
outside the repository. The host identity must already be in the user's trusted
SSH known-hosts file. Deployment never bypasses host-key checking.

```sh
make host-build
make host-deploy
make host-verify
```

Bootstrap is for the dedicated host foundation, with no unrelated workloads.
It installs packages and replaces SSH, resolver, firewall and database access
configuration. Do not rerun it after adding new public services without reviewing
their required firewall/authentication rules. It does not automatically reboot,
configure DNS/TLS, create an intake service, or connect an off-provider repository.
Keep an existing authenticated session open until a fresh key-only login passes.

Verification connects as actual OS/runtime identities. It exercises permitted
inserts/reads and rejected reads, writes, deletes, admin impersonation and owner
escalation. Its randomly named synthetic schema is removed in a finally block.
Disabling the reader session's read-only default must still leave its writes
rejected by table permissions. These tests certify only the bounded foundation.
CI checks shell syntax, ShellCheck and Python compilation without a production key.
Live access, networking, service startup and persistence require host execution.

## Direct SQL access

After SSH login as `debian`:

```sh
psql -h /var/run/postgresql -U aitrust_reader -d aitrustid
```

For authorized migrations, use `sudo -u postgres psql -d aitrustid` and `SET ROLE
aitrust_owner` within the migration. Keep application runtime sessions separate.
Physical backup administration now uses separate restricted service keys and an
unprivileged account on the independent repository host. They permit only the
pgBackRest protocol, with pinned host identities and no shell/forwarding access.

## Recovery and remaining gates

Before the first configuration change, bootstrap saves the original SSH files
and any firewall configuration under `/var/lib/aitrust-id/host-rollback`, root-only.
If access fails, recover through the provider console/rescue path; validate SSH
syntax before reloading it. This saved configuration is not a database backup or
a verified rescue drill. Package upgrades require normal Debian recovery rather
than an automatic version downgrade.

Both hosts run pgBackRest 2.59.3. WAL archiving is on with a one-minute archive
timeout, to a fresh encrypted repository at a different provider. Weekly full and
daily differential backup jobs, 15-minute protected-generation jobs and local
age/capacity checks are enabled. The source host also checks archive failure,
database disk reserve and WAL growth every five minutes.

The backup host passed 20 checks after reboot. Two isolated named-target restores
passed with networking disabled: before and after deleting a synthetic row,
including checksums and runtime permission checks. Protected-copy access/deletion,
corruption, wrong-key, shell/forwarding and local monitoring failures were exercised.
This approximately 31 MB synthetic database does not establish production-scale
recovery time, retention, full replacement-host recovery or global security.
See [backup execution](backup-implementation.md) and
[result](../runs/2026-10-08-independent-backup-result.json).

Provider snapshots supplement this. Do not accept real data until all of these pass:

- Owner-held offline recovery keys, provider MFA and full replacement-host recovery.
- Collection/consent, source-text exclusions and coordinated retention/deletion.
- A named HTTPS intake service with auth, object permissions, quotas and retry tests.
- Staging with synthetic records, rollback and deployment compatibility checks.
- External availability/backup/disk alerts with a tested recipient and runbook.
- Private VPN administration and tested recovery access, if adopted before onboarding.
- Billing renewal/due-date verification so a missed payment cannot surprise operations.
