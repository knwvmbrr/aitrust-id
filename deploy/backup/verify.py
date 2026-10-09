#!/usr/bin/env python3
"""Read effective policy and backup freshness; no certification claim."""
import argparse
import datetime
import json
import os
from pathlib import Path
import subprocess
import sys


def run(args):
    return subprocess.run(args, text=True, capture_output=True, check=False, timeout=30)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--status-file', default='/var/lib/aitrust-id/backup-status/last-success.json')
    parser.add_argument('--minimum-free-percent', type=int, choices=range(20,100), default=20)
    args = parser.parse_args()
    if os.geteuid() != 0:
        raise SystemExit('Run with sudo')
    checks = {}
    ssh_lines = run(['sshd', '-T']).stdout.splitlines()
    ssh = dict(line.split(' ', 1) for line in ssh_lines)
    for key, value in {'permitrootlogin':'no','passwordauthentication':'no',
                       'kbdinteractiveauthentication':'no','allowagentforwarding':'no','x11forwarding':'no'}.items():
        checks['ssh_' + key] = ssh.get(key) == value
    users = [user for line in ssh_lines if line.startswith('allowusers ') for user in line.split()[1:]]
    checks['ssh_accounts'] = set(users) == {'ait-backup-admin','pgbackrest'}
    rules = json.loads(run(['nft','--json','list','ruleset']).stdout)['nftables']
    chains = {i['chain']['name']:i['chain'] for i in rules if 'chain' in i and i['chain'].get('table') == 'aitrust_host'}
    checks['dual_stack_input_drop'] = chains.get('input',{}).get('policy') == 'drop'
    checks['forward_drop'] = chains.get('forward',{}).get('policy') == 'drop'
    checks['persistent_firewall'] = run(['systemctl','is-enabled','nftables']).stdout.strip() == 'enabled'
    listeners = run(['ss','-lnutH']).stdout.splitlines()
    checks['no_database_tcp_listener'] = not any(line.split()[4].rsplit(':',1)[-1] == '5432' for line in listeners)
    checks['no_multicast_name_listener'] = not any(line.split()[4].rsplit(':',1)[-1] in {'5353','5355'} for line in listeners)
    checks['dns_works'] = run(['getent','ahostsv4','apt.postgresql.org']).returncode == 0
    checks['protected_root_only'] = (Path('/var/lib/aitrust-id/protected').stat().st_mode & 0o777) == 0o700
    checks['repository_account_cannot_read_protected'] = run(['runuser','-u','pgbackrest','--','ls','/var/lib/aitrust-id/protected']).returncode != 0
    checks['update_timer'] = run(['systemctl','is-active','apt-daily-upgrade.timer']).stdout.strip() == 'active'
    checks['pgbackrest_patched'] = run(['dpkg','--compare-versions',run(['pgbackrest','version']).stdout.split()[-1],'ge','2.59.3']).returncode == 0
    status = Path(args.status_file)
    report = json.loads(status.read_text()) if status.exists() else {}
    now = datetime.datetime.now(datetime.timezone.utc)
    checks['protected_generation_present'] = bool(report)
    checks['protected_generation_fresh'] = bool(report) and (now - datetime.datetime.fromisoformat(report['at'])).total_seconds() < 1800
    checks['backup_fresh'] = bool(report) and now.timestamp() - report['last_backup_stop'] < 30*3600
    disk = os.statvfs('/var/lib/aitrust-id/protected')
    checks['capacity_above_required_percent'] = disk.f_bavail / disk.f_blocks >= args.minimum_free_percent / 100
    failures = [key for key, value in checks.items() if not value]
    print(json.dumps({'scope':'independent_backup_host','checks':checks,'failures':failures,
                      'passed':not failures,'production_ready':False}, indent=2))
    return int(bool(failures))


if __name__ == '__main__':
    sys.exit(main())
