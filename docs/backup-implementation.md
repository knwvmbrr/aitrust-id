# Independent backup implementation

The paid Debian 13 backup VPS is dedicated to AI Trust ID. The owner installed
the dedicated administrative public key; login and provider-console host identity
now match. This document is the implementation plan; runtime evidence determines
completion, rather than the existence of these files.

**Executed:** encrypted repository/WAL, scheduled backups, verified root-owned
protected generations, 20 host checks after reboot and two named-target restores
with networking disabled passed. Negative credential, corruption, wrong-key,
outage and monitoring checks passed. See
[result](../runs/2026-10-08-independent-backup-result.json). Owner offline key
custody, MFA, external notification delivery and production recovery remain open.

## Boundaries and risks

The primary PostgreSQL host uses its own restricted SSH key to archive WAL to an
unprivileged repository account. A separate repository key permits only the
pgBackRest remote protocol on the primary. Both directions pin host identities;
neither service key permits an interactive shell, forwarding or administration.
Both hosts must run the same patched pgBackRest version.

Backups use a fresh AES-256-CBC encrypted repository. The recovery secret is
stored in protected configuration and a private owner recovery bundle outside
the public checkout. An owner-held offline copy still needs acknowledgement.
Encryption does not protect against a malicious backup administrator or the
loss of every copy of the recovery key.

The repository account can write the working repository. Backup-host root keeps
separate copied generations under a root-only directory. Copies use independent
files from the working repository, never service-writable hard links. Unchanged
files can share inodes between root-only protected generations to bound storage.
Each staged generation undergoes pgBackRest repository verification before
publication. Publication is an atomic rename after copying;
incomplete staging copies do not replace a previous protected generation.
The primary's service credential cannot read, remove or overwrite those copies.
This is a tested filesystem permission boundary, not provider immutability.
Root compromise on the backup host can destroy both copies; independent account
MFA, owner recovery custody and future offline media remain required.

Working backup retention is two full sets, with weekly full and daily differential
backups for the synthetic pilot. Protected copies have no automatic expiry until
the owner approves a real-data retention policy. Free-space and backup-age checks
fail closed and produce local systemd failure state. External alert delivery is
separate and must be tested before real data is accepted.

The backup copy operation follows a completed backup under a host-local lock.
WAL may continue arriving while files are copied; the restore drill must demonstrate
a consistent full backup and the captured continuous WAL range. This does not
establish an atomic filesystem snapshot or promise that in-flight WAL is captured.

## Execution and acceptance

1. Patch the backup host, disable root/password SSH, apply the dual-stack firewall
   and verify a fresh login using a dedicated non-root administrator.
2. Install matching pgBackRest and PostgreSQL restore binaries without creating
   a database TCP listener. Exchange distinct restricted service keys and pin
   verified host public keys. Negative checks must reject shell/forwarding access.
3. Configure a new encrypted stanza; enable primary WAL archiving with bounded
   archive timeout. Execute checks on both hosts and one full backup.
4. Publish a protected copied generation. Test an attempted write and deletion
   as the repository account, and shell access using the primary service key.
5. Restore into a new isolated socket-only cluster on the backup host; never
   restore over the primary. Check synthetic record IDs, checksums and role
   permissions. Test point-in-time recovery before and after a synthetic change.
6. Enable backup schedules only after the initial drill. Record actual sizes,
   elapsed restore time, captured WAL and security checks. Exercise backup-age
   and free-space failure cases. Keep collection off until owner key custody,
   retention, notifications and application security gates are complete.

Build, deploy and verify commands belong in `deploy/backup/` and the Makefile.
Public run records exclude IP addresses, private keys and secret configuration;
private host identities and recovery material remain outside the repository.

## Operator commands

Set the explicitly approved host/key variables outside the checkout:
`AITRUST_BACKUP_HOST`, `AITRUST_BACKUP_KEY`, `AITRUST_PRIMARY_HOST`,
`AITRUST_PRIMARY_KEY`, `AITRUST_RECOVERY_DIR`. The recovery directory must be
owner-only and outside the public repository. Both host identities must already
be verified and pinned. No command bypasses strict checking.

```sh
make backup-build
make backup-deploy       # first baseline only; root SSH is disabled afterward
make backup-configure   # encrypted repository, restricted service keys and WAL
make backup-verify      # current effective policy, age and space
```

Run `/opt/aitrust-id/backup/schedule.sh` as backup-host root only after the initial
drill passes; it enables the three backup/protection/health timers. The configure
command installs the source monitor and enables its five-minute timer. Subsequent
baseline updates require a reviewed administrator/sudo deployment; do not reuse
the initial root-SSH bootstrap after enabling collection or additional services.

The restore command is an explicitly synthetic, fresh-directory drill:

```sh
sudo unshare --net python3 /opt/aitrust-id/backup/restore.py \
  --generation <recorded-protected-generation> --backup-label <recorded-set> \
  --target <recorded-synthetic-point> --schema <recorded-synthetic-schema> \
  --expected-rows 2
```

Use the private drill record for exact values and one row for its after-delete
target. Select the recorded backup and generation explicitly: a newer differential
backup can be too late for an older target. Source recovery parameter requirements
are stored separately; lowering them can abort PostgreSQL WAL recovery.
The restored cluster is stopped in a finally block. The private test directory
and encrypted corruption-test copies remain for evidence, with no real data.

Health failures are recorded locally through systemd/journald; this does not
notify a human outside either host. The independent repository's account is
still a single provider boundary, and root can destroy protected copies.

The [pgBackRest repository-host guide](https://pgbackrest.org/user-guide.html)
defines the remote-host and encryption contracts; the
[configuration reference](https://pgbackrest.org/configuration.html) defines the
supported options. Recovery targets remain proposed until measured.
