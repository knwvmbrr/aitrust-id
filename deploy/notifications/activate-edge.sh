#!/usr/bin/env bash
# Run only after the owner-approved notification DNS resolves to this host.
set -Eeuo pipefail
[[ $EUID -eq 0 ]] || exit 1
expected=${AITRUST_NOTIFY_IPV4:?Approved notification IPv4 required}
getent ahostsv4 notify.aitrustid.com | awk '{print $1}' | sort -u | awk -v expected="$expected" 'BEGIN { ok=0 } $0==expected {ok=1} END {exit !ok}'
caddy validate --config /etc/caddy/Caddyfile
install -d -m 0700 /var/lib/aitrust-id/notification-rollback
[[ -f /var/lib/aitrust-id/notification-rollback/nftables.conf ]] || cp -p /etc/nftables.conf /var/lib/aitrust-id/notification-rollback/nftables.conf
if ! grep -Fq 'tcp dport { 80, 443 }' /etc/nftables.conf; then
  sed '/tcp dport 22/i\    tcp dport { 80, 443 } ct state new accept' /etc/nftables.conf > /etc/nftables.conf.new
  chmod 0600 /etc/nftables.conf.new
  nft --check --file /etc/nftables.conf.new
  mv /etc/nftables.conf.new /etc/nftables.conf
fi
nft --file /etc/nftables.conf
systemctl enable --now caddy
systemctl is-active caddy ntfy
