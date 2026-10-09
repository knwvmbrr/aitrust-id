#!/usr/bin/env python3
"""Root-managed backup and verified protected repository publication."""
import datetime
import fcntl
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import uuid

BASE = Path('/var/lib/aitrust-id')
REPO = Path('/var/lib/pgbackrest')


def verification_valid(report):
    errors = re.findall(r'(?:missing|checksum invalid|size invalid|other): (\d+)', report)
    return ('status: ok' in report and 'status: valid' in report and
            'status: invalid' not in report and bool(errors) and
            all(int(value) == 0 for value in errors))


def run(args):
    return subprocess.run(args, check=True, text=True, capture_output=True, timeout=3600).stdout


def main():
    if os.geteuid() != 0:
        raise SystemExit('Root is required for protected generations')
    if len(sys.argv) != 2 or sys.argv[1] not in {'backup', 'protect'}:
        raise SystemExit('Usage: cycle.py backup|protect')
    os.umask(0o077)
    protected = BASE / 'protected'
    status = BASE / 'backup-status'
    with (status / 'cycle.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        free = os.statvfs(protected)
        if free.f_bavail / free.f_blocks < 0.20:
            raise RuntimeError('Backup capacity below 20 percent free; owner action required')
        if sys.argv[1] == 'backup':
            kind = 'full' if datetime.datetime.now(datetime.timezone.utc).weekday() == 6 else 'diff'
            run(['runuser', '-u', 'pgbackrest', '--', 'pgbackrest', '--stanza=aitrustid', '--type=' + kind, 'backup'])
        else:
            run(['runuser', '-u', 'pgbackrest', '--', 'pgbackrest', '--stanza=aitrustid', 'check'])
        info = json.loads(run(['runuser', '-u', 'pgbackrest', '--', 'pgbackrest', '--stanza=aitrustid', '--output=json', 'info']))
        if not info or info[0]['status']['code'] != 0 or not info[0].get('backup') or info[0].get('cipher') != 'aes-256-cbc':
            raise RuntimeError('Working repository has no completed valid backup')
        stage = protected / ('.staging-' + uuid.uuid4().hex)
        stage.mkdir(mode=0o700)
        current = protected / 'current'
        args = ['rsync', '-rt', '--no-links', '--no-specials', '--no-devices', '--chmod=D0700,F0600']
        if current.is_symlink():
            previous = current.resolve(strict=True)
            if previous.parent != protected:
                raise RuntimeError('Protected generation pointer escapes its boundary')
            args += ['--link-dest=' + str(previous)]
        run([*args, str(REPO) + '/', str(stage) + '/'])
        # Hard links are only between root-owned protected generations. There
        # are no shared inodes with the service-owned working repository.
        verify = run(['pgbackrest', '--allow-root', '--stanza=aitrustid',
                      '--repo1-path=' + str(stage), '--output=text', '--verbose', 'verify'])
        if not verification_valid(verify):
            raise RuntimeError('Protected repository has missing or invalid files')
        name = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + uuid.uuid4().hex[:8]
        final = protected / name
        stage.rename(final)
        pointer = protected / ('.current-' + uuid.uuid4().hex)
        pointer.symlink_to(name)
        os.replace(pointer, current)
        report = {'at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                  'mode': sys.argv[1], 'generation': name, 'verify': verify,
                  'last_backup_stop': info[0]['backup'][-1]['timestamp']['stop'],
                  'free_bytes': os.statvfs(protected).f_bavail * os.statvfs(protected).f_frsize}
        tmp = status / '.last-success.json'
        tmp.write_text(json.dumps(report, indent=2) + '\n')
        os.replace(tmp, status / 'last-success.json')
        print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
