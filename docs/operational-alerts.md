# Operational alerts and owner recovery

## Implemented boundary

The owner approved private, self-hosted ntfy at `https://notify.aitrustid.com`.
The DNS-only A record points to the independent backup host. Caddy terminates
verified HTTPS; ntfy binds only to loopback. PostgreSQL remains socket-only.
No public application intake, research forwarding or public community service is
connected by this change. The tag catalogue remains a local preview.

Each host has a distinct publish-only account for its operational topic. The
owner's account reads both topics and cannot publish. Default access is deny-all.
Anonymous reads/publishing, cross-topic publishing, publisher reads, reader
publishing and unrelated-topic reads were denied in executed checks. Both hosts'
real heartbeats were read over HTTPS and observed in the signed-in Chrome UI.

ntfy and Caddy use separate unprivileged service identities and filesystem
sandboxes. ntfy cannot read the database, backup credentials or protected recovery
copies. Signups, attachments and upstream forwarding are disabled. Cached brief
messages expire after 24 hours. Memory, CPU, request body size, request rate,
subscriptions and daily message volume are bounded. Administrator/root or
provider compromise remains outside these service-account protections.

The Python standard-library sender runs as the dedicated `ait-alert` identity.
Root-only source credentials are supplied through systemd LoadCredential. Its
reader permits ordinary 0400/0600 files or the exact root-owned 0440 file within
systemd's root-owned private `/run/credentials/<unit>` directory; group/other
access outside that boundary is rejected. Redirects are rejected before a bearer
token could be forwarded. SMTP requires certificate-verified TLS before login.
The service cannot read PostgreSQL, pgBackRest credentials or protected copies.

Messages contain a host role, UTC time and approved unit identifiers. They never
include response text, database rows, keys, SMTP replies or raw journals. Failed
delivery does not advance sent state. Five-minute timers inspect approved units;
changed incidents send immediately, unchanged incidents repeat hourly, recovery
sends after an incident and healthy heartbeats send daily. A test does not advance
operational state. Both HTTPS timers are enabled; their executed service result
and next scheduled activation were verified.

## Email channel

OVH completed verified STARTTLS and iCloud accepted a real test to
`admin@aitrustid.com`. The owner supplied an inbox screenshot confirming the test arrived. The primary
email service and independent five-minute timer are enabled; successful execution
and its next scheduled activation were verified. Email
has separate state so an HTTPS success cannot suppress an email notification.
The DigitalOcean host cannot use iCloud SMTP: its connection timed out, consistent
with the provider's restriction on ports 25, 465 and 587. It uses HTTPS instead.

iCloud's app-specific credential may grant more mail access than sending. It stays
outside Git, root-only on the primary host, with service access through systemd's
private credential mount. Apple account password changes revoke app passwords.

## Verified custody and remaining limitations

OVH has a registered security key and backup codes. DigitalOcean uses GitHub
sign-in; GitHub's authenticator MFA and passkey are configured. These observations
verify configuration, not recovery-code custody or a lost-device exercise.

The existing repository cipher and base64-encoded backup administrator key were
saved into two named Apple Passwords records. Their saved, masked UI entries were
verified. Retrieval/byte-for-byte restoration was not tested. An independent
offline copy and full replacement-host recovery drill remain open.

The owner's Chrome notification dashboard has both topic subscriptions and shows
both host heartbeats. Desktop permission and separate-device delivery must be
verified before claiming unattended reception. Keeping `upstream-base-url` empty
avoids forwarding to another service; self-hosted iOS reception may be delayed.

A host cannot notify while powered off. The notification endpoint shares the
backup host, so losing that host also loses HTTPS notification delivery. Primary
SMTP provides a separately verified and enabled transport, but
there is no independent external uptime observer. Missing daily heartbeats need
human attention. This implementation does not establish high availability or a
blanket security guarantee. Real data collection remains disabled.

## Build, deploy and verify

- Local: `make alerts-build notifications-build`; shellcheck the four shell scripts
  in `deploy/alerts` and `deploy/notifications`.
- Deployment: use a root-only staging directory containing the reviewed source
  pair; execute `bash deploy/alerts/install.sh primary` or `backup` as root on the
  intended host. It does not initially enable timers. The primary email unit is
  prepared only when its private SMTP credential already exists.
- Notification edge: execute `prepare-edge.sh`; provision topic identities using
  `provision.py`, capturing its output into a private file outside Git. After the
  owner-approved DNS resolves to the intended host, execute `activate-edge.sh`
  with that host's `AITRUST_NOTIFY_IPV4`. It preserves the previous firewall file
  at `/var/lib/aitrust-id/notification-rollback/nftables.conf`.
- Local authorization: `sudo python3 deploy/notifications/verify-local.py` on the
  backup host. External authorization: run the same script with `--https` and
  `--credentials` pointing to the private provisioning JSON outside Git. Its
  report contains only check labels/statuses, never credentials or bodies.
- Live sender: `sudo systemctl start aitrust-alerts.service`; verify its result and
  authenticated topic receipt before `sudo systemctl enable --now aitrust-alerts.timer`.
- Primary email: test through systemd with the reviewed LoadCredential sandbox;
  confirm the owner's inbox before enabling `aitrust-email-alerts.timer`.
- Inspect failures privately with `sudo journalctl -u aitrust-alerts` or
  `-u aitrust-email-alerts`. Never publish unsanitized journals.
- Rollback: disable the relevant alert timers; stop Caddy/ntfy; validate and restore
  the saved firewall file with nft; remove only the `notify` DNS record. This
  reverses this endpoint without changing database, SSH or backup policies.

## Evidence

- `runs/2026-10-08-notification-local-authorization.json`: 10 loopback ACL checks.
- `runs/2026-10-08-notification-https-authorization.json`: 12 external HTTPS checks,
  including both actual host heartbeats.
- `runs/2026-10-08-notification-runtime-security.json`: runtime boundaries,
  scheduled checks and deployed sender source hash.
- `runs/2026-10-08-operational-email-test.json`: iCloud acceptance, not inbox proof.
- `runs/2026-10-08-notification-timers.json`: enabled HTTPS timers.
- `runs/2026-10-08-owner-recovery-and-alerts-result.json`: current aggregate truth.

Sources: [ntfy access control](https://docs.ntfy.sh/config/#access-control),
[ntfy installation](https://docs.ntfy.sh/install/),
[DigitalOcean SMTP restrictions](https://docs.digitalocean.com/support/why-is-smtp-blocked/),
[DigitalOcean federated MFA](https://docs.digitalocean.com/platform/accounts/2fa/),
[iCloud SMTP](https://support.apple.com/en-us/102525),
[Apple app-specific passwords](https://support.apple.com/en-us/102654).
