#!/usr/bin/env bash
# Dedicated Debian 13 host only. Run from an authenticated, independently checked
# SSH session. PostgreSQL remains socket-only; this does not deploy public intake.
set -Eeuo pipefail
umask 027
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
[[ $EUID -eq 0 ]] || { echo 'Run with sudo.' >&2; exit 1; }
source /etc/os-release
[[ $ID == debian && $VERSION_ID == 13 ]] || { echo 'Requires Debian 13.' >&2; exit 1; }
[[ -s /home/debian/.ssh/authorized_keys ]] || { echo 'Admin key required.' >&2; exit 1; }
install -d -m 0700 /var/lib/aitrust-id/host-rollback
rollback=/var/lib/aitrust-id/host-rollback
if [[ ! -f $rollback/baseline.saved ]]; then
  cp -a /etc/ssh/sshd_config "$rollback/sshd_config"
  cp -a /etc/ssh/sshd_config.d "$rollback/sshd_config.d"
  [[ ! -f /etc/nftables.conf ]] || cp -a /etc/nftables.conf "$rollback/nftables.conf"
  date -u +%FT%TZ > "$rollback/baseline.saved"
fi
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get -y -o Dpkg::Options::=--force-confold full-upgrade
apt-get -y install ca-certificates curl gnupg nftables unattended-upgrades \
  postgresql-common python3 shellcheck wireguard-tools
install -d /usr/share/postgresql-common/pgdg
curl --fail --silent --show-error --proto '=https' --tlsv1.2 \
  https://www.postgresql.org/media/keys/ACCC4CF8.asc \
  -o /usr/share/postgresql-common/pgdg/apt.postgresql.org.asc
fingerprint=$(gpg --show-keys --with-colons /usr/share/postgresql-common/pgdg/apt.postgresql.org.asc | awk -F: '$1=="fpr" { print $10; exit }')
[[ $fingerprint == B97B0AFCAA1A47F044F244A07FCC7D46ACCC4CF8 ]] || { echo 'PGDG signing key mismatch.' >&2; exit 1; }
cat > /etc/apt/sources.list.d/pgdg.sources <<'EOF'
Types: deb
URIs: https://apt.postgresql.org/pub/repos/apt
Suites: trixie-pgdg
Architectures: amd64
Components: main
Signed-By: /usr/share/postgresql-common/pgdg/apt.postgresql.org.asc
EOF
chmod 0644 /etc/apt/sources.list.d/pgdg.sources
# Do not let package installation create/start a default network listener.
if ! pg_lsclusters --no-header | awk '{print $1}' | grep -qx 18; then
  printf '\ncreate_main_cluster = false\n' >> /etc/postgresql-common/createcluster.conf
fi
apt-get update
apt-get -y install postgresql-18 postgresql-client-18 pgbackrest
backup_version=$(pgbackrest version | awk '{print $2}')
dpkg --compare-versions "$backup_version" ge 2.59.3 || { echo 'Patched pgBackRest >=2.59.3 required.' >&2; exit 1; }
for account in ait-intake ait-review ait-analysis; do
  if ! id "$account" >/dev/null 2>&1; then
    useradd --system --user-group --no-create-home --shell /usr/sbin/nologin "$account"
  fi
done
if ! pg_lsclusters --no-header | awk '{print $1, $2}' | grep -qx '18 main'; then
  pg_createcluster 18 main --start-conf=auto -- --data-checksums --auth-local=peer --auth-host=scram-sha-256
fi
install -d /etc/postgresql/18/main/conf.d
install -o postgres -g postgres -m 0640 postgresql.conf /etc/postgresql/18/main/conf.d/aitrust-id.conf
install -o postgres -g postgres -m 0640 pg_hba.conf /etc/postgresql/18/main/pg_hba.conf
install -o postgres -g postgres -m 0640 pg_ident.conf /etc/postgresql/18/main/pg_ident.conf
systemctl enable postgresql@18-main.service
systemctl restart postgresql@18-main.service
runuser -u postgres -- psql --no-psqlrc --set ON_ERROR_STOP=1 < roles.sql
install -d -m 0755 /etc/systemd/resolved.conf.d
cat > /etc/systemd/resolved.conf.d/aitrust-id.conf <<'EOF'
[Resolve]
LLMNR=no
MulticastDNS=no
EOF
# resolved drops privileges and must be able to read its non-secret config.
chmod 0644 /etc/systemd/resolved.conf.d/aitrust-id.conf
systemctl restart systemd-resolved.service
install -m 0644 sshd.conf /etc/ssh/sshd_config.d/00-aitrust-id.conf
sshd -t
systemctl reload ssh.service
# Restrict both IPv4 and IPv6; preserve SSH, DHCP renewal and path-MTU discovery.
install -m 0600 nftables.conf /etc/nftables.conf
nft --check --file /etc/nftables.conf
systemctl enable nftables.service
systemctl restart nftables.service
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
install -d -m 0755 /opt/aitrust-id/host
install -m 0755 verify.py /opt/aitrust-id/host/verify.py
install -d -m 0755 /etc/systemd/journald.conf.d
cat > /etc/systemd/journald.conf.d/aitrust-id.conf <<'EOF'
[Journal]
Storage=persistent
SystemMaxUse=256M
RuntimeMaxUse=64M
EOF
chmod 0644 /etc/systemd/journald.conf.d/aitrust-id.conf
systemctl restart systemd-journald.service
python3 /opt/aitrust-id/host/verify.py
echo 'Host baseline applied. Verify a NEW SSH connection before leaving the existing session.'
echo 'Independent backups, public intake, DNS/TLS, retention and recovery are NOT complete.'
