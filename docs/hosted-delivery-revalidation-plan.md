# Source-bound delivery checks on disposable Linux

Architecture before implementation, November 22, 2026. Root owns this workflow
and shared delivery state. The Mac has less than 1 GiB available, below the
existing 2 GiB installation reserve; do not start a heavy local build or install.
Require the runner's existing Java compiler before Share controls so a missing
compiler cannot silently skip those cases; install no new JDK.
Use a standard ephemeral public-repository Linux runner with the current locked
Python/npm/browser dependencies. No paid runner or new service is introduced.

## Outcome and boundaries

Run the existing `scripts/revalidate.py` protocol and website capabilities
serially against one checkout. Preserve their full ordered commands, source
fingerprints, per-command exit/output digests and unchanged product/test limits.
Do not construct receipts from a different subset of CI logs. The current
manifest has69 protocol commands and64 website commands; the manifest remains
the authority rather than hardcoding these counts as a new acceptance rule.
Assess both actual reports against the unchanged checkout before declaring the
job successful. The11 protected checks and independent release gates stay intact.

A read-only same-repository pull-request workflow qualifies the candidate;
its main-push execution can qualify the actual protected merge. PR merge commits
and protected main commits have different identities: report both actual Git
HEAD and event SHA and never call the former the latter. Run no signing, secrets,
production calls, private examples, uploads of user input or deployment.

Preserve only the two existing source-bound JSON receipts in an artifact; use the
existing bounded unique-key evidence reader before export. Never upload the build,
source tree, home, workspace, screenshots or private logs. Retain reports for7days.
Use GitHub's actual run/head/merge identities when reviewing the artifact; reports
are not signed release artifacts. A failed or interrupted capability remains
Failed/Unavailable; a previous report is never a substitute. Initialize fresh
explicit unavailable reports before work.

## Failure and resource risks

Installation/network/browser failures are possible; they must fail the job with
the original evidence preserved. Bound the job and setup/check steps, without
changing any evaluator, worker, result wait or NF release deadline. A workflow
can rerun because PR path filters use a cumulative diff; freeze sources first,
retain reports privately for review and avoid metadata-only pushes while it runs.
Report hashes establish source/byte identity, not accuracy, human accessibility,
legal approval or permission to enable a tag. No original requirement closes
from this pipeline alone.
