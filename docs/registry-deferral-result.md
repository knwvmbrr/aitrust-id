# Registry deferral — executed acceptance

X-14 is complete for its full named job: defer the registry from this release.
The source remains available as an explicitly inactive prototype. F-044 and N-011
remain open; no registry, research intake, retention or training system is implied.

Codex implemented and verified the current refusal image, which returns status 64
and a fixed message before a listener or database opens. Compose publishes no
registry port, attaches no volume or network, runs without root, uses a read-only
root filesystem, drops capabilities and limits memory/PIDs. No environment version
can activate the preserved prototype. Modified forks require their own review.

Actual Linux Podman execution verified default and future-version cases with only
synthetic data: no application writes, no published ports, UID 10001, zero effective/
permitted/bounding capabilities, no-new-privileges, and verified removal of all
three disposable containers and their tagged image. No local Docker or production
restart was used. The source-bound release guard rejects stale/failing evidence,
launcher/image changes, command/image overrides and storage/network activation.

902 Python tests passed, including 57 registry and existing route controls. This
closes one full requirement: **103 complete, 99 open, all 202 preserved**. It is
not independent tag accuracy, legal approval or future collection acceptance.

Failed container checks are retained. Their cause was an engine-created mount
path mistaken for an application write. The corrected verifier uses an existing
mount path; the application-write check remains enforced. See the
[failure record](../runs/2026-10-10-registry-deferral-failure-resolution.json),
[actual Linux record](../runs/2026-10-10-registry-deferral-linux-corrected.json),
[Python execution](../runs/2026-10-10-registry-deferral-python.json) and
[boundary review](../runs/2026-10-10-registry-deferral-reviewed-boundaries.json).

Publication is tracked separately in state and the deployment receipt. A source
or contract change reopens the acceptance; a document label cannot pass the guard.
