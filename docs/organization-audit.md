# Keep your organization's tag history

This optional, organization-operated tool keeps versioned tag metadata in your
PostgreSQL database. It supports corrections, reviews, private exports and
explicit retention. Personal checking and personal downloads need none of it.
It does not turn an unreviewed result into a validated tag or certify an author.
No hosted audit service, SSO, subscription or automatic collection is enabled.

## What you need

Use a dedicated Linux PostgreSQL 18 cluster, an empty application database, and
pgBackRest 2.59.3 or newer for encrypted backups. Keep it separate from unrelated
workloads. Use existing administrator and individual database accounts. This
installer creates two internal **NOLOGIN** implementation roles; it creates no
passwords and enrolls no user automatically. Follow your PostgreSQL deployment's
security updates and restrict its network/firewall and resource limits.

From the repository root, create a Python environment and install the existing
hash-pinned dependencies:

```sh
python3 -m venv .venv-audit
.venv-audit/bin/pip install --require-hashes -r eval/requirements.lock
```

Store credentials and exports **outside the checkout**, in a directory you own
with mode `0700`; files must be mode `0600`. Use an existing PostgreSQL service
file and, if needed, an existing private password file. Never put passwords in
command arguments or commit them. A service profile contains your database,
host/socket, port and existing username. For TCP the command forces
`sslmode=verify-full`; configure your trusted CA/root certificate. The executed
integration drill used private Unix sockets, not a live TCP/TLS connection.

Example command prefix (replace these private paths/profile names):

```sh
.venv-audit/bin/python scripts/organization-audit.py \
  --service audit-admin --service-file /private/audit/services.conf install
```

`install` refuses system databases and databases already containing application
objects. It creates the schema transactionally and revokes public schema creation.
Use a dedicated cluster: the physical backup workflow refuses clusters containing
another non-system application database. Production authentication must use
restricted peer/SCRAM/TLS rules. The test cluster's trust authentication is confined
to an isolated, temporary Unix socket and is **not a deployment configuration**.

## Choose the retention policy before adding records

There is no default policy. The administrator explicitly selects record days,
audit-marker days, and maximum backup age in hours. Supported ranges are 1–3,650
record days, up to 4,000 audit days, and 1–168 backup hours. Audit-marker retention
must cover record retention plus the backup window. A policy is immutable in this
version; changing it requires an explicit migration design, not an overwrite.

```sh
.venv-audit/bin/python scripts/organization-audit.py \
  --service audit-admin --service-file /private/audit/services.conf \
  tenant --tenant 11111111-1111-4111-8111-111111111111 \
  --record-days 30 --audit-days 40 --backup-hours 24
```

Those numbers are an **example selected by an operator**, not the company's
research policy or adoption of the historical hash-registry proposal. Record and
audit retention are counted from database receipt/event time. Hashes and positions
can link to sensitive information; metadata is not anonymous.

Enroll distinct existing login roles with only their needed capabilities:

```sh
.venv-audit/bin/python scripts/organization-audit.py \
  --service audit-admin --service-file /private/audit/services.conf \
  enroll --tenant 11111111-1111-4111-8111-111111111111 \
  --principal audit_writer --capability write
```

Repeat with separate reader (`read`), reviewer (`review`) and custodian (`delete`)
principals. More than one capability may be explicitly granted. Superuser,
bypass-RLS, role-creation, replication and database-creation accounts cannot be
enrolled. Other privileged/group memberships are refused. Each session maps to
one tenant; accepting a caller-supplied tenant string is not an access mechanism.
The database administrator remains trusted and can rewrite its own database.

## Preview, store and review one record

`prepare` accepts the current gateway 0.1.0 assertion, detailed device/CLI preview,
or detailed extension export. A minimal share summary lacks subject identity and
is refused. The projection retains source-file and subject digests, lengths,
method/processing digests, tag codes, reported scores/positions, result state and
redaction counts. It omits answer text, origin host, entity names, arbitrary notes,
credentials and attachments. It is **a metadata projection**, not the original
file. Keep the source privately if you need it later. Its digest binds bytes but
does not authenticate the producer, establish truth or reproduce missing inputs.

```sh
.venv-audit/bin/python scripts/organization-audit.py prepare \
  --input /private/audit/source.json --output /private/audit/preview
```

Inspect `preview/metadata.json`. Nothing has been sent or stored. Use the writer's
profile to run `policy` and inspect its returned policy and fingerprint. Then:

```sh
.venv-audit/bin/python scripts/organization-audit.py \
  --service audit-writer --service-file /private/audit/services.conf \
  append --input /private/audit/preview/metadata.json \
  --accept-policy POLICY_SHA256
```

An identical retry is idempotent. A conflicting overwrite is refused. To append a
correction, prepare another supported record for the same subject/normalization
and pass `--predecessor PREVIOUS_SOURCE_SHA256`. The old record stays unchanged;
an expired/deleted predecessor is unavailable, not reconstructed. Reviews use
the reviewer's profile and `review --id SOURCE_SHA256 --decision disagree
--reason false_alarm`. Choices are deliberately bounded; no original answer or
free-form accusation enters the database. A database principal is an accountable
handle, not proof of an independent human label.

## Export and verify

With the reader profile, run `export --output /private/audit/export-001`.
It writes `audit.json` and `checkpoint.json` privately. Keep the checkpoint in a
separate trusted location; a checkpoint stored alongside an attacker-modifiable
export is not an independent witness. Run offline:

```sh
.venv-audit/bin/python scripts/organization-audit.py verify \
  --input /private/audit/export-001/audit.json \
  --checkpoint /private/audit/export-001/checkpoint.json
