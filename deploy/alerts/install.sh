#!/usr/bin/env bash
set -Eeuo pipefail
[[ $EUID -eq 0 ]] || { echo 'Run as root.' >&2; exit 1; }
role=${1:?primary or backup required}
[[ $role == primary || $role == backup ]] || exit 1
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
# A stable unprivileged identity works with minimal-image D-Bus policy.
id ait-alert >/dev/null 2>&1 || useradd --system --no-create-home --shell /usr/sbin/nologin ait-alert
install -d -o root -g root -m 0755 /opt/aitrust-id/alerts
install -d -o root -g root -m 0700 /etc/aitrust-id/alerts
install -o root -g root -m 0755 alerts.py /opt/aitrust-id/alerts/alerts.py
cat > /etc/systemd/system/aitrust-alerts.service <<UNIT
[Unit]
Description=AI Trust ID bounded operational HTTPS alerts
After=network-online.target
Wants=network-online.target
[Service]
Type=oneshot
User=ait-alert
Group=ait-alert
StateDirectory=aitrust-alerts
StateDirectoryMode=0700
LoadCredential=delivery.json:/etc/aitrust-id/alerts/ntfy.json
ExecStart=/usr/bin/python3 /opt/aitrust-id/alerts/alerts.py --role $role
TimeoutStartSec=150
UMask=0077
NoNewPrivileges=true
PrivateTmp=true
PrivateDevices=true
ProtectSystem=strict
ProtectHome=true
ProtectKernelTunables=true
ProtectKernelModules=true
ProtectControlGroups=true
RestrictSUIDSGID=true
RestrictAddressFamilies=AF_UNIX AF_INET AF_INET6
InaccessiblePaths=-/etc/pgbackrest -/var/lib/postgresql -/var/lib/pgbackrest -/var/lib/aitrust-id/protected
UNIT
cat > /etc/systemd/system/aitrust-alerts.timer <<'UNIT'
[Unit]
Description=Retry operational notifications every five minutes
[Timer]
OnBootSec=2min
OnUnitActiveSec=5min
Unit=aitrust-alerts.service
[Install]
WantedBy=timers.target
UNIT
chmod 0644 /etc/systemd/system/aitrust-alerts.{service,timer}
systemd-analyze verify /etc/systemd/system/aitrust-alerts.{service,timer}
if [[ $role == primary && -f /etc/aitrust-id/alerts/smtp.json ]]; then
  # Independent channel state: an HTTPS success must never suppress email.
  sed -e 's/bounded operational HTTPS alerts/bounded operational email alerts/' \
      -e 's/StateDirectory=aitrust-alerts$/StateDirectory=aitrust-email-alerts/' \
      -e 's@/alerts/ntfy.json@/alerts/smtp.json@' \
      /etc/systemd/system/aitrust-alerts.service > /etc/systemd/system/aitrust-email-alerts.service
  sed -e 's/Unit=aitrust-alerts.service/Unit=aitrust-email-alerts.service/' \
      -e 's/operational notifications/operational email/' \
      /etc/systemd/system/aitrust-alerts.timer > /etc/systemd/system/aitrust-email-alerts.timer
  chmod 0644 /etc/systemd/system/aitrust-email-alerts.{service,timer}
  systemd-analyze verify /etc/systemd/system/aitrust-email-alerts.{service,timer}
fi
systemctl daemon-reload
python3 /opt/aitrust-id/alerts/alerts.py --role "$role" --inspect
echo 'Units prepared; timer enablement unchanged. No email sent. Delivery test required before initial enablement.'
