#!/usr/bin/env python3
"""Configure two approved hosts using private local credentials and pinned SSH.

This enables WAL archiving on the primary. It does not accept real submissions.
Secrets remain in an owner-private recovery directory and protected host files.
"""
import base64
import io
import ipaddress
import json
import os
from pathlib import Path
import secrets
import subprocess
import tarfile


def required(name):
    return os.environ[name]


def host(name):
    return str(ipaddress.ip_address(required(name)))


def command(args, data=None):
    return subprocess.run(args, input=data, capture_output=True, check=True, timeout=240).stdout


def ssh(address, user, key, script, data=None):
    return command(['ssh', '-i', str(key), '-o', 'IdentitiesOnly=yes', '-o', 'BatchMode=yes',
                    '-o', 'StrictHostKeyChecking=yes', '-o', 'ConnectTimeout=10',
                    user + '@' + address, script], data)


def private_file(path, value):
    if not path.exists():
        with path.open('x') as stream:
            stream.write(value)
        path.chmod(0o600)


def upload(address, user, key, files):
    folder = '/var/lib/aitrust-id/backup-upload-' + secrets.token_hex(8)
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode='w:gz') as archive:
        for name, value in files.items():
            info = tarfile.TarInfo(name)
            data = value if isinstance(value, bytes) else value.encode()
            info.size = len(data)
            info.mode = 0o600
            archive.addfile(info, io.BytesIO(data))
    ssh(address, user, key, 'sudo -n install -d -m 0700 ' + folder + '; sudo -n tar -xzf - -C ' + folder, stream.getvalue())
    return folder