```

Verification checks the ordered hash chain, retained metadata against its append
event, policy, and the exact snapshot when the checkpoint is supplied. It does
not authenticate source assertions or endorse the recorded detector conclusions.
An expired audit prefix is explicitly represented by a base sequence/hash.
Exports stop safely if the head changes, records expire mid-export, or the bound
is exceeded. This version supports a complete export of up to 10,000 records and
10,000 events within 20 MB; it refuses a truncated success. Larger deployments
need a partition/archive design before exceeding that supported export bound.

## Delete, expire and back up

The custodian uses `remove --id SOURCE_SHA256` to remove active metadata and
`expire` to sweep expired metadata and an eligible audit prefix. Expired records
are excluded from reads before the sweep. Schedule `expire` as the custodian and
monitor failures; no daemon is installed by this tool. Audit markers deliberately
retain digests, event choices, timestamps and database handles for the separately
selected audit period. Removal never claims to erase old backups, WAL, dead tuples,
filesystem/provider copies, or exported copies. Physical erasure is unverified.

Configure a **dedicated**, encrypted pgBackRest stanza/repository using its official
[configuration reference](https://pgbackrest.org/configuration.html). The supported
config contains exactly `[global]` and your stanza; no extra repositories,
remote-host overrides or included configuration files. Set `repo1-path`,
`repo1-cipher-type=aes-256-cbc`, a private cipher passphrase, and `log-level-file=off`
with console logging `warn`, `error` or `off`. The stanza supplies `pg1-path`,
`pg1-port` and `pg1-socket-path`. Provide a private empty include directory.
Initialize/check the stanza using pgBackRest. Retain the cipher key separately.

The administrator, on the database host over its private socket, runs:

```sh
.venv-audit/bin/python scripts/organization-audit.py \
  --service audit-admin --service-file /private/audit/services.conf \
  backup --config /private/audit/pgbackrest.conf \
  --empty-include-directory /private/audit/empty --stanza audit
```

A supported full backup contains a committed **locked** marker. Source access
resumes when the wrapper finishes; a crash can leave it locked and requires
administrator investigation. Backups are full only. After each successful backup,
sets older than the strictest selected tenant backup window are explicitly expired
and the inventory is checked. Run the backup command on a monitored schedule.
No promise is made that an unscheduled/offline operator has run expiry. pgBackRest
requires a newer full backup before an old full can expire; failure is reported,
not hidden. Its ordinary time retention alone is not a strict maximum age; see the
[official user guide](https://pgbackrest.org/user-guide.html).

## Restore without bringing deleted metadata back

1. Preserve the **latest** administrator-generated `recovery-controls --output
   /private/audit/recovery-N` outside the database and its backup repository.
   Update it after changes/deletion and before recovery. Keep the returned SHA-256
   pin separately in the recovery authority. Never substitute an old pin because
   the latest is missing. A timestamp cannot establish which authority is latest.
2. Restore an explicitly selected backup to a **new empty data directory** with
   pgBackRest `--type=immediate --target-action=promote --set=BACKUP_LABEL restore`.
   Start it with TCP disabled on a private Unix socket, using existing recovery
   admin access. Do not restore to “latest” WAL: a later source unlock could replay.
   Arbitrary SQL dumps, snapshots, latest-WAL restores and raw copies are outside
   this quarantine contract.
3. Tenant functions must refuse access while locked. Use the restored administrator
   profile with `reconcile --input /private/audit/recovery-N/recovery.json
   --expected-sha256 LATEST_TRUSTED_PIN --maximum-age-minutes 60`.
   Missing/wrong/too-old/future controls are refused. The tool cannot independently
   discover a newer off-host pin; supplying the current trusted pin is the
   operator's recovery duty. If it is unavailable, do not reopen the store.
4. Reconciliation removes records absent from the current authority or expired by
   server time before permitting tenant access. Newer missing records/history are
   explicitly unavailable; it does not invent them. Export headers retain the
   applied authority fingerprint and disclose the history gap. Review that output
   before exposing any network access.

This is a demonstrated database recovery workflow, not completion of a whole-host
replacement drill, actual organizational incident response or managed-service SLA.
The company research intake stays disabled. The operator guide, source, schema,
checks and synthetic execution evidence remain public; credentials, private
records and cipher keys do not belong in the repository.

## Run the development drill

On a disposable Linux machine with the documented PostgreSQL/pgBackRest/runtime
dependencies and an existing non-root account:

```sh
sudo unshare --net -- .venv-audit/bin/python scripts/verify-organization-audit.py \
  --run-as EXISTING_NON_ROOT_ACCOUNT \
  --output output/verification/organization-audit.json
```

The runner verifies the isolated namespace, permanently drops privilege, uses
invented input, starts only its own socket-only clusters, and stops/removes those
clusters and scratch files. It never changes production data or starts collection.
