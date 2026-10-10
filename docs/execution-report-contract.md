# Execution report writing

Architecture: keep committed runs immutable, while routine test output goes to
ignored `output/verification/`. Shared JavaScript and Python writers validate
that destinations stay under repository `runs/` or `output/`, reject symlink
components and publish whole JSON files atomically. Reports under `runs/` use
exclusive publication and cannot replace an existing record. Scratch output may
replace an earlier scratch result. An explicit dated evidence destination is
required before recording a new run in the changelog.

This closes a real historical-overwrite risk in default verification commands.
It does not retroactively make old reports immutable or create independent
attestation. Raw source/input, tokens and private operational paths must not be
added to public reports. The existing changelog validates contributor attribution
and evidence hashes before commit/build/deploy; report writing is a separate
filesystem boundary. A compromised owner account can change repository files;
this mechanism protects ordinary command execution, not a hostile local OS.

Acceptance: positive atomic scratch and new-run writes, rejection of existing
run files, outside paths, symlink parents/targets, invalid JSON and failed
publication. Integration verifies normal browser reports use the shared writer
and default to scratch paths; date fields reflect actual execution. Preserve
all existing committed evidence bytes. Add source guards against old fixed-date
output defaults so new verification commands do not repeat the failure.
