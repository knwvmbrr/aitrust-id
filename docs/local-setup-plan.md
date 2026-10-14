# One-command local setup — F-105

The owner accepted separating this setup job from F-142 human acceptance.
From a clean clone, a standard-library Python command will build and start the
three existing services using a preinstalled Linux container engine. The command
does not install a privileged daemon, change system settings, or accept input
programs to execute. The existing loopback endpoint and runtime taxonomy remain.

Architecture: preflight Python/engine/port before mutation; exclusively create
an owner-private directory outside the repository; install the hash-locked
schema checker in its own virtual environment; generate a private token; build
source-matched images; create uniquely labelled networks and constrained
containers; inspect effective security and source identity; then verify health,
authentication and the real redaction/evaluation/schema pipeline. Readiness is
recorded only after those checks. A stop command operates only on recorded IDs
whose labels still match, never on a global project or unrelated resource.

Risks: builds and initial package downloads use external registries; pinned
hashes constrain artifacts, not all supply-chain compromise. Engine access has
host-level consequences. A port or existing-directory conflict must fail rather
than replace an installation. Engine differences can silently ignore limits,
so inspect effective runtime limits and internal networks. Failure cleanup is
limited to IDs created in this invocation; private files and failed state remain
for diagnosis, without logging the token or raw input. Concurrent setup is
serialized by exclusive directory creation. Existing Docker/Podman storage,
production services and other networks must remain unchanged.

Acceptance: clean Linux clone, one command, healthy three-service stack, actual
positive and negative checks, private credentials, least-privilege effective
configuration, source identity, no printed token/input, port/preexisting-file/
dependency/build/health refusal and owned cleanup. Synthetic and automated
checks do not complete F-142, independent accuracy or extension signing setup.

An explicit `--build-network host` option is limited to initial image builds on
Linux hosts whose isolated builder cannot reach configured DNS/downloads. It
increases network reach for pinned dependency installation and must be chosen
by the operator; private builder networking remains the default. Builds still
have their container filesystem, hash-locked artifacts and allowlisted context.
No host credential directories are mounted. Runtime service networks, UID,
capabilities, resource limits and loopback publishing remain unchanged. This is
not a promise against compromised dependencies or host administration.
