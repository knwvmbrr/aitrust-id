#!/usr/bin/env bash
set -Eeuo pipefail
: "${AITRUST_HOST:?Set AITRUST_HOST to the approved Debian host}"
: "${AITRUST_SSH_KEY:?Set AITRUST_SSH_KEY to its dedicated private key outside the repo}"
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
ssh_options=(-i "$AITRUST_SSH_KEY" -o IdentitiesOnly=yes -o BatchMode=yes -o StrictHostKeyChecking=yes -o ConnectTimeout=10)
COPYFILE_DISABLE=1 tar --format=ustar -czf - bootstrap.sh sshd.conf nftables.conf postgresql.conf pg_hba.conf pg_ident.conf roles.sql verify.py |
  ssh "${ssh_options[@]}" "debian@$AITRUST_HOST" 'umask 077
install -d -m 0700 /home/debian/aitrust-host-bootstrap
tar -xzf - -C /home/debian/aitrust-host-bootstrap'
ssh "${ssh_options[@]}" "debian@$AITRUST_HOST" 'cd /home/debian/aitrust-host-bootstrap
sudo -n bash bootstrap.sh'
# A separate connection verifies that access survived SSH/firewall changes.
ssh "${ssh_options[@]}" "debian@$AITRUST_HOST" 'sudo -n python3 /opt/aitrust-id/host/verify.py'