def main():
    os.umask(0o077)
    primary = host('AITRUST_PRIMARY_HOST')
    backup = host('AITRUST_BACKUP_HOST')
    primary_key = Path(required('AITRUST_PRIMARY_KEY')).resolve(strict=True)
    backup_key = Path(required('AITRUST_BACKUP_KEY')).resolve(strict=True)
    recovery = Path(required('AITRUST_RECOVERY_DIR')).resolve()
    checkout = Path(__file__).resolve().parents[2]
    if recovery == checkout or checkout in recovery.parents:
        raise SystemExit('Recovery secrets must be outside the public checkout')
    recovery.mkdir(parents=True, mode=0o700, exist_ok=True)
    if recovery.stat().st_mode & 0o077:
        raise SystemExit('Recovery directory must be owner-only')
    cipher = recovery / 'repository-cipher.txt'
    private_file(cipher, base64.b64encode(secrets.token_bytes(48)).decode() + '\n')
    secret = cipher.read_text().strip()
    if len(secret) < 48 or any(c.isspace() for c in secret):
        raise SystemExit('Invalid recovery cipher format')
    for name in ['primary-archive', 'repository-read']:
        path = recovery / name
        if not path.exists():
            command(['ssh-keygen','-q','-t','ed25519','-N','','-C','aitrust-' + name,'-f',str(path)])
    version_primary = ssh(primary,'debian',primary_key,'sudo -n pgbackrest version').decode().strip()
    version_backup = ssh(backup,'ait-backup-admin',backup_key,'sudo -n pgbackrest version').decode().strip()
    if version_primary != version_backup:
        raise SystemExit('pgBackRest versions must match exactly')
    primary_host_key = ssh(primary,'debian',primary_key,'sudo -n cat /etc/ssh/ssh_host_ed25519_key.pub').decode().split()[:2]
    backup_host_key = ssh(backup,'ait-backup-admin',backup_key,'sudo -n cat /etc/ssh/ssh_host_ed25519_key.pub').decode().split()[:2]
    settings = ssh(primary,'debian',primary_key,
                   "sudo -n runuser -u postgres -- psql --no-psqlrc -XAt -d aitrustid -c \"SELECT jsonb_object_agg(name, setting::integer) FROM pg_settings WHERE name IN ('max_connections','max_worker_processes','max_wal_senders','max_prepared_transactions','max_locks_per_transaction')\"").decode().strip()
    json.loads(settings)
    settings_path = recovery/'recovery-settings.json'
    private_file(settings_path, settings+'\n')
    if json.loads(settings_path.read_text()) != json.loads(settings):
        raise SystemExit('Source recovery settings changed; migrate recovery metadata explicitly')
    wrapper = Path(__file__).with_name('remote.py').read_bytes()
    common = ('[global]\nrepo1-path=/var/lib/pgbackrest\nrepo1-cipher-type=aes-256-cbc\n'
              'repo1-cipher-pass=' + secret + '\nrepo1-retention-full=2\nstart-fast=y\n'
              'process-max=1\nlog-level-file=warn\nlog-level-console=warn\narchive-timeout=120\n')
    primary_config = common + 'repo1-host=' + backup + '\nrepo1-host-user=pgbackrest\n\n[aitrustid]\npg1-path=/var/lib/postgresql/18/main\n'
    backup_config = common + '\n[aitrustid]\npg1-host=' + primary + '\npg1-host-user=postgres\npg1-path=/var/lib/postgresql/18/main\n'
    for name, config in [('primary.conf', primary_config), ('repository.conf', backup_config)]:
        path = recovery / name
        if path.exists() and path.read_text() != config:
            raise SystemExit('Recovery configuration differs; explicit migration is required')
        private_file(path, config)
    restrict = 'restrict,command="/opt/aitrust-id/backup/remote.py" '
    primary_files = {'config':primary_config, 'id_ed25519':(recovery/'primary-archive').read_bytes(),
                     'authorized_keys':'from="' + backup + '",' + restrict + (recovery/'repository-read.pub').read_text(),
                     'known_hosts':backup + ' ' + ' '.join(backup_host_key) + '\n',
                     'ssh_config':f'Host {backup}\n  User pgbackrest\n  IdentityFile /var/lib/postgresql/.ssh/id_ed25519\n  IdentitiesOnly yes\n  BatchMode yes\n  StrictHostKeyChecking yes\n  UserKnownHostsFile /var/lib/postgresql/.ssh/known_hosts\n  ConnectTimeout 10\n',
                     'remote.py':wrapper, 'source-health.py':Path(__file__).with_name('source-health.py').read_bytes(),
                     'source-monitor.sh':Path(__file__).with_name('source-monitor.sh').read_bytes()}
    backup_files = {'config':backup_config,'id_ed25519':(recovery/'repository-read').read_bytes(),
                    'authorized_keys':'from="' + primary + '",' + restrict + (recovery/'primary-archive.pub').read_text(),
                    'known_hosts':primary + ' ' + ' '.join(primary_host_key) + '\n', 'remote.py':wrapper,
                    'recovery-settings.json':settings+'\n',
                    'ssh_config':f'Host {primary}\n  User postgres\n  IdentityFile /home/pgbackrest/.ssh/id_ed25519\n  IdentitiesOnly yes\n  BatchMode yes\n  StrictHostKeyChecking yes\n  UserKnownHostsFile /home/pgbackrest/.ssh/known_hosts\n  ConnectTimeout 10\n'}
    for address,user,key,files,account,home in [
        (primary,'debian',primary_key,primary_files,'postgres','/var/lib/postgresql'),
        (backup,'ait-backup-admin',backup_key,backup_files,'pgbackrest','/home/pgbackrest')]:
        folder = upload(address,user,key,files)
        body = f'''set -eu
install -d -o {account} -g {account} -m 0700 {home}/.ssh
install -d -m 0755 /etc/pgbackrest /opt/aitrust-id/backup
if [ -f /etc/pgbackrest/pgbackrest.conf ] && [ ! -f /var/lib/aitrust-id/pre-backup.conf ]; then
  install -m 0600 /etc/pgbackrest/pgbackrest.conf /var/lib/aitrust-id/pre-backup.conf
fi
install -o root -g {account} -m 0640 {folder}/config /etc/pgbackrest/pgbackrest.conf
install -o {account} -g {account} -m 0600 {folder}/id_ed25519 {home}/.ssh/id_ed25519
install -o {account} -g {account} -m 0600 {folder}/known_hosts {home}/.ssh/known_hosts
install -o {account} -g {account} -m 0600 {folder}/ssh_config {home}/.ssh/config
install -o {account} -g {account} -m 0600 {folder}/authorized_keys {home}/.ssh/authorized_keys
install -m 0755 {folder}/remote.py /opt/aitrust-id/backup/remote.py
usermod --password '*' {account}
'''
        if account == 'postgres':
            body += f'''install -m 0755 {folder}/source-health.py /opt/aitrust-id/backup/source-health.py
install -m 0755 {folder}/source-monitor.sh /opt/aitrust-id/backup/source-monitor.sh
sed -i 's/^AllowUsers debian$/AllowUsers debian postgres/' /etc/ssh/sshd_config.d/00-aitrust-id.conf
'''
        else:
            body += f'install -m 0600 {folder}/recovery-settings.json /etc/pgbackrest/recovery-settings.json\n'
        body += f'''printf 'Match User {account}\\n    ForceCommand /opt/aitrust-id/backup/remote.py\\n' > /etc/ssh/sshd_config.d/90-aitrust-backup-protocol.conf
chmod 0644 /etc/ssh/sshd_config.d/90-aitrust-backup-protocol.conf
sshd -t
systemctl reload ssh
rm -rf -- {folder}
'''
        ssh(address,user,key,'sudo -n bash -s',body.encode())
    ssh(backup,'ait-backup-admin',backup_key,'sudo -n runuser -u pgbackrest -- pgbackrest --stanza=aitrustid stanza-create')
    archive_config = "archive_mode = on\narchive_command = '/usr/bin/pgbackrest --stanza=aitrustid archive-push %p'\narchive_timeout = '60s'\n"
    ssh(primary,'debian',primary_key,'sudo -n tee /etc/postgresql/18/main/conf.d/zz-aitrust-backup.conf > /dev/null',archive_config.encode())
    ssh(primary,'debian',primary_key,'sudo -n chmod 0640 /etc/postgresql/18/main/conf.d/zz-aitrust-backup.conf; sudo -n chown postgres:postgres /etc/postgresql/18/main/conf.d/zz-aitrust-backup.conf; sudo -n systemctl restart postgresql@18-main')
    ssh(primary,'debian',primary_key,'sudo -n runuser -u postgres -- pgbackrest --stanza=aitrustid check')
    ssh(backup,'ait-backup-admin',backup_key,'sudo -n runuser -u pgbackrest -- pgbackrest --stanza=aitrustid check')
    ssh(primary,'debian',primary_key,'sudo -n bash /opt/aitrust-id/backup/source-monitor.sh')
    print('Matching versions, restricted service keys, encrypted stanza and both archive checks verified.')


if __name__ == '__main__':
    main()
