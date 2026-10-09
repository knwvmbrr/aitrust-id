#!/usr/bin/env bash
set -Eeuo pipefail
: "${AITRUST_HOST:?Set AITRUST_HOST to the approved Debian host}"
: "${AITRUST_SSH_KEY:?Set AITRUST_SSH_KEY to its dedicated private key}"
ssh -i "$AITRUST_SSH_KEY" -o IdentitiesOnly=yes -o BatchMode=yes \
  -o StrictHostKeyChecking=yes -o ConnectTimeout=10 "debian@$AITRUST_HOST" \
  'sudo -n python3 /opt/aitrust-id/host/verify.py'
