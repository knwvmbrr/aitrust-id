#!/usr/bin/env bash
# Run on the repository after a successful initial protected restore drill.
set -Eeuo pipefail
[[ $EUID -eq 0 ]] || { echo 'Run as root.' >&2; exit 1; }
[[ -s /var/lib/aitrust-id/backup-status/last-success.json ]] || { echo 'Initial protected generation required.' >&2; exit 1; }
python3 /opt/aitrust-id/backup/verify.py
for mode in backup protect; do
  cat > "/etc/systemd/system/aitrust-$mode.service" <<EOF
[Unit]
Description=AI Trust ID encrypted $mode cycle
After=network-online.target
Wants=network-online.target
OnFailure=aitrust-backup-failure.service
[Service]
Type=oneshot
ExecStart=/usr/bin/python3 /opt/aitrust-id/backup/cycle.py $mode
TimeoutStartSec=3600
UMask=0077
NoNewPrivileges=true
PrivateTmp=true
PrivateDevices=true
ProtectSystem=strict
ProtectHome=read-only
ReadWritePaths=/var/lib/pgbackrest /var/lib/aitrust-id/protected /var/lib/aitrust-id/backup-status /var/log/pgbackrest
RestrictAddressFamilies=AF_UNIX AF_INET AF_INET6
EOF
done
cat > /etc/systemd/system/aitrust-backup.timer <<'EOF'
[Unit]
Description=Daily AI Trust ID backup (weekly full, other days differential)
[Timer]
OnCalendar=*-*-* 03:00:00 UTC
Persistent=true
RandomizedDelaySec=300
Unit=aitrust-backup.service
[Install]
WantedBy=timers.target
EOF
cat > /etc/systemd/system/aitrust-protect.timer <<'EOF'
[Unit]
Description=Verify and protect encrypted repository every 15 minutes
[Timer]
OnCalendar=*-*-* *:00/15:00 UTC
Persistent=true
Unit=aitrust-protect.service
[Install]
WantedBy=timers.target
EOF
cat > /etc/systemd/system/aitrust-backup-health.service <<'EOF'
[Unit]
Description=AI Trust ID backup age and capacity checks
OnFailure=aitrust-backup-failure.service
[Service]
Type=oneshot
ExecStart=/usr/bin/python3 /opt/aitrust-id/backup/verify.py
UMask=0077
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=read-only
EOF
cat > /etc/systemd/system/aitrust-backup-health.timer <<'EOF'
[Unit]
Description=Check AI Trust ID backup health every ten minutes
[Timer]
OnBootSec=5min
OnUnitActiveSec=10min
Unit=aitrust-backup-health.service
[Install]
WantedBy=timers.target
EOF
cat > /etc/systemd/system/aitrust-backup-failure.service <<'EOF'
[Unit]
Description=Record AI Trust ID backup failure (external delivery not configured)
[Service]
Type=oneshot
ExecStart=/usr/bin/logger -p daemon.err AI-Trust-ID-backup-failure-inspect-failed-systemd-units
EOF
chmod 0644 /etc/systemd/system/aitrust-{backup,protect,backup-health,backup-failure}.service /etc/systemd/system/aitrust-{backup,protect,backup-health}.timer
systemd-analyze verify /etc/systemd/system/aitrust-{backup,protect,backup-health,backup-failure}.service /etc/systemd/system/aitrust-{backup,protect,backup-health}.timer
systemctl daemon-reload
systemctl start aitrust-backup.service
systemctl start aitrust-protect.service
systemctl start aitrust-backup-health.service
systemctl enable --now aitrust-backup.timer aitrust-protect.timer aitrust-backup-health.timer
echo 'Backup, protected generation and local health timers enabled; external notification delivery remains unconfigured.'
