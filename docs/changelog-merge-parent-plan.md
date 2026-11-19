# Preserve evidence identity during a real pending merge

Before implementation: the existing changelog verifier already authenticates a historical event against its unique original reachable addition and that commit's exact evidence bytes. Its staged-index wrapper currently searches only HEAD. A pending merge can introduce a real sequence in which an observed manifest was corrected; the original event lives only in MERGE_HEAD until the merge commits. Requiring both old and corrected hashes against today's manifest prevents a valid merge despite preserved immutable records.

Extend origin lookup only for uncommitted/staged verification of a real pending merge. Search HEAD and Git's verified MERGE_HEAD commit together. Keep the unique original-addition requirement, exact event-byte equality, exact evidence-byte hash, append-only old records, human entry checks and fresh current-file coverage. Explicit committed ranges and arbitrary/dangling branches gain no additional trust. Do not edit earlier events or rewrite their evidence.

Exercise actual temporary Git merge histories, index snapshots, changed-event tampering, bad original evidence and copied-but-unmerged branch events. All existing refusal checks stay required. This affects change-accountability tooling only, not tag results or independent release acceptance.

Read the literal MERGE_HEAD file under Git’s per-worktree absolute git directory,
not an ambiguously resolved ref or final symlink: an
ordinary branch or tag can legally use that name. Require one bounded regular
no-follow, nonblocking, stable-identity file containing a single full commit OID;
verify that exact object is a commit. Named refs, links, FIFOs, oversized or
multiple-parent metadata do not supply historical evidence.
