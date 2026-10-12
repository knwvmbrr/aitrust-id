# Check backup retention safely

This practice check uses **one invented record** in a disposable, encrypted
PostgreSQL backup. It never opens your application database or an existing backup.
It helps an operator see what withdrawal does—and what it cannot do by itself.

You need an existing ordinary Linux account, PostgreSQL 18 binaries at
`/usr/lib/postgresql/18/bin`, pgBackRest 2.59.3 or later at `/usr/bin/pgbackrest`,
Python 3, `unshare`, sudo access and at least 2 GB of free temporary disk space.
The tool refuses if its isolation checks fail. It installs nothing.

From a reviewed checkout on a dedicated development host, replace `debian` with
your existing ordinary account and run:

```sh
sudo unshare --net python3 -I scripts/verify-backup-retention.py --run-as debian
```

The initial root process verifies a separate, loopback-only network namespace.
It then permanently drops to the named account, removes supplementary groups,
sets no-new-privileges and checks that effective and permitted capabilities are
zero **before creating a database**. Running as root without that isolation, using
a root account, extra network interfaces or optimized Python checks is refused.

The process tries IPv4 and IPv6 external connections and requires their refusal.
Database connections use a private Unix socket; there is no TCP listener. Every
config-consuming pgBackRest command uses a new private configuration and an empty
private include directory. Child processes use a minimal environment. This is
process isolation, not a defense against a compromised host administrator.

## Read the result

The terminal prints a short summary. The detailed public-safe result goes to
`output/verification/backup-retention.json`. Exit 0 means the selected controls
and cleanup passed; exit 1 records a failed control; exit 2 means the execution
contract could not be met. Check the exit status as well as the JSON.

| Control | Expected result |
|---|---|
| Restore the first completed full backup | The invented row is present |
| Delete the current row; create and restore a second full backup | The row is absent from SQL |
| Restore the retained first backup before expiry | The deleted row is still recoverable |
| Restore with a different encryption key | Refused |
| Restore a copy with damaged backup metadata and its fallback copy | Refused |
| Expire the first full backup; select that exact label again | Refused |
| Restore the retained second backup after expiry | Successful; the row is absent from SQL |

The retention value is for this disposable test only. It does not adopt or change
a production retention policy. The test stops every owned cluster, removes its
temporary database directory and binds the result to five source-file hashes.
Cleanup failure prevents a passing result. Ctrl-C and other cancellations remain
cancellations after cleanup; an unresolved active cluster directory is kept intact. It never deletes another backup or
cluster to make a check pass.

Raw command logs may contain the temporary test encryption key. They are discarded
with the temporary directory by default. If troubleshooting needs them, add
`--private-logs /absolute/new/private/directory` outside the checkout. The destination
must be new and is guarded by the existing private-file workflow. Never publish
raw logs or use a production credential as a test key.

## What remains separate

SQL absence and refusal of an expired named backup do **not** prove erasure of
deleted database pages, physical disks, provider snapshots or every independent
copy. They do not prove recovery on a replacement host, a consenting research
pilot, accepted retention terms or legal compliance. N-011 and F-073 keep their
full acceptance requirements. No tag accuracy or production readiness follows
from this practice result.

See [the architecture](backup-retention-plan.md), [executed results](backup-retention-result.md),
and the pgBackRest [retention documentation](https://pgbackrest.org/user-guide.html#backup/retention)
and [expire command](https://pgbackrest.org/command.html#command-expire).
