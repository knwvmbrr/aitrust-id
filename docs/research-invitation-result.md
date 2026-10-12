# Executed invitation component

Codex added an independently applied synthetic PostgreSQL invitation profile under N-011. The original metadata profile remains separately runnable. Neither profile creates a public endpoint, installs production authorization or accepts participant records.

Current Mac source controls pass 33 tests. On the dedicated Linux host, two fresh ordinary-user PostgreSQL 18 clusters passed the original profile’s 39 control groups and the invitation profile’s 15 groups, including six concurrent submissions against two slots. Unknown/revoked/expired invitation and duplicate, private payload, quota, cross-invitation, withdrawal/replay, role bypass, shadowing and bounded retirement behavior were exercised. Exact source hashes matched; both socket-only clusters were stopped and removed, then the owned staging directory was removed.

The first local archive list incorrectly requested a nonexistent `protocol/__init__.py`; it stopped before remote access. Protocol is an existing namespace package. The corrected source-only archive includes the actual files and imports successfully on Linux. The first passing invitation receipt is preserved for its earlier verifier source; the expanded current verifier is bound by a later receipt.

N-011 remains 60% and open, with its original full acceptance retained. Independent tag accuracy, participant consent, production logins/intake, provider handling, backup expiry and replacement-host recovery are not credited. Protected CI/publication remain pending for this increment.

The first website run completed all eight checks but correctly refused because generated scope projections changed during execution. Preparing them before a new source-bound run produced a passing eight-check receipt. The first full Python run also refused the stale reviewed route inventory (nine failures, 2507 passes); that failure is retained and a fresh inventory review must precede the accepted whole-suite run. Neither guard was relaxed.
