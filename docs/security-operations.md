# Security response and replacement-host recovery

Michael is the accountable operator and repository owner. Codex implements and
verifies software changes; Claude's lane is review. Neither automated assistant
is an on-call human responder. There is no response-time SLA, staffed security
team, certification, or guarantee against compromise. The public site is a
static catalogue and account-free personal preview; research collection remains
disabled. Private operational credentials and user information are never public
transparency records.

Use GitHub's private vulnerability reporting control to submit a security issue.
Do not put private answers, credentials or exploit instructions in public issues.
The operator triages the report, records affected versions and routes, contains
exposure, fixes and tests the defect, then publishes a sanitized advisory and
changelog entry. Keep private material out of the advisory. security@aitrustid.com
is an additional owner-created address; independent inbox receipt is not claimed.

## When a capture adapter breaks

1. Stop capture for that adapter. Do not broaden permissions or fall back to
   scraping prompts, other tabs, or an entire page. A missing response is
   Unavailable, never a clean verdict or a fabricated tag.
2. Keep the independent pasted-text and Terminal checkers available. Save the
   adapter/method version, error category and an invented reproduction, rather
   than a person's conversation.
3. Repair the declared selector or transport and run the relevant extension and
   lifecycle checks. Exercise missing, changed, duplicate and out-of-order
   response cases before reenabling that adapter. Record source identities and
   the limitation that synthetic markup is not current vendor acceptance.

## When storage or a server fails

Keep public checking independent of private organizational storage. Disable
private intake during recovery. Alert messages contain only approved service
names, state and UTC time; application data stays out of both mail and ntfy.
The source health check verifies archive failures, WAL reserve and free disk.
The separate provider retains protected encrypted generations. Never restore
into the live primary or put the repository decryption key on the backup host.

The recovery drill has distinct stages. Check each proof before moving forward;
a failed command leaves the recovery incomplete.

1. **Prepare:** run `deploy/recovery/prepare.py --execute` as root only on the
   dedicated Debian 13 primary with the supported PostgreSQL 18 profile. Its
   existing `cloud-localds` and `qemu-img` tools are prerequisites. The installer
   refuses package upgrades/removals and insufficient memory/disk. The downloaded
   Debian image is checked against the vendor's HTTPS SHA512 manifest; this is
   not a detached image signature.
2. **Build:** provide the eight versioned `deploy/host/` configuration files to
   `deploy/recovery/guest.py start --work WORK --source FILE`. This executes the
   baseline inside a fresh KVM guest, never on the primary. Poll its `inspect`
   command until preparation succeeds and the primary snapshot is unchanged.
   Pin SSH from the guest console before connecting.
3. **Isolate:** run `deploy/recovery/isolate.py isolate --work WORK --launcher
   HASHED_GUEST_HELPER`. The helper must be root-owned in the content-hash cache.
   Verify a different network namespace, loopback only and denied outbound TCP.
   Boot again inside that boundary before introducing any recovery material.
4. **Collect:** on the owner's computer, run `deploy/recovery/collect.py --primary
   HOST --primary-key KEY --recovery-directory BUNDLE --work WORK --output PROOF`.
   Use existing strict SSH host pins. It validates a root-protected generation,
   verifies the owner-held cipher against the source, and streams encrypted files.
   Administrator private keys remain on the owner's computer. Files and arguments
   containing credentials must stay outside every Git checkout.
5. **Restore:** `deploy/recovery/apply.py` accepts its private JSON material on
   standard input, plus `--work`, `--isolation-tool` and `--guest-program`. The
   material has `cipher`, `source_settings` (the five bounded PostgreSQL recovery
   settings) and `owner_admin_public_key`. It refuses a wrong target, bad cipher
   and corrupt metadata; restores the actual selected backup; verifies identity,
   inventory and roles; and keeps database TCP and outbound archiving disabled.
   A successful restore checkpoint cannot be overwritten by rerunning restore.
6. **Operate:** `deploy/recovery/monitor.py` accepts the three versioned operational
   sources on stdin, plus `--work`, `--apply-tool` and `--isolation-tool`. It
   reconstructs the existing monitor units, detects an actual guest database
   outage/restart, and checks bounded incident/recovery messages without sending
   them externally. Normal backup probes are deferred only in this offline drill;
   disabled archiving is explicitly detected as a failure, never called healthy.
7. **Verify and remove:** authenticate with the owner's existing key without
   forwarding its private bytes, then use `deploy/recovery/finish.py reboot`,
   `verify`, and finally `cleanup`, with the same work and pinned helper paths.
   Verify a new guest boot, restored database, source health and unchanged primary
   snapshot before deletion. Keep sanitized proofs outside the disposable work
   directory. Cleanup removes only that nonce's VM, decrypted disk, temporary key
   and encrypted staging copy. It does not remove original protected generations.

Every helper must first be installed in `/var/lib/aitrust-id/recovery-source/`
under `NAME-SHA256.py`, root-owned with mode 0700, by a verified authenticated
transfer. Verify the hash before execution. Do not run root helpers from writable
`/tmp` locations. Do not paste recovery material into a shell command, browser,
chat, source tree or public log. Control subprocesses have closed standard input;
only explicit transfer subprocesses receive payload bytes.

## What the November 6 drill establishes

A real Debian guest with its own kernel, systemd, SSH, firewall and PostgreSQL
restored an actual protected encrypted generation from the independent provider.
Its 46 foundation checks passed before isolation. Wrong-key, corrupt-metadata and
wrong-destination attempts were refused. Owner-key administration, operational
failure detection, reboot persistence, source preservation and cleanup succeeded.
The database had zero application tables: no occupied application-table recovery,
production-load RTO, cross-provider failover or human recovery acceptance is
claimed. Prior synthetic record-recovery tests remain separate evidence.

Failures found and corrected during execution: disappearing transient units now
use a persistent preparation checkpoint and an explicit bounded launch builder;
control SSH subprocesses cannot consume private stdin intended for a transfer;
reboot verification waits for bounded readiness; owner access uses the exact
pinned host-key alias instead of disabling strict checking.

Separate obligations remain open: owner offline custody and recovery-code access,
independent monitoring/receiver acceptance, human operation, live vendor and
screen-reader acceptance, consenting research pilot, independent tag accuracy,
and any qualified legal/security review required for a broader deployment. These
are not erased by a successful replacement-host drill. No promise that all
possible security defects are absent is made.

Three narrow repairs followed the complete VM run: explicit closed stdin in the guest launcher, readiness metadata that does not infer data-copy state, and an image-tool prerequisite check. Fourteen focused cases exercise the current repaired source. The evidence preserves the actual executed helper hashes separately; a second complete VM run of these later source edits is not claimed.

Review also tested repeat-use behavior: receiver installation reuses only a root-owned, private, single-link, hash-matching file; all other existing objects are refused. Reboot verification waits for the specific requested boot change through transient SSH unavailability. These repairs have focused source-bound tests, including an actual isolated receiver-cache exercise on Linux; they do not imply another complete VM restoration.
