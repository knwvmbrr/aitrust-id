# Draft privacy engineering result

Codex · 2026-10-13 client date. Runtime evidence captured in UTC.

The explicit privacy mode of the existing local gateway checks caller-selected
text without calling PS. The user CLI provides a short result, optional private
JSON export and mode-preserving replay. It never changes or sends the draft.

Actual source-bound Linux checks: [26 existing service controls](../runs/2026-10-13-draft-privacy-real-services.json),
[15 full-pipeline replay controls](../runs/2026-10-13-draft-privacy-real-replay.json),
and [16 privacy-route controls](../runs/2026-10-13-draft-privacy-real-linux.json).
The privacy checks execute the installed checker environment, stop only owned
synthetic dependencies, verify privacy with the evaluator stopped and refuse
privacy while the redactor is stopped. They verify recovery on the actual
gateway-to-dependency path, not a cached engine health flag.

The real run exposed a restart defect. A [bounded container probe](../runs/2026-10-13-private-address-restart-probe.json)
found that a dynamically assigned private address changed across restart.
The setup now reserves and verifies private backend addresses. Its IPv4
selection rejects ambiguous, public and undersized subnets. The recovery
verifier also checks live readiness from the gateway.

[Fresh complete-input Linux setup](../runs/2026-10-13-draft-privacy-clean-setup-linux.json)
passes all ten failure controls. Original staging services were restored with
the same identities and configuration. [Bounded fixture cleanup](../runs/2026-10-14-draft-privacy-fixture-cleanup.json)
removed only the four newly owned test directories; no global prune was used.

[211 focused development checks](../runs/2026-10-13-draft-privacy-recovery-focused.json)
cover mode selection, identity refusal, CLI, replay, cancellation and private
subnet selection. These are development and operational checks, not an
independent recognition study.

F-105 returns to 100% on fresh full-job setup evidence. F-024 advances to 80%
because manual checking works, while browser compose/send permissions and
edit/cancel/proceed enforcement remain unimplemented. T-PII remains 80% pending
independent recognition and human acceptance. All 202 scope records remain:
124 complete and 78 open. No new tag is adopted, no browser send is intercepted,
no research collection is enabled and no physical-device result is inferred.
