# PostgreSQL account/history: architecture and isolated execution plan

Checked2026-11-24. No server mutation, dependency installation or application code written at this checkpoint. ROOT rejected the earlier bespoke ctypes/libpq and duplicate Starlette proposals before implementation. This plan uses maintained psycopg3 and the SAME reviewed account ASGI/security/domain implementation. ROOT owns existing account app/store/UI and optional state-filter extension; this worker owns new PostgreSQL-only paths.

## Actual prerequisites

Approved primary: private access metadata, StrictHostKeyChecking retained. Actual read-only observations: Debian Python3.13.5/x86_64, PostgreSQL18.7, installed libpq5 version19.0-2.pgdg13+1, Unix socket only,40connections, fsync/full_page_writes/synchronous_commit/data_checksums ON. Onlyaitrustid/postgres DBs, zero application tables. Free disk69769408512B and RAM7943460KiB. Existing deployed tool venv has Starlette1.10/Uvicorn0.54/Pydantic2.14 but no FastAPI/PGPython driver; these existing packages/services remain untouched.

ROOT explicitly authorizes a server-only isolated review venv containing the minimal existing gateway hashed-lock FastAPI/Uvicorn closure plus psycopg3.3.9 pure Python. No extras, binary psycopg, custom driver, new laptop dependency, Docker/model, public service, credential or payment. Fifteen exact wheel artifacts total3437525B; source archive URLs/checksums/sizes total5894716B are indexed, not downloaded. All14 non-driver selections match existing gateway-lock hashes; the new driver wheel219041B SHA d2d7d04a1ce6dab4f5b27316bea3b52585cafa2f2d631e5b09dd69823f5c26f6, source171122B SHA87c1d85c3e0e88e811d3c0b3808f947bd967c6faf34af6cd86fd021f77793d6c. PyPI declares LGPL-3.0-only; use plain psycopg with existing system libpq, retaining actual installed LICENSE/NOTICE/source information. Other declared licenses MIT/BSD/Apache/PSF remain exact package facts, not global clearance. Dependency JSON lists every complete URL/hash/size. Before code execution after ROOT approval, download only this closed wheel set on the server, verify every SHA/size and wheel packaged grant texts, then pip --no-index --no-deps --require-hashes into the new private venv. Preserve complete dependency notices and installation/source map. No mutation to the existing deployed tool venv, apt packages or main PostgreSQL.

## Exact software boundary

New PostgresAccountStore subclasses the existing AccountStore domain methods and overrides only the transaction/storage layer. A small closed dialect/row adapter converts the fixed inherited domain SQL qmark placeholders to psycopg %s parameter binding, without interpolating request values, and adapts real returned rows for integer/name indexing. No fabricated SQLite rows/API, status substitution or custom transport. Own schema uses real PostgreSQL types/constraints/sequences; domain behavior and account error codes remain identical. Read/write domain methods, scrypt, session tokens/rotation, CSRF/exact Origin/Host, account privacy, independent free checking and entitlement callbacks remain in their current shared reviewed code. New trusted CLI constructs this store and calls existing services.accounts.app.create_app; no duplicate ASGI/security implementation, route or UI.

Support inherited history_list(...,state=None) after ROOT's filter handoff: total_entries remains overall, matching_entries is the filtered count; cursor must be in the authenticated owner's filtered set and export remains complete/unfiltered. Until that shared handoff, retain current callable compatibility; no local editing of shared account files.

Each PG operation owns one connection and transaction. Connection uses explicit private Unix socket/database/runtime role, peer server identity, connection3s/statement3s/lock1s/idle-in-transaction5s limits; no request DSN, password, service file or environment fallback. Runtime actual session_user/current_user must both be the expected unprivileged runtime role, not superuser plus SET ROLE. Validate server/cluster/database/schema identity and migration digest. Acquire the singleton meta row FOR UPDATE before sampling trusted clock; clock rollback refuses. This deliberately matches existing serialized development semantics at this initial4096-account bounded scale. At most2 app operations/connections (same factory semaphore), no pool or extra unbounded workers; existing40 main connections untouched.

Preserve4096 accounts+pending erasures,8192 sessions/1024 anonymous sessions,4096 rate buckets; owner1000records/5MB/30day retention. Indexed pruning: history(created_at), sessions(expires_at),sessions(seen_at),rates(until_at),history(account_id,sequence) plus unique(account_id,event_id), account username uniqueness/session account indexes. Bytea salt/hash/token lengths and metadata/history payload size constraints are enforced. Accounts/sessions/history use cascading referential integrity; deletion plus cleanup outbox is one real transaction. An unavailable or revoked entitlement blocks enable/append only; list/export/disable/delete/account removal work independently, including after expiry. No HTTP grant/checkout endpoint or verified-payment flag.

