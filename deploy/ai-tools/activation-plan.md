# Provider-host activation, 2026-11-21

This implements the operator-authorized deployment of the existing four routes
on `vps-18ef1326.vps.ovh.us`. It is a separate service namespace and does not
change the original tag validation or scope acceptance.

1. Verify public DNS from the external client, assigned host/socket/path absence,
   old staging `/healthz` and systemd/cgroup support. The server's `/etc/hosts`
   aliases its own hostname to loopback; that is not public DNS evidence.
2. Prepare ONLY the14 tracked runtime/notice/lock files from exact source commit
   `a5215149af23be51cd29f9b37ce1d85bdeff0c49`. Upload an explicit source manifest
   and generated exact config/units; no private worktree files. Create a new
   root-owned immutable release and its own hash-locked venv. Extract the exact
   apt-SHA-verified Caddy package privately; no global package installation.
3. `activate.py` defaults to a read-only plan. `--apply-reviewed` requires root,
   exact source/config/binary hashes, absent units/state and an absent owned
   firewall tag. Snapshot the existing file/rules first. Never execute the
   existing flush-containing nftables file.
4. Install ONLY the two new units with exclusive creation. Verify/start the
   loopback-only app. Before any public rule, `verify-isolation.py` requires
   actual cgroup limits, nonroot/no-capability/no-new-privilege process status,
   attached ingress+egress BPF and a bounded functional probe in the actual
   cgroup/mount namespace. The probe verifies blocked homes/source writes,
   permitted loopback and denied nonloopback connection to the owned primary's
   SSH port. It reads no home/database contents and sends no credentials.
5. Insert ONLY the tagged newTCP44340/s80-burst rule; preserve all old rules by
   handle and normalized definition. Atomically append its marked persistence
   command to the existing file after an exact-before check; do not load it.
   Start ONLY the new proxy. Trusted certificate issuance uses TLS-ALPN443;
   there is no new DNS, token, port80 or wildcard certificate.
6. From the external client prove trusted TLS/hostname, official modern+legacy
   MCP discovery/canonical checks, ordinary HTTP positive/no-finding, privacy
   and ingress refusals. Prove effective proxy limits and both services'
   ownership. Check real cancel/reap and stop/recovery without touching other
   services. Retain exact source/config/unit/firewall and certificate public
   metadata; do not copy private key/state or request logs.
7. Only after actual public proof, `--finalize-after-proof` enables the two new
   units. Root-owned activation records retain the exact release and rule
   handle. State-only service health replaces request logging.

On unsafe failure, stop that mutation and use `--rollback RECORD`: stop/disable
ONLY newly installed API units, remove ONLY the owned rule handle/tag, restore
only the exactly matching owned persistence addition, and remove only the exact
new unit files after their hashes match. Keep the release and private snapshots
for review. Never flush/reload firewall rules or remove shared parent paths.
An unexpected file/rule mutation refuses rollback for review rather than
removing someone else's changes.

Limits: the functional namespace probe is not a duplicate of every execution
restriction. Actual cgroup files, service process status and mounts are separate
evidence. Hosting does not bypass host-AI workspace connector policy and does
not make PS independently validated or remote PII available.

Primary reference for the actual host's systemd257 IP/BPF/resource controls:
https://www.freedesktop.org/software/systemd/man/257/systemd.resource-control.html
