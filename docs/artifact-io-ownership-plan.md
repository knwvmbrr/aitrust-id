# Artifact evidence publication ownership repair

Architecture before code. Base bd1610329fc22bba9c3e91fd0ade9dd5c7c176ab.
Own only tools/artifact_evidence_io.py, focused tests, this plan and exact
execution/review records plus scoped attributed changelog metadata. No MCP,
policy, signing identity, other foundational helper or global ledger edits.

## Actual failure and contract

An owned prepublish callback moved the temporary file aside, placed a different
file at its old name and refused. Unconditional cleanup then deleted the new
file. Preserve this original counter, atomic no-replace publication of COMPLETE
verified bytes, no new final output on prepublish refusal, raw FD ownership,
all-close attempts and typed postpublication uncertainty. Failed private bytes
may remain; never promise rollback or generic recursive deletion.

## Bounded correction

On any prepublication or link-attempt failure, retain temporary names and bytes;
do not unlink by a name whose ownership may have changed. After the trusted
prepublish callback returns, verify original descriptor contents, regular-file
owner/mode/link count and its temporary-name identity before attempting link.
On successful publication only, validate both final and temporary aliases against
the held descriptor before one temporary unlink. If identity/check/cleanup fails,
retain names and report OutputCommitUncertain. No final pathname is removed.

Track every descriptor used as a private ancestor and every immediate private
parent/directory. Recheck .git absence and immediate owner-private permissions
in check(), after prepublish, after successful publication and before closing.
close() must attempt every owned descriptor exactly once even if the final
boundary check or an individual close fails. Postpublication boundary/close
failure remains typed uncertain; ordinary prepublication refusal stays ordinary.

## Threat boundary and risks

These descriptor checks cover stable owned private directories and the actual
sequential callback/fault counterexamples. Portable stat-then-link/unlink is not
an atomic defense against an actively hostile concurrent same-UID filesystem
writer. Do not claim that universal guarantee or add blind rollback. Source
snapshots/old receipts remain historical when the helper changes. No signing,
license, detector, source-truth or broader original closure follows.

## Focused proof

Use only tiny owned synthetic files: original callback swap/refusal, swap/return,
normal complete 0600 no-replace output, symlink/existing output refusal, fdopen
failure, write failure, post-link unlink/fsync/close failures, all-close attempts,
private marker appearing during callback or after save, ancestor/private-mode
drift and cached public-to-private directory checks. No SDK, archive build,
network acquisition, account, daemon or large output. Distinct peer replays the
actual counters and positive publication before PM integration.
