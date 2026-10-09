#!/usr/bin/env bash
set -Eeuo pipefail
[[ $EUID -eq 0 ]] || exit 1
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
install -o root -g caddy -m 0640 Caddyfile /etc/caddy/Caddyfile
caddy validate --config /etc/caddy/Caddyfile
install -d -m 0755 /etc/systemd/system/caddy.service.d
cat > /etc/systemd/system/caddy.service.d/aitrust.conf <<'UNIT'
[Service]
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/var/lib/caddy
InaccessiblePaths=-/etc/pgbackrest -/var/lib/postgresql -/var/lib/pgbackrest -/var/lib/aitrust-id/protected -/etc/ntfy -/var/lib/ntfy -/var/cache/ntfy
MemoryMax=192M
CPUQuota=25%
UNIT
systemctl daemon-reload
systemd-analyze verify caddy.service ntfy.service
# No external ports are opened here. DNS and separate exposure checks required.
echo 'Edge validated; service activation unchanged. No public firewall rules changed.'
