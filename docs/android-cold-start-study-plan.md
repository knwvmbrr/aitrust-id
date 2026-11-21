# Predeclared Android cold-start characterization

This is one experimental study, not a production workflow or a retry-until-green
procedure. Exactly three fresh standard GitHub-hosted Ubuntu24.04 jobs will run
the API36 flow at frozen commit `56b0294c8e22b456eface6dad0a8d1afe68d1450`.
GitHub documents each standard hosted job as a fresh VM instance; this does not
assert physical host independence. Source: https://docs.github.com/en/actions/concepts/runners/github-hosted-runners

Question: will the existing intermittent owned-Ready first-receive failure recur,
and if it does, what fixed lifecycle/action metadata does the already frozen
failure-only discriminator observe? The earlier all-seven pass and zero-case
failures all remain evidence. The data do not justify a root-cause or reliability
claim if no failure recurs.

## Fixed execution contract

- One draft experimental stacked PR against `codex/android-hosted-followup`.
  Do not merge it into PR134, main or production.
- Trigger only the new study workflow path on PR `opened`. No push, dispatch,
  schedule, synchronize or reopen trigger. The three-job matrix is gated to the
  owned head/base/repository and `run_attempt == 1`; rerunning cannot start three
  more emulator jobs. No second PR/study without a new hypothesis and authorization.
- Matrix samples1/2/3 run independently, fail-fast:false, max-parallel3. Each job
  checks out exactly56b with no persisted credentials. Its control script is
  checked out separately from the study commit. No secrets are referenced.
- Copy the existing pinned Android workflow steps, runner,15-minute deadline,
  native/helper source, seven commands/assertions/waits, KVM rule, existing SDK
  license rule and ephemeral development signing unchanged. No local SDK,
  terms acceptance, paid runner escalation, physical device or app endpoint.
- Source-start/source-end guards bind the frozen commit and selected source
  identities; a dirty/drifted source cannot become an accepted study sample.
- Retain every sample's original reports, APK and build log with unique names,
  including failure/Unavailable/partial output. Retain a separate aggregate JSON.
- Aggregate FAIL unless all three source-bound jobs report EXECUTED, pass:true,
  API36, phase complete, exactly the original ordered seven passing cases, no
  Internet permission and unchanged existing license record. Missing, malformed,
  Unavailable, skipped, extra, failed or drifted input fails the aggregate. Never
  average out a failed job or promote absence of data to zero findings.

## Outcome and stop rule

This study stops after those three jobs. If all three pass, preserve all three
and say historical cause UNKNOWN; do not rerun for a failure. If any fails,
retain all outcomes, inspect only its existing safe metadata and propose a fix
only when the data identify a concrete mechanism. Do not call a diagnostic
failure a native bug without evidence. No accuracy, physical-phone, human,
maintained-release, full N-014 or original-requirement closure is granted.

Risks: startup/network/runner variability can confound three small observations;
the failure-only event buffer is bounded and can be absent/partial; source hashes
prove identity, not semantic correctness. Existing deliberate pause clearing may
discard interrupted drafts. This experiment changes no runtime behavior and
introduces no new success predicate or timing relaxation. Distinct source-only
workflow/security review is required before opening the PR and launching jobs.
