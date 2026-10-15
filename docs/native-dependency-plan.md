# Native dependency evidence: architecture and acceptance

F-057/X-02 require review below top-level npm license labels. Inspect all artifacts
in both complete locks, including platform alternatives. Use the existing
integrity-checked archive cache without installing or executing package code.
Capture each bounded regular archive once; verify its lock integrity and observed
SHA-256 before parsing those same bytes. Stream tar members with size/count/path
limits. Record native-format and executable-name candidates, exact binary hashes,
root bundled-version lists and README licensing declarations. Record nested
archives as uninspected rather than silently claiming transitive coverage.

Store upstream declaration bytes unchanged under content-addressed names. An
offline verifier binds the inventory to both locks, the earlier notice inventory,
scanner code and tests. An explicit archive replay reproduces the observations.
Changed locks, unknown artifacts, duplicate/unsafe members, altered declarations,
stale source identities, corrupt archives and attempted permission promotion fail.
No source is extracted or executed and no network is used by either command.

Risks: binary format/name recognition is a candidate inventory, not a complete
native-code detector or SBOM. Java bytecode can share a fat-binary magic value;
encoded/embedded/nested code and full source/relinking obligations need separate
review. Upstream README license tables are declarations, not the full license
texts or legal clearance. Classification never grants permission. All clearance
and complete-transitive-coverage flags remain false. No new tag, endpoint,
telemetry, production data or runtime dependency is introduced.

Acceptance: exercise actual locked archives; reproduce a selected artifact and
the complete 205-artifact inventory; refuse checksum changes, unsafe/link/duplicate
members, size/count excesses, declaration drift, malformed version metadata,
missing artifact coverage and false permission claims. Use focused tests.

Three locked workerd 1.20261006.1 artifacts have observed executable members of
135,408,472, 134,840,256 and 139,110,920 bytes. Their exact archive SHA-256 plus
member name select those exact limits. All other members retain 128 MiB; total
expanded bytes stay bounded. Streaming hashes do not retain binaries in memory.
The first attempted collection refused these cases and wrote no inventory.