Before COMMIT mark possible completion; post-attempt failures/cancellation report typed uncertainty/control-flow propagation and never assert rollback of a possibly committed update. Close owned cursor/connection on every path; a worker timeout retains its existing slot until it actually finishes. Preserve durable cleanup outbox and idempotent history UUID replay/conflict semantics. No automatic retry after ambiguous commit. Account signup recovery means log in using chosen credentials after an uncertain response; no fabricated verified email/password recovery.

## Review isolation: proposed, not executed

Create exactly one NEW workspace /var/lib/aitrust-id/account-review/<nonce32> after ROOT approves, recorded dev/inode/uid/mode; no shared paths, main DB/table/role/config, service units, firewall/DNS/proxy or public port modification. New venv/source/profile/logs live only in that workspace. Use existing debian operator and existing ait-intake synthetic runtime OS identity; no user/password/token/account creation on the host. Parent/source/venv0750 operator:runtime group; runtime private configuration0600; PGdata0700 operator; socket0770 operator:runtime. Existing service files/interpreters remain untouched.

Initialize a separate PostgreSQL18 synthetic cluster, not the running main cluster. Fixed listen_addresses='', owned private socket, unused port55449, max_connections8, shared_buffers32MB/work_mem1MB, durable fsync/full_page_writes/synchronous_commit/checksums enabled, no archives/replication/foreign extension. PGprocess owned by operator, runtime peer mapping only within this new cluster. HBA: operator admin peer; runtime can connect ONLYait_account_review and optionalait_account_restore; every other local/TCP connection rejected. NOLOGIN schemaowner; actual runtime LOGIN role NOSUPERUSER/NOCREATEDB/NOCREATEROLE/NOREPLICATION/NOBYPASSRLS/NOINHERIT/connectionlimit2. No owner membership; runtime limited CRUD on exact7tables and required sequence usage, no CREATE/TEMP/default PUBLIC execute/privilege grant. Service authentication/ownership is authoritative; no RLS or hostile-database-owner protection is falsely claimed.

Migration installs a fresh dedicated account schema under a single transaction/advisory lock and owner identity; unknown/existing version/objects refuse. Any precommit failure rolls back fully. A later rollback refuses to drop nonempty account data; never destroy another schema/DB. Runtime cannot migrate. Review DB uses synthetic accounts/data only. A pg_dump/restore round trip into separately namedait_account_restore within this SAME synthetic cluster tests restored signup/session/history/delete behavior; no main backup configuration or existing retention changed. Preserve outcomes and private artifacts, terminate/reap owned server/HTTP processes and confirm no listener remains. Retain failed owned workspace for diagnosis; do not blindly recurse/delete shared/private data.

Review runtime allowance:512MB disk/256MB service+PG memory, existing>=2GiB host reserve, two simultaneous store operations; closed wheel acquisition<=5MB plus metadata<=2MB, no sdists/compiler/new system packages. Synthetic workload<=10accounts/200history records and nonce-generated identifiers/passwords, no user inputs/owner secrets. Loopback account app port18791 only, same approved /v1/account and/account assets. No Caddy/public routing change. Capture main cluster PID/system identity SHA/config fingerprints/application table count and existing service process before/after; prove same main cluster is untouched. No 'main unchanged' claim based solely on child termination.

## Verification and rollout boundary

Before provisioning ROOT reviews exact dependency proposal and this isolation plan. Local stdlib/source-focused tests do not impersonate real PG. On isolated server prove real migration rollback, actual runtime privilege refusals, two-account isolation/signup/logout/login, CSRF/Origin, enabled/disabled/revoked history, idempotent/conflict append, filtered pagination/export, expiry/pruning, account deletion+outbox retry, clock rollback and ambiguous commit. Test actual HTTP workflow through existing create_app, not just SQL. Restore exact synthetic data into isolated restore DB and repeat read/delete/relogin. No public activation, signup collection, real merchant, pricing, charge or original requirement closure is inferred. Root later owns public service/privacy/backup activation and source admission.

## Planned owned paths

- tools/account_postgres.py
- services/accounts/postgres.py
- scripts/verify-account-postgres.py
- scripts/account-postgres-review.py
- deploy/accounts/001-account-schema.sql
- deploy/accounts/requirements.lock
- deploy/accounts/runtime-sources.json
- tests/test_account_postgres.py
- docs/account-postgres-plan.md
- docs/account-postgres.md
- runs/2026-11-24-account-postgres.json
- runs/changes/2026-11-24-account-postgres.json
- own CHANGELOG entry only after qualified handoff

No shared state/scope/account core/store/app/UI, gateway lock, production deployment config or policy/signer edits. Reuse current00bfae2 source or ROOT's next clean account-filter handoff as explicitly selected, preserving branch/evidence histories.

## Primary documentation checked

https://www.psycopg.org/psycopg3/docs/basic/install.html — pure Python psycopg uses installed libpq, no compiler/packaged binary required.
https://www.psycopg.org/psycopg3/docs/basic/transactions.html — transaction contexts commit/rollback and autocommit distinctions; a lost COMMIT acknowledgement is not proof of rollback.
https://www.psycopg.org/psycopg3/docs/basic/params.html — values bound separately from SQL.
https://www.postgresql.org/docs/18/libpq-connect.html — absolute host selects Unix socket, requirepeer authenticates server OS identity.


