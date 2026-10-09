#!/usr/bin/env bash
# Dedicated backup host: local-only notification pilot before DNS/HTTPS exposure.
set -Eeuo pipefail
[[ $EUID -eq 0 ]] || { echo 'Run as root.' >&2; exit 1; }
export DEBIAN_FRONTEND=noninteractive
install -d -m 0755 /etc/apt/keyrings
curl --fail --silent --show-error --proto '=https' --tlsv1.2 https://archive.ntfy.sh/apt/keyring.gpg -o /etc/apt/keyrings/ntfy.gpg
fingerprint=$(gpg --show-keys --with-colons /etc/apt/keyrings/ntfy.gpg | awk -F: '$1=="fpr" { print $10; exit }')
[[ $fingerprint == 55BA774A6F5EE67431E4B6B7CFDB962D4F1EC4AF ]] || { echo 'ntfy signing identity mismatch.' >&2; exit 1; }
chmod 0644 /etc/apt/keyrings/ntfy.gpg
printf '%s\n' 'deb [arch=amd64 signed-by=/etc/apt/keyrings/ntfy.gpg] https://archive.ntfy.sh/apt stable main' > /etc/apt/sources.list.d/ntfy.list
apt-get update
apt-get -y install ntfy caddy libnss-systemd
systemctl stop ntfy caddy
id ntfy >/dev/null 2>&1 || useradd --system --home-dir /var/lib/ntfy --shell /usr/sbin/nologin ntfy
install -d -o ntfy -g ntfy -m 0700 /var/lib/ntfy /var/cache/ntfy
install -d -o root -g ntfy -m 0750 /etc/ntfy
cat > /etc/ntfy/server.yml <<'CONFIG'
base-url: "https://notify.aitrustid.com"
listen-http: "127.0.0.1:2586"
auth-file: "/var/lib/ntfy/user.db"
auth-default-access: "deny-all"
cache-file: "/var/cache/ntfy/cache.db"
cache-duration: "24h"
behind-proxy: true
enable-signup: false
enable-login: true
enable-reservations: false
upstream-base-url: ""
visitor-request-limit-burst: 30
visitor-request-limit-replenish: "10s"
visitor-message-daily-limit: 200
visitor-subscription-limit: 5
global-topic-limit: 10
log-level: "warn"
CONFIG
chown root:ntfy /etc/ntfy/server.yml
chmod 0640 /etc/ntfy/server.yml
install -d -m 0755 /etc/systemd/system/ntfy.service.d
cat > /etc/systemd/system/ntfy.service.d/aitrust.conf <<'UNIT'
[Service]
User=ntfy
Group=ntfy
UMask=0077
NoNewPrivileges=true
PrivateTmp=true
PrivateDevices=true
ProtectSystem=strict
ProtectHome=true
ProtectKernelTunables=true
ProtectKernelModules=true
ProtectControlGroups=true
ReadWritePaths=/var/lib/ntfy /var/cache/ntfy
InaccessiblePaths=-/etc/pgbackrest -/var/lib/postgresql -/var/lib/pgbackrest -/var/lib/aitrust-id/protected
RestrictAddressFamilies=AF_UNIX AF_INET AF_INET6
MemoryMax=192M
CPUQuota=25%
UNIT
systemctl daemon-reload
systemctl enable --now ntfy
curl --fail --silent --retry 10 --retry-connrefused --retry-delay 1 http://127.0.0.1:2586/v1/health
ntfy --version
ntfy user add --help
ntfy token add --help
