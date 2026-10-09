#!/usr/bin/env bash
# First baseline install uses owner-authorized root key, then disables root SSH.
set -Eeuo pipefail
: "${AITRUST_BACKUP_HOST:?Set the approved backup host}"
: "${AITRUST_BACKUP_KEY:?Set the dedicated backup key outside the repo}"
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
[[ -s $AITRUST_BACKUP_KEY.pub ]] || { echo 'Public key sidecar missing.' >&2; exit 1; }
ssh_options=(-i "$AITRUST_BACKUP_KEY" -o IdentitiesOnly=yes -o BatchMode=yes -o StrictHostKeyChecking=yes -o ConnectTimeout=10)
ssh-keygen -y -P '' -f "$AITRUST_BACKUP_KEY" >/dev/null
COPYFILE_DISABLE=1 tar --format=ustar -C .. -czf - backup/bootstrap.sh backup/remote.py backup/cycle.py backup/verify.py backup/restore.py backup/negative-checks.py host/sshd.conf host/nftables.conf |
  ssh "${ssh_options[@]}" "root@$AITRUST_BACKUP_HOST" 'umask 077; install -d -m 0700 /root/aitrust-backup-bootstrap; tar -xzf - -C /root/aitrust-backup-bootstrap'
ssh "${ssh_options[@]}" "root@$AITRUST_BACKUP_HOST" 'cat > /root/aitrust-backup-bootstrap/backup/admin.pub; chmod 0600 /root/aitrust-backup-bootstrap/backup/admin.pub' < "$AITRUST_BACKUP_KEY.pub"
ssh "${ssh_options[@]}" "root@$AITRUST_BACKUP_HOST" 'bash /root/aitrust-backup-bootstrap/backup/bootstrap.sh'
ssh "${ssh_options[@]}" "ait-backup-admin@$AITRUST_BACKUP_HOST" 'sudo -n true; pgbackrest version; sudo -n sshd -T | head -n 8'
