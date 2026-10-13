# F-105 — one-command Linux setup

The clean committed clone ran `python3 scripts/setup-local.py --engine podman`
with explicit private state, an offline checker wheelhouse and explicitly
selected `--build-network host` for image dependency downloads. Installed Linux Podman
and previously downloaded pinned image/package dependencies were prerequisites.
The command created a fresh private token/checker environment, built three
source-matched images, started constrained containers, checked the authenticated
schema-valid pipeline and then demonstrated PS plus procedural PII redaction.
It never executes the text submitted for checking.

Ten actual Linux controls passed: port collision, changed ownership, checker
finding exit status, input/token log exclusion, owned stop and credential
retention, existing-install refusal, missing engine, corrupt dependency,
build failure and startup failure. All owned resources were removed; the
original dedicated staging containers were restored with the same IDs, images
and configuration. The site, database and backups were not changed by these tests.

Container inspection and actual process capability sets enforce non-root UID
10001, read-only filesystems, no new privileges, PID limit 128, bounded memory,
private internal dependencies and loopback-only publishing. Gateway dependencies
use validated addresses from its owned inspection network, so an unavailable
container DNS alias cannot silently substitute another service.

Earlier attempts refused readiness: build DNS, engine inspection spelling and
an unhealthy gateway exposed real gaps; isolated namespace fixture attempts also
failed. Their diagnostics remain in the private execution archive. No failed
attempt counted toward completion. The current public receipt is
[the complete-input actual Linux run](../runs/2026-10-13-one-command-complete-input-linux.json).
`python3 scripts/verify-local-setup-evidence.py` refuses changed source, missing
failure controls and assertions of human or independent tag validation.

Under the [owner-approved separation](../runs/2026-10-13-clean-setup-owner-decision.json),
F-105 is complete for this named setup job. F-142 retains real-person installation,
accessibility and physical-phone acceptance. This is a development checker,
not tag accuracy certification, a cold-host daemon installer, a tested Docker
setup claim, an extension-signing installer or research collection.

Review strengthened this evidence to bind all 27 Dockerfile/COPY/lock/health/CLI
inputs. The earlier seven-input receipt stays historical. Exact input bytes now
allow verification of downloaded source without requiring Git ancestry. Changed
COPY inputs, protocol helpers or dependency locks require a fresh actual run.
