# Consumer and dependency acceptance — 2026-10-10

Codex implemented and executed this increment. The scope ledger now has 61
completed records and 141 open records, preserving every original ID. F-001 was
reopened when its date-time checker was found missing and is reclosed only after
the fail-closed fix and real checks. F-096, F-116 and X-13 close their named current
jobs; no tag is independently release validated by these component closures.

The current extension shares a bounded record profile between the service worker
and isolated page consumer. It refuses incompatible versions, unverified signed
records, bad dates/identities/spans, duplicate tags and asserted scores below a
supplied floor. Response bodies have a 2 MiB cap, strict UTF-8 and a fixed JSON
content type. Credentials go only to the existing authenticated loopback endpoint;
redirects and browser caching are disabled. Unknown valid signal IDs render safely.

Actual browser fixtures exercise all six states, stale response identity,
navigation, streaming, injection, keyboard behavior and compact tags. PII-only
results no longer announce a PS command-risk finding. Withheld tags expose their
actual code/reason inside optional details. The 38-case service-worker fault suite
uses real Web Stream/Response types with synthetic Chrome storage and fetch.
Installed-extension refresh, broader live vendor coverage and human screen-reader
acceptance remain unperformed; no fixture is presented as that evidence.

The new offline `scripts/check-assertion.py` accepts your own record, not an API
call to our evaluator. It checks schema formats and optionally the real extension
profile. Its status/exit codes distinguish invalid from unsupported and missing
tooling. Schema-only acceptance is neither signature verification nor accuracy.
Outside-implementer acceptance and a future adopted migration remain open.

The evaluation lock now includes the mandatory date-time checker and every
transitive artifact hash. Clean Python and both npm installations pass. Actual
corrupted pip and npm artifacts are refused. Three selected Linux images use an
immutable multi-platform base; embedded locks and all runtime package versions
match the inventory. The redactor's sealed model identity verifies before load.
The inactive registry is explicitly outside that verified preview inventory.

Thirty-one real Linux HTTP checks pass, including stopping each staging
dependency, observing the correct unavailable response, restarting it and
recovering. The services remain non-root, bounded and read-only with no internal
published ports. Bounded isolation probes are not a guarantee against every
exfiltration channel. Production data/backups were not altered and local Docker
was not started.

The final Python run passes 731 tests. Earlier failed reports remain in history:
the missing date checker, a mistaken synthetic missing-token setup, and an audit
negative test that assumed the first scope record could never be reopened. Each
has a recorded correction. Public test transcripts redact private environment
paths; they are not raw unsanitized transcripts. Later state/count documentation
updates do not masquerade as new runtime execution.

Evidence: [full suite](../runs/2026-10-10-consumer-version-final-python.json),
[Linux route](../runs/2026-10-10-consumer-current-service.json),
[fault suite](../runs/2026-10-10-extension-consumer-faults-corrected.json),
[six-state browser](../runs/2026-10-10-six-state-consumer-browser.json),
[selected dependency inventory](../runs/2026-10-10-selected-dependency-inventory.json),
[clean installs and corrupted-artifact refusal](../runs/2026-10-10-clean-hashed-installs.json),
[running image locks](../runs/2026-10-10-installed-runtime-locks.json), and
[preserved scope](scope-progress.md).
