# Offline fleet deployment

This is software for an operator-owned **PS development** fleet on macOS/Linux.
It deploys the existing standalone checker, with its original limitations. It
is not a validated tag release, browser force-install service or commercial
organization deployment. No website account, background agent or network is
needed. Other personal tag routes remain independent.

Use Python with the existing hash-pinned `eval/requirements.lock` environment.
Every private directory must be owned by the current operator and mode `0700`,
with private regular files mode `0600`, outside source checkouts. Resolve system
temporary-directory links before using them. Protect the authority key separately
from device workspaces; compare the public-key fingerprint by a trusted channel.
A policy signature authenticates the selected key, not an employer, consent or
accuracy. The operating system and selected source checkout must be trusted.

## Package and enroll

Run these commands yourself in your trusted clone. Replace the example private
paths with your own existing `0700` directories. Key generation creates a new
organization authority; this project does not generate your production key for
you or send it anywhere.

```sh
python scripts/fleet.py keygen --private /private/fleet-admin/key.json --public /private/fleet-admin/public.json
python scripts/fleet.py package --output /private/fleet-admin/package.json
```

Copy only the public key and source package to an enrolled device's private
transfer directory. A device must obtain its package from an independently
trusted source, inspect/approve its exact identity and select the authority.
An organization signature alone cannot approve new executable source.

```sh
python scripts/fleet.py enroll --root /private/device/fleet --public-key /private/device/public.json --package /private/device/package.json --cohort canary --consent-local-only
```

Enrollment prints a random device ID, exact package identity and authority
fingerprint. It starts **paused**. Use `stable` for a separate cohort. Up to eight
packages can be approved with repeated `--package` options, supporting staged
updates and rollback. Approving additional source later requires explicit removal
and re-enrollment; it creates a new device ID and old device-targeted policies no
longer apply. Keep the key and text outside the managed directory.

## Sign and apply policy

Create a private `payload.json` with exactly these fields. Use the real device ID
and approved package identity from enrollment. `issued_at` and `expires_at` are
integer UTC epoch seconds, with at most seven days between them. The device clock
must be correct; offline operation has no external time or revocation authority.

```json
{"format":"fleet-policy/v1","sequence":1,"cohort":"canary","devices":["REPLACE-WITH-DEVICE-UUID"],"package":"REPLACE-WITH-APPROVED-PACKAGE-SHA256","max_chars":20000,"enabled":true,"issued_at":1,"expires_at":2}
```

The placeholder document is intentionally not a valid current policy. Produce
real epoch values, for example using `python -c 'import time; print(int(time.time()))'`.
Sign with the separately held authority key, then transfer **only the policy**.

```sh
python scripts/fleet.py sign-policy --payload /private/fleet-admin/payload.json --key /private/fleet-admin/key.json --output /private/fleet-admin/policy.json
python scripts/fleet.py apply --root /private/device/fleet --policy /private/device/policy.json
python scripts/fleet.py inventory --root /private/device/fleet
python scripts/fleet.py resume --root /private/device/fleet
python scripts/fleet.py check --root /private/device/fleet
```

`check` reads UTF-8 text from stdin, up to 20,000 characters. It never executes
that text. The default output is brief. `--json` explicitly exports metadata
including subject hashes/spans that can link to the input; protect it accordingly.
No response text is retained in the device state or automatically uploaded.

Each apply first runs fixed synthetic clean/command-pattern probes against the
approved package. A broken package does not replace the active policy. These
probes check installation behavior, not representative accuracy.

## Rollout, pause, rollback and removal

`rollout --policy FILE --device-root ROOT ...` explicitly selects the enrolled
roots available to the current operator. It uses no hidden remote transport.
Use your existing authenticated administration channel for remote hosts, then
run the same local command there. Unavailable or wrong-cohort devices are
reported individually with a failing exit status. They are never created or
automatically enrolled. A canary policy cannot change a stable device.

Policy sequence must increase. To roll back, sign a **new** higher-sequence policy
selecting an already approved previous package. Replaying an old signature is
refused. Local `pause` wins over every organization policy; `resume` cannot enable
a disabled, expired, missing or unapproved policy. A failed/expired managed route
does not modify or disable the separate personal checker.

```sh
python scripts/fleet.py pause --root /private/device/fleet
python scripts/fleet.py remove --root /private/device/fleet --confirm-managed-removal
```

Inventory is an explicit local export: device ID, cohort, package, policy state
and at most 100 metadata events. No private key, text, subject hash or automatic
network destination is included. Removal verifies owned members, refuses foreign
files/links and removes only this enrolled directory. Reserved `.state-*` files
contain pending atomic state and are safely discarded after interruption; never
put your own files in this directory. A malicious same-user process or OS
administrator is outside this tool's security boundary.

Real employee consent, independent deployment/security review, stable browser
store distribution, service terms/provider identity and any paid activation
remain separate open organization obligations. No fleet policy can claim to
complete a personal tag's validation gate or require receipt issuance.
