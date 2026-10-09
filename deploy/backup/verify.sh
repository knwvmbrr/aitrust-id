#!/usr/bin/env bash
set -Eeuo pipefail
: "${AITRUST_BACKUP_HOST:?Set the approved backup host}"
: "${AITRUST_BACKUP_KEY:?Set its dedicated private key outside the repo}"
ssh -i "$AITRUST_BACKUP_KEY" -o IdentitiesOnly=yes -o BatchMode=yes \
  -o StrictHostKeyChecking=yes -o ConnectTimeout=10 "ait-backup-admin@$AITRUST_BACKUP_HOST" \
  'sudo -n python3 /opt/aitrust-id/backup/verify.py'
