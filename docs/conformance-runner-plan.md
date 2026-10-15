# Conformance runner: architecture and acceptance

Run a versioned set of invented assertion records against either the existing
reference CLI or an implementer's explicitly supplied local executable. This
extends F-119's runnable tool and F-120's inspectable evidence, without issuing a
tag or granting outside-person, accuracy, license or certification acceptance.

The harness pins the vector file's bytes and sends one input per fresh process.
It appends `--profile schema` or `--profile extension` to the supplied argument
list; no shell is used. The response contract is the existing small checker JSON
summary and exit status. Both must match the case. The report identifies every
case, vector digest and harness source digest, retaining result hashes rather
than arbitrary program output. Incomplete execution cannot pass. Results do not
contain the command arguments, submitted records or exceptions.

Risks: an implementation is executable code, so users must trust the executable
they select. Process supervision bounds elapsed time and stdout and kills the
owned process group on failure; it is not a filesystem or network sandbox.
Synthetic cases establish a limited interoperability target, not comprehensive
correctness or an independent human assessment. Changed vectors require an
explicit version/pin update. Existing signal/tag jobs and the external acceptance
requirements remain open. Any acceptance reassignment requires the pending owner
answer; this implementation itself changes no completion counts.

Acceptance: run both actual reference profiles; run an independently written
adapter using the documented process contract; detect a lying always-pass
adapter, mismatched exits, forged certification, invalid/duplicate-key output,
missing tooling, output floods, timeouts and child cleanup. Use focused checks.
