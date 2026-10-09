#!/usr/bin/env bash
# Empty, dedicated backup VPS only. Secret configuration is deployed separately.
set -Eeuo pipefail
umask 027
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
[[ $EUID -eq 0 ]] || { echo 'Requires root.' >&2; exit 1; }
source /etc/os-release
[[ $ID == debian && $VERSION_ID == 13 ]] || { echo 'Requires Debian 13.' >&2; exit 1; }
[[ -s admin.pub ]] || { echo 'Dedicated admin public key required.' >&2; exit 1; }
install -d -m 0700 /var/lib/aitrust-id/backup-rollback
if [[ ! -e /var/lib/aitrust-id/backup-rollback/baseline.saved ]]; then
  cp -a /etc/ssh/sshd_config /etc/ssh/sshd_config.d /var/lib/aitrust-id/backup-rollback/
  [[ ! -f /etc/nftables.conf ]] || cp -a /etc/nftables.conf /var/lib/aitrust-id/backup-rollback/
  date -u +%FT%TZ > /var/lib/aitrust-id/backup-rollback/baseline.saved
fi
id ait-backup-admin >/dev/null 2>&1 || useradd --create-home --shell /bin/bash ait-backup-admin
install -d -o ait-backup-admin -g ait-backup-admin -m 0700 /home/ait-backup-admin/.ssh
install -o ait-backup-admin -g ait-backup-admin -m 0600 admin.pub /home/ait-backup-admin/.ssh/authorized_keys
# '*' cannot authenticate by password and does not mark the pubkey account locked.
usermod --password '*' ait-backup-admin
printf 'ait-backup-admin ALL=(ALL:ALL) NOPASSWD: ALL\n' > /etc/sudoers.d/ait-backup-admin
chmod 0440 /etc/sudoers.d/ait-backup-admin
visudo --check --file /etc/sudoers.d/ait-backup-admin
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get -y -o Dpkg::Options::=--force-confold full-upgrade
apt-get -y install ca-certificates curl gnupg nftables unattended-upgrades postgresql-common python3 shellcheck rsync
install -d /usr/share/postgresql-common/pgdg
curl --fail --silent --show-error --proto '=https' --tlsv1.2 \
  https://www.postgresql.org/media/keys/ACCC4CF8.asc -o /usr/share/postgresql-common/pgdg/apt.postgresql.org.asc
fingerprint=$(gpg --show-keys --with-colons /usr/share/postgresql-common/pgdg/apt.postgresql.org.asc | awk -F: '$1=="fpr" { print $10; exit }')
[[ $fingerprint == B97B0AFCAA1A47F044F244A07FCC7D46ACCC4CF8 ]] || { echo 'Signing key mismatch.' >&2; exit 1; }
cat > /etc/apt/sources.list.d/pgdg.sources <<'EOF'
Types: deb
URIs: https://apt.postgresql.org/pub/repos/apt
Suites: trixie-pgdg
Architectures: amd64
Components: main
Signed-By: /usr/share/postgresql-common/pgdg/apt.postgresql.org.asc
EOF
chmod 0644 /etc/apt/sources.list.d/pgdg.sources
printf '\ncreate_main_cluster = false\n' >> /etc/postgresql-common/createcluster.conf
apt-get update
apt-get -y install postgresql-18 postgresql-client-18 pgbackrest
dpkg --compare-versions "$(pgbackrest version | awk '{print $2}')" ge 2.59.3
id pgbackrest >/dev/null 2>&1 || useradd --create-home --shell /bin/bash pgbackrest
usermod --password '*' pgbackrest
install -d -o pgbackrest -g pgbackrest -m 0700 /home/pgbackrest/.ssh /var/lib/pgbackrest /var/log/pgbackrest
install -d -o root -g root -m 0700 /var/lib/aitrust-id/protected /var/lib/aitrust-id/backup-status
install -d -o root -g root -m 0755 /opt/aitrust-id/backup
install -m 0755 remote.py /opt/aitrust-id/backup/remote.py
install -m 0755 cycle.py /opt/aitrust-id/backup/cycle.py
install -m 0755 verify.py /opt/aitrust-id/backup/verify.py
install -m 0755 restore.py /opt/aitrust-id/backup/restore.py
install -m 0755 negative-checks.py /opt/aitrust-id/backup/negative-checks.py
cat > /etc/logrotate.d/pgbackrest <<'EOF'
/var/log/pgbackrest/*.log {
    weekly
    rotate 4
    compress
    missingok
    notifempty
    su pgbackrest pgbackrest
}
EOF
chmod 0644 /etc/logrotate.d/pgbackrest
install -d -m 0755 /etc/systemd/resolved.conf.d
printf '[Resolve]\nLLMNR=no\nMulticastDNS=no\n' > /etc/systemd/resolved.conf.d/aitrust-id.conf
chmod 0644 /etc/systemd/resolved.conf.d/aitrust-id.conf
systemctl restart systemd-resolved
sed 's/AllowUsers debian/AllowUsers ait-backup-admin pgbackrest/' ../host/sshd.conf > /etc/ssh/sshd_config.d/00-aitrust-id.conf
chmod 0644 /etc/ssh/sshd_config.d/00-aitrust-id.conf
sshd -t
systemctl reload ssh
install -m 0600 ../host/nftables.conf /etc/nftables.conf
nft --check --file /etc/nftables.conf
systemctl enable --now nftables
systemctl restart nftables
cat > /etc/apt/apt.conf.d/52aitrust-id-unattended <<'EOF'
Unattended-Upgrade::Origins-Pattern {
  "origin=Debian,codename=trixie-security,label=Debian-Security";
  "origin=apt.postgresql.org,codename=trixie-pgdg";
};
Unattended-Upgrade::Automatic-Reboot "false";
APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Unattended-Upgrade "1";
EOF
chmod 0644 /etc/apt/apt.conf.d/52aitrust-id-unattended
systemctl enable --now apt-daily.timer apt-daily-upgrade.timer
install -d -m 0755 /etc/systemd/journald.conf.d
printf '[Journal]\nStorage=persistent\nSystemMaxUse=256M\nRuntimeMaxUse=64M\n' > /etc/systemd/journald.conf.d/aitrust-id.conf
chmod 0644 /etc/systemd/journald.conf.d/aitrust-id.conf
systemctl restart systemd-journald
echo 'Baseline applied; verify fresh non-root administrator access.'
