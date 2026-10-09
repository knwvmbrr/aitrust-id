#!/usr/bin/env python3
"""Provision separate topic identities; credential output is private JSON only."""
import json
import os
from pathlib import Path
import re
import secrets
import subprocess

DESTINATION = Path('/var/lib/aitrust-id/notification-provision.json')

def command(args, password=None):
    env = dict(os.environ)
    if password is not None:
        env['NTFY_PASSWORD'] = password
    process = subprocess.run(['runuser', '-u', 'ntfy', '--', '/usr/bin/ntfy', *args],
                             env=env, capture_output=True, text=True, timeout=30)
    if process.returncode:
        raise RuntimeError('ntfy provisioning command failed: ' + args[0])
    return process.stdout

if os.geteuid() != 0:
    raise SystemExit('Root required')
os.umask(0o077)
if DESTINATION.exists():
    print(DESTINATION.read_text())
    raise SystemExit(0)
identities = {}
for name, permission, topics in (
    ('primary-publisher', 'write-only', ('aitrust-primary-ops',)),
    ('backup-publisher', 'write-only', ('aitrust-backup-ops',)),
    ('owner-reader', 'read-only', ('aitrust-primary-ops', 'aitrust-backup-ops')),
):
    password = secrets.token_urlsafe(36)
    command(['user', 'add', '--role=user', name], password)
    for topic in topics:
        command(['access', name, topic, permission])
    output = command(['token', 'add', '--label=AI-Trust-ID-operations', name])
    match = re.search(r'\btk_[a-zA-Z0-9]{29}\b', output)
    if not match:
        raise RuntimeError('Token format changed')
    identities[name] = {'username': name, 'password': password, 'token': match.group(),
                        'permission': permission, 'topics': list(topics)}
fd = os.open(DESTINATION, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
with os.fdopen(fd, 'w') as handle:
    json.dump(identities, handle)
    handle.flush()
    os.fsync(handle.fileno())
print(json.dumps(identities))
