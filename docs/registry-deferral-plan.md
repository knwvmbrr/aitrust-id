# Registry deferral enforcement — architecture before change

Scope X-14 defers the registry container from 0.1. This is separate from the
owner's consented future research pipeline (N-011), which remains unconnected.
The optional profile currently launches an unvalidated Streamlit/SQLite prototype
whose caption overclaims anonymity and whose 30-day expiry is not implemented.

## Implementation and protection

Retain the prototype as explicitly inactive historical research source. Its copy
must disclose linkability and missing retention. The current registry image builds
only a small refusal launcher on the same pinned Python base as the existing
services, runs without root and exits with a fixed deferred message before any
application, listener or database opens. Remove the registry's published port and
storage volume from the initial Compose profile. Keep the profile and proposal
identity so a future accepted implementation remains tracked, rather than erased.
No future-version/environment switch enables it. Future activation requires new
reviewed code, contract, consent, access, retention and protocol-version decisions.

Extend the existing release guard to reject changes to these exact properties.
Version the source review after tests, retain public claims as deferred, and keep
personal checker/production database/backup operations separate.

## Verification

Execute the refusal entry point locally with a fake data directory and assert
fixed status/output and zero filesystem writes. Deliberately mutate the Compose
contract: default activation, published ports, volumes, image override and command
replacement must be rejected. Build and run the actual image in disposable Linux
staging on the dedicated project host using Podman. Confirm exit, no listener,
non-root/read-only/capability-limited execution and no data writes. No local Docker,
real user data, new endpoint or production restart is needed.

Risk: an archived prototype remains readable and modifiable under the open-source
license. Deferral enforcement applies to this reviewed release; it cannot prevent
a person running modified source. A launcher refusal is not research consent,
retention or future registry acceptance. Preserve those requirements independently.
