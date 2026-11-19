# Where the CI wait goes

Observed 2026-11-19 by Codex, including a separate read-only review lane. This is
an observation and next experiment, not an implemented speed improvement.

The metadata follow-up [run 44486045559](https://github.com/knwvmbrr/aitrust-id/actions/runs/44486045559)
took **509 seconds elapsed**. Its jobs used **1,255 summed seconds**. These are
different measures; neither is a claim about billed or rounded runner minutes.
The exact run revision, workflow digest and per-step observations are in the
[execution record](../runs/2026-11-19-ci-efficiency-observation.json).

| Cost | Observed time | Meaning |
| --- | ---: | --- |
| Site job | 504 seconds | Critical path for the developer |
| Site browser/OS provisioning | 243 seconds | Nearly half of that job |
| Site catalogue/accessibility checks | 125 seconds | Actual assertions, retained |
| Site device-engine checks | 48 seconds | Actual engine parity, retained |
| Accessibility browser/OS provisioning | 93 seconds | Separate installation |
| No-egress full test suite | 275 seconds | Executes in its distinct isolation boundary |
| Spec job | 162 seconds | Includes normal-environment checks |

The two browser provisioning steps account for 336 seconds, or about 26.8% of
summed job time. Selected native/model notice checks took about three seconds;
they are not the main bottleneck. These measurements do not prove an alternative
will be faster.

The next bounded experiment is a version-matched, digest-pinned hosted browser
image, changing provisioning only. Verify that an appropriate official image
exists and verify its digest before selecting one. Benchmark image pull,
Python/OS compatibility, nonroot browser behavior and the entire unchanged
assertion set on the hosted runner. Adoption needs actual parity and a measured
improvement. A preinstalled image or cache is not automatically faster.

Keep all required named checks, current-source evidence, signature/source
controls, namespace isolation and the separate accuracy/accessibility release
gate. Preserve existing event deduplication and main-only provenance signing.
Do not replace isolated tests with normal-environment results. Do not exempt
arbitrary paths or grant cached test-result credit. Even a changelog-only change
can alter a published artifact because the site builder exports the changelog.

No workflow or assertion changes were made for this observation. F-054's
existing acceptance is unchanged; no open requirement is closed.
