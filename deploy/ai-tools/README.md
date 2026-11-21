# Remote connector deployment preparation

This is a separate PS-only service. It does not replace the website, database,
notification service, existing containers or local privacy checker. Preparation
is not public deployment, TLS issuance, account integration or tag validation.

## Plan and risk boundary

The assigned hostname is `vps-18ef1326.vps.ovh.us`; no new DNS record is needed
for that hostname. `api.aitrustid.com` is not configured by these files.
The only accepted application routes are POST `/mcp`, POST `/v1/check`, GET
`/v1/tags`, and GET `/healthz`. No authentication credentials are accepted or
forwarded. Absence of Origin permits server clients; any Origin is refused
until an exact origin is separately configured in the application and proxy.
The provider-host configuration intentionally has no browser CORS grant.

A new immutable release and private virtualenv contain only selected tracked
sources and the existing hash-locked optional MCP environment. The application
listens on IPv4 loopback port8790. Separate DynamicUser services avoid an
interactive login account, protect homes and system files, limit CPU/memory/tasks
and kill the service control group on stop. The application's IP policy allows
loopback only. These unit settings must be accepted and their effective runtime
properties checked on the actual host before publication; rendering or
`systemd-analyze verify` alone does not prove an enforced sandbox.

The separate Caddy process uses the exact Debian backport package2.11.2-1~bpo13+1,
verified against current signed apt metadata before extraction. No global
package installation is required. The proxy has no admin endpoint, persisted
configuration, access logging or request/error logging. It rejects query,
credentials, compression, transfer framing and unexpected methods/paths with a
fixed response; the application repeats its own validation. Caddy may normalize
wire headers before proxying, so actual ingress refusal controls are required.

Production HTTPS needs trusted certificate issuance and public TCP443 reachability;
TCP80 is needed only if HTTP challenge/redirect is chosen. The prepared TLS
configuration disables redirects and HTTP challenge and uses TLS-ALPN on443.
No port, firewall, global unit, user, existing server configuration or DNS change
is performed by the prepare script or loopback verifier. No existing nftables
rules are flushed. Caddy ACME egress is a separate proxy permission; the
application has no need for outbound internet, database or home access.

## Preparation, review, activation

Use `prepare.py --help`. It creates a NEW exclusive destination, never adopts or
overwrites an existing directory, and accepts an exact Git commit. It writes
selected sources, a release-source manifest, rendered unit/config candidates
and an activation plan. Optional venv provisioning uses only the existing
hash-locked binary-wheel cohort from official PyPI. Preparation does not invoke
systemctl, change users, write `/etc`, install packages or change firewall rules.
Its failure leaves the private candidate available for inspection; remove only
that explicitly owned directory after collecting evidence.

After independent source/config/loopback proof, the operator must review the
activation plan and reserve the exact new `/opt/aitrustid-ai-tools` namespace.
Copy the reviewed release to its exact SHA path, place the reviewed extracted
Caddy binary at the release path, install ONLY the two new unit filenames with
exclusive creation, run `systemd-analyze verify`, then daemon-reload/start those
two units. Before start, snapshot the new namespace's absence and the current
firewall/unit inventory. A collision with any existing path/unit is a refusal,
not an invitation to replace it. Do not replace the host's existing Caddy or
container service. Open only the separately reviewed TCP443 rule in the
existing firewall table, preserving all other rules and SSH access.

Rollback: close ONLY that newly added443 rule by its recorded handle, stop and
disable ONLY `aitrustid-ai-tools.service` and `aitrustid-ai-tools-proxy.service`,
remove ONLY their exact newly created unit files, daemon-reload, and retain or
remove the exact reviewed release after collecting fixed operational evidence.
No recursive deletion of a shared parent or flush of network rules is allowed.
Certificate state belongs only to the new proxy state directory; it is sensitive
and is not source-code or proof material. A previous release is never deleted
by preparation.

Before announcing public service: require effective unit limits/network policy,
trusted HTTPS chain and exact host, real official MCP client discovery/check,
HTTP positive/no-finding/refusal/recovery, disconnect/shutdown child reaping,
no submitted-text logs, and prior service health. Provider-domain availability
is independent of ChatGPT/Claude workspace approval and connector policies.

Official configuration references:
- https://caddyserver.com/docs/caddyfile/options
- https://caddyserver.com/docs/caddyfile/directives/reverse_proxy
- https://caddyserver.com/docs/caddyfile/directives/request_body
- https://caddyserver.com/docs/caddyfile/directives/tls

The prepared release directory is private0700. At activation, the operator
makes ONLY the reviewed public-code/config/venv release traversable and readable
by the two dynamic service users (directories0755, public files0644,
executables0755), keeping proxy certificate state0700. Root owns release code;
service users must not modify it. Do not copy any private runtime `.env`, keys,
account files or local worktree extras. The app has no state directory and
`MemorySwapMax=0`; effective swap and BPF network restrictions require the
operator's actual systemd runtime check. Host-wide swap policy is untouched.

If80/443 are approved together, insert ONLY a tagged new-TCP connection rule
with a40/second,80-burst limit before the existing input drop; retain established
traffic and SSH22. Record the exact rule handle. Do not reload or flush the
ruleset or container tables. Persistent configuration edits require a prior
snapshot and an atomic, separately reviewed addition to the existing file.
Neither candidate preparation nor its proof performs this action.
