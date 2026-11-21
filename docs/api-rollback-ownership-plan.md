# Retire API activation authority before replacement

The original operator accepted an old successful rollback record again after a
new activation installed identical canonical units. Hash equality established
content, not ownership. Actual temporary files and original functions reproduced
stale stop/disable/delete against the replacement; no real services were used.

Before changing code: serialize mutating entrypoints with one no-follow private
lock in the existing owned BASE. Read-only activation planning creates nothing.
A new apply claims an exclusive active record name and random invocation epoch;
state and the lease must agree before publish/finalize/rollback. Canonical hashes and each installed unit’s captured device/inode
remain required, so an identical-content replacement cannot borrow ownership. Legacy unanchored records, including the historical live record,
fail closed: no automatic adoption or remote rollback is performed by this work.

Rollback preflights every recorded unit, exact rule handle plus its full recorded
definition (ignoring only mutable counter values) and persistence bytes
before stopping anything. A missing recorded rule handle cannot adopt a tagged
rule. Save rollback_in_progress before resource changes and retain its lease on
all failures. Only that same active invocation can resume after partial removal.
Persist terminal rolled_back before releasing the lease; a failed terminal write
must prevent a replacement activation. Retired records can never regain authority
because a later active invocation has a different epoch. A persistent exclusive
lock prevents overlapping cooperating operator processes.

Crash limits: this is not one atomic transaction across systemd, nft and files.
An interrupted/uncertain write or lease cleanup can require manual operator
review; safety takes priority over automatic adoption. Never flush/reload the
firewall or touch other namespaces. Deployed app/operator879 and remote services
remain unchanged; these are isolated source and synthetic host controls only.

Owned changes: deploy/ai-tools/activate.py, tests/test_ai_tools_activation.py,
this architecture, immutable failure/correction evidence and attributed event.
Verify the original stale replay, actual replacement preservation, failed state
write before mutations, terminal-write blocking/recovery, unit/rule/persistence
drift before service actions, lock contention and dry-run/no-overwrite behavior.
