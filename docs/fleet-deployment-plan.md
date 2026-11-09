# Owner-controlled fleet deployment

F-159 needs functioning enrollment, rollout cohorts, policy precedence, inventory
and rollback. The supported software profile will distribute the existing
standalone PS **development** checker to private operator-owned macOS/Linux
workspaces. It will not create a hosted service, browser force-install policy,
public tag release, background collector or paid contract.

Each device independently enrolls with a separately obtained Ed25519 public key
and explicitly approves exact source packages. Signed organization policy may
select only those approved packages, restrict the input limit, pause a managed
route and target its cohort/device. It cannot change detector thresholds, claim
validation, collect text, enable telemetry or issue authorship receipts. Local
pause and withdrawal take precedence. Personal checking remains separate.

A package binds a fixed, inspected standalone source graph and license. Install
only private JSON package files, never arbitrary archive paths or install hooks.
Before activation, preflight the approved checker on fixed synthetic clean and
command-pattern inputs. Before execution, verify package identity, all source bytes, policy signature,
expiry, target and monotonic policy sequence. Materialize approved code into an
owned temporary directory and use bounded stdin/stdout subprocesses; never put
response text in arguments, inventory or logs. Cache packages for offline use;
expired policy makes only the managed route unavailable.

Use a private per-device directory, owner-only no-follow regular files, bounded
strict JSON, an OS-released exclusive lock and atomic state replacement. A crash
before activation leaves the old policy intact. Rollback requires a new signed
policy sequence selecting a previously approved package. Inventory is an explicit
metadata-only export; nothing is automatically sent. Removal verifies owned
members before deletion and refuses foreign or altered files.

Risks include an incorrectly selected trust key or source approval, same-user
malware, replay, clock changes, policy/capture coercion, interrupted writes,
wrong-cohort rollout and text leakage. This does not protect against a malicious
OS administrator or establish that an organization has legitimate employee
consent. Do not create a real organization key or enroll this Mac during tests.
Exercise actual two-cohort CLI operation, disabled/expired/offline states,
unauthorized updates, rollback, interruption and personal-route independence on
macOS and isolated Linux. Preserve full F-159 acceptance; keep organization
rollout, human/security review and commercial activation obligations explicit.
