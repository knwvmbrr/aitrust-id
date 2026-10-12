# Synthetic admission execution — 2026-10-12

Codex implemented and executed the private request parser, real command-line
admission and withdrawal path, independent sandbox profile and CI job. All records
were invented. No public endpoint or production database was changed.

The current local selected suite passed **177 tests**. An isolated network
namespace on the owned Linux staging host passed **174 tests**, with one existing
platform skip and two Node-dependent parity checks unavailable on that host.
Those two parity checks passed locally; CI installs Node 24 and runs the complete
suite rather than silently excluding them.

Three fresh non-root, socket-only PostgreSQL 18 databases passed **39 storage,
15 invitation and 8 admission control groups**. The admission groups invoke real
CLI processes, including a six-process quota race. Both IPv4 and IPv6 external
connections were refused in the distinct test namespace; Unix socket database
operations ran. Every temporary database was stopped and removed, selected source
hashes stayed unchanged, and the owned staging checkout was removed.

Failures remain in the record: namespace/probe setup, absent Linux Node, and a
verifier function shadowing Python’s concurrency module. The latter crashed after
six successful groups; a fresh private diagnostic reproduced the AttributeError.
The function was renamed and the complete current run then passed. A new malformed
UUID boundary test also caught a generic exception; it now produces the admission
contract refusal. Failed runs are not rewritten into successes.

- [Current Linux controls](../runs/2026-10-12-admission-linux-controls.json)
- [Current local controls](../runs/2026-10-12-admission-local-controls.json)
- [Retained verifier failure](../runs/2026-10-12-admission-worker-shadowing-refusal.json)
- [Retained UUID contract failure](../runs/2026-10-12-admission-uuid-contract-refusal.json)

**No full requirement closes from this component.** N-011 and F-141 remain open.
No human label, independent tag accuracy, participant consent, deployed research
service or production authentication is asserted. The [operating guide](research-admission.md)
lists the remaining real-pilot gates.