## Current shared-source and bounded implementation handoff

ROOT's clean40fc0ba9142261299c38698786374984503edca9 is the selected shared source for the actual final PG/API run, replacing the preliminary00b source before any account workflow execution. Optional state filtering, all/filtered counts, filtered-owner cursor and supplied-GET-CSRF binding are inherited unchanged. No older API emulation or shared-file edits. Actual separate-cluster provisioning has completed with15 hash-exact wheels and packaged notice texts, real least-privileged peer role, fresh migration success, intentional migration rollback and actual schema/owner/TEMP refusals. No account/API acceptance is inferred from provisioning alone.

The driver transaction ledger starts at entry before profile/connect/runtime guard and ends after commit/close,8s original finite/nondecreasing time; fixed metadata/domain queries clamp the server statement timeout to the remaining entry budget, at most3s. Runtime and schema guards use real results, not fabricated SQLite rows. The original app10s worker timeout retains its slot until the worker finishes. An OS/DB-owner freeze outside normal server timeout behavior is not excluded by an application wall-clock promise.

## Passfile diagnostic correction before edit

The first genuine40fc11-group PG/HTTP workflow passes, with exactly three harmless libpq warnings that /dev/null is not a regular passfile (165 stderr bytes; private server logs separately retained). Preserve that exact source49/actual result. Replace the character-device passfile option with /run/aitrust-account-peer-no-password only after verifying /run is a root-owned directory without group/other write and that the leaf does not exist (including symlinks). The application cannot create that root-protected leaf; if an operator creates it, refuse before libpq rather than read it. No credential/file is created, no default ~/.pgpass/environment fallback is enabled, and peer role/server authentication is unchanged. Qualify one actual connection/role/empty stderr plus focused refusals, without relabelling the prior11-group source or repeating it unchanged.

## Inherited libpq environment refusal before edit

ROOT source review identified that explicit host socket alone does not prevent PGHOSTADDR selecting TCP, and service/other libpq environment defaults can fill unset fields. Preserve the real49 HTTP phase and later unexecuted passfile-only source bytes. Before importing/calling psycopg.connect, refuse any environment key beginning PG, including empty values; no production os.environ mutation. Per-child trusted launch environments are explicitly fixed/clean and preserve the actual existing HOME only if present. Test PGHOSTADDR/PGSERVICE/PGPASSWORD as inert canaries with driver.connect never called and fixed diagnostics, then one real corrected Unix peer transaction. No external address/contact or owner credential lookup, and no old11-source promotion. Primary source: PostgreSQL18 libpq connection parameters https://www.postgresql.org/docs/18/libpq-connect.html.

## Shipped synthetic recovery and client launch boundary

The new review tool includes actual fixed review-to-restore pg_dump/pg_restore, never an arbitrary destination/archive flag. Runtime privileges are restored under the NOLOGIN schemaowner; the actual runtime peer role remains unprivileged. Fixed client launchers clear inherited environment in the child via execve, preserve only existing HOME plus closed PATH/LANG/no-bytecode/Python-psycopg settings, and never mutate the parent/threaded process environment. psql receives only its explicit fixed PGOPTIONS. pip adds --isolated; pg_dump/restore are no-password. Earlier successful provisioning remains bound to its original95dd helper; current restore/cleanup are separately qualified, not relabelled. All dependency wheels are private server prerequisites, not a new public bundle or admitted15th distribution route; original14 routes/policies remain unchanged.

Synthetic recovery verifies a nonempty owner record/password login, actualSQL expiry, persisted rollback-clock refusal, account deletion/outbox durability and retry through a separate real access engine. A point-in-time synthetic restore does not promise deletion from historical production backups, credential reset, encryption/RPO, public collection or future downloadable-wheel license clearance. Those deployment claims remain unavailable.

## Structural observer-independent cleanup and final current workflow

A private after-test observer initially saw a query backend exit between child enumeration and /proc stat, before its manually sequenced stop. Preserve the raw failure and corrected successful stop/main comparison. Shipped finish() now catches any review-observer error, ALWAYS attempts verified-owned filesystem/process-bound pg_ctl stop in finally, checks socket/postmaster disappearance, then independently attempts main snapshot/listener diagnostics. Original observer failure type remains visible; later cleanup/snapshot errors cannot replace it or manufacture pass. stop() no longer depends on diagnostic SQL being available. A fresh owned start reuses only this nonce's existing PG18 data, not provisioning or data reset.

ROOT authorizes one final current11-group HTTP run because PG-environment/passfile guards changed after the initial source49 run. The existing real access ledger is reused, fresh synthetic account identifiers stay within the original5 signup rate allowance, and distinct final log/report/fixture paths preserve original private evidence. No restore/provision/dependency rerun, unchanged broad suite, or original acceptance promotion.
