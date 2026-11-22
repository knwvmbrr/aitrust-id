# Source-bound hash-inbox and agent-output evidence refresh

Plan recorded before edits by Codex /root/web_camo, 2026-11-22.

## Cause and unchanged contracts

At source755040c0fef91b44a534d297b7e3e357b069eefd, both historical
hash-inbox OS receipts, both agent-output OS receipts and the agent view receipt
match current bound sources except scripts/worker_process.py. Its reviewed
ownership repair requires new actual observations, not replacement hashes in
old records. The ordinary spec job consumes old inbox evidence before it reaches
the agent producer, so rerunning that job unchanged cannot refresh this evidence.

Preserve every November6/9 receipt unchanged. No product or worker behavior,
case count, namespace check, source validation, privacy flag, tag semantics or
completed-original criterion is changed by this maintenance. Fleet/SSO and root
source inventories, ledgers and changelog are outside this worker's ownership.

## Exact source and execution plan

Freeze selectors in scripts/verify-hash-reports-evidence.py and
scripts/verify-agent-output.py, and the corresponding two evidence test files,
to these new immutable execution destinations BEFORE running the producers:

- runs/2026-11-22-hash-inbox-macos.json
- runs/2026-11-22-hash-inbox-linux.json
- runs/2026-11-22-agent-output-macos.json
- runs/2026-11-22-agent-output-linux.json
- runs/2026-11-22-agent-output-view.json

The inbox producer binds its consumer, tests and existing workflow, so no later
source adjustment can be silently called covered. The agent producer binds its
own executing verifier. Record before/after source identity in each execution.

Extend only the existing private-hash-inbox-software workflow with Node24 and
its existing hash-locked eval requirements, then invoke the unchanged agent
producer after the unchanged inbox namespace/drop-privilege producer. Keep one
Ubuntu24.04 job, Python3.13, contents:read, existing10minute budget and7day
artifact retention. Add agent/worker source trigger paths; no new service, secret,
permission, public collection or environment is introduced. Both JSON outputs
are retained by the same job even if a later execution fails. Root commits and
pushes the final source for this one hosted Linux run.

Run the unchanged29-case inbox producer and33-case agent producer on macOS,
then the existing Chromium two-theme view check with its original privacy/CSP,
320px,200percent, keyboard and accessibility assertions. The browser slot is
explicitly granted and no native/Docker workload is started. Root updates dated
site reference copies and capability/source registrations. After Linux evidence
is retrieved exactly, run the narrow evidence consumers/tests and obtain a
different reviewer. No full-project or additional unchanged suite is needed.

## Risks and refusal boundaries

Stale receipts must continue to fail; missing new Linux evidence is an expected
pending state until actual hosted execution. Capture failures as new evidence
and diagnose before retrying. Never patch a recorded source map, case list or
platform flag. Existing temporary synthetic keys/files remain private and are
removed by the unchanged producers. A view check is browser engineering, not
human/physical-device acceptance. Hosted execution remains source-bound software
evidence, not detector accuracy, real feedback collection or new original credit.
