#!/usr/bin/env bash
set -Eeuo pipefail
[[ $EUID -eq 0 ]] || { echo 'Run as root.' >&2; exit 1; }
python3 /opt/aitrust-id/backup/source-health.py
cat > /etc/systemd/system/aitrust-source-backup-health.service <<'EOF'
[Unit]
Description=AI Trust ID source archive and disk reserve checks
OnFailure=aitrust-source-backup-failure.service
[Service]
Type=oneshot
ExecStart=/usr/bin/python3 /opt/aitrust-id/backup/source-health.py
UMask=0077
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=read-only
EOF
cat > /etc/systemd/system/aitrust-source-backup-health.timer <<'EOF'
[Unit]
Description=Check source WAL and disk every five minutes
[Timer]
OnBootSec=3min
OnUnitActiveSec=5min
Unit=aitrust-source-backup-health.service
[Install]
WantedBy=timers.target
EOF
cat > /etc/systemd/system/aitrust-source-backup-failure.service <<'EOF'
[Unit]
Description=Record source backup failure (external delivery not configured)
[Service]
Type=oneshot
ExecStart=/usr/bin/logger -p daemon.err AI-Trust-ID-source-backup-failure-inspect-source-health
EOF
chmod 0644 /etc/systemd/system/aitrust-source-backup-{health,failure}.service /etc/systemd/system/aitrust-source-backup-health.timer
systemd-analyze verify /etc/systemd/system/aitrust-source-backup-{health,failure}.service /etc/systemd/system/aitrust-source-backup-health.timer
systemctl daemon-reload
systemctl start aitrust-source-backup-health.service
systemctl enable --now aitrust-source-backup-health.timer
