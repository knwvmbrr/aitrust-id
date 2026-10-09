#!/usr/bin/env python3
"""Bounded operational mail, never raw logs or database content."""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import smtplib
import ssl
import stat
import subprocess
import time
import urllib.request
from email.message import EmailMessage
from datetime import datetime, timezone

UNITS = {
    'primary': ('postgresql@18-main.service', 'aitrust-source-backup-health.service',
                'aitrust-source-backup-health.timer', 'nftables.service', 'ssh.service'),
    'backup': ('aitrust-backup.service', 'aitrust-protect.service',
               'aitrust-backup-health.service', 'aitrust-backup.timer',
               'aitrust-protect.timer', 'aitrust-backup-health.timer',
               'nftables.service', 'ssh.service', 'ntfy.service', 'caddy.service'),
}
FIELDS = {'smtp_host', 'smtp_port', 'tls_mode', 'username', 'password', 'sender', 'recipient'}


def validated_config(config):
    if isinstance(config, dict) and config.get('transport') == 'ntfy':
        if set(config) != {'transport', 'base_url', 'topic', 'token'}:
            raise ValueError('Invalid notification fields')
        if config['base_url'] != 'https://notify.aitrustid.com' or config['topic'] not in {'aitrust-primary-ops', 'aitrust-backup-ops'}:
            raise ValueError('Unapproved notification destination')
        if not isinstance(config['token'], str) or not re.fullmatch(r'tk_[a-zA-Z0-9]{29}', config['token']):
            raise ValueError('Invalid notification token')
        return config
    if not isinstance(config, dict) or set(config) != FIELDS:
        raise ValueError('Invalid configuration fields')
    if any(not isinstance(config[k], str) or not config[k] or '\r' in config[k] or '\n' in config[k]
           for k in FIELDS - {'smtp_port'}):
        raise ValueError('Invalid configuration values')
    if not re.fullmatch(r'[A-Za-z0-9.-]{1,253}', config['smtp_host']):
        raise ValueError('Invalid SMTP hostname')
    if type(config['smtp_port']) is not int or (config['tls_mode'], config['smtp_port']) not in {
            ('starttls', 587), ('implicit', 465)}:
        raise ValueError('TLS and port required')
    for field in ('sender', 'recipient'):
        if not re.fullmatch(r'[A-Za-z0-9.!#$%&\x27*+/=?^_`{|}~-]+@[A-Za-z0-9.-]+', config[field]):
            raise ValueError('Invalid mail address')
    return config


def systemd_credential(path, info):
    """Accept systemd's root-owned, ACL-readable credential mount only."""
    directory = os.environ.get('CREDENTIALS_DIRECTORY')
    path = Path(path)
    if (not directory or path.parent != Path(directory)
            or path.parent.parent != Path('/run/credentials')
            or info.st_uid != 0 or info.st_gid != 0
            or stat.S_IMODE(info.st_mode) != 0o440):
        return False
    parent = path.parent.lstat()
    return (stat.S_ISDIR(parent.st_mode) and parent.st_uid == 0
            and parent.st_gid == 0 and stat.S_IMODE(parent.st_mode) in {0o500, 0o550})


def load_config(path):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd) as handle:
        info = os.fstat(handle.fileno())
        mode = stat.S_IMODE(info.st_mode)
        private_mode = mode in {0o400, 0o600}
        # systemd uses a private root-owned mount and a service-specific ACL.
        service_credential = mode == 0o440 and systemd_credential(path, info)
        if (not stat.S_ISREG(info.st_mode) or not (private_mode or service_credential)
                or info.st_uid not in {0, os.geteuid()} or info.st_size > 16384):
            raise ValueError('Credential file permissions invalid')
        return validated_config(json.load(handle))


def inspect(role):
    issues = []
    for unit in UNITS[role]:
        result = subprocess.run(['/usr/bin/systemctl', 'show', unit,
                                 '--property=LoadState,ActiveState,Result'],
                                capture_output=True, text=True, timeout=10, check=True)
        props = dict(line.split('=', 1) for line in result.stdout.splitlines() if '=' in line)
        if props.get('LoadState') != 'loaded':
            issues.append(unit + ':missing')
        elif props.get('ActiveState') == 'failed' or props.get('Result', 'success') != 'success':
            issues.append(unit + ':failed')
        elif (unit.endswith('.timer') or unit in {'postgresql@18-main.service', 'ssh.service', 'nftables.service', 'ntfy.service', 'caddy.service'}) and props.get('ActiveState') != 'active':
            issues.append(unit + ':inactive')
    return sorted(issues)


def plan(previous, issues, now, test=False):
    digest = hashlib.sha256(json.dumps(issues).encode()).hexdigest()
    old = previous.get('digest')
    if test:
        return 'test', digest
    if issues:
        if digest != old or now - previous.get('sent_at', 0) >= 3600:
            return 'incident', digest
    elif previous.get('had_issues'):
        return 'recovered', digest
    elif old is None or now - previous.get('sent_at', 0) >= 86400:
        return 'heartbeat', digest
    return None, digest


def message(config, role, kind, issues):
    mail = EmailMessage()
    if config.get('transport') != 'ntfy':
        mail['From'] = config['sender']
        mail['To'] = config['recipient']
    mail['Subject'] = f'AI Trust ID | {role} | {kind}'
    timestamp = datetime.now(timezone.utc).isoformat()
    mail.set_content(f'AI Trust ID operational {kind}\nHost role: {role}\nUTC: {timestamp}\n'
                     + ('Checks requiring attention:\n' + '\n'.join(issues) if issues else 'Approved unit checks report healthy.')
                     + '\n\nInspect the private administrator journal for details. This message contains no application data.\n')
    return mail


class RejectRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError('Notification redirect rejected')


def deliver(config, mail):
    if config.get('transport') == 'ntfy':
        context = ssl.create_default_context()
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), RejectRedirect(),
                                            urllib.request.HTTPSHandler(context=context))
        request = urllib.request.Request(config['base_url'] + '/' + config['topic'],
                                         data=mail.get_content().encode(), method='POST',
                                         headers={'Authorization': 'Bearer ' + config['token'],
                                                  'Title': str(mail['Subject']),
                                                  'Content-Type': 'text/plain; charset=utf-8'})
        with opener.open(request, timeout=20) as response:
            result = json.loads(response.read(16384))
            if response.status != 200 or result.get('event') != 'message' or result.get('topic') != config['topic']:
                raise ValueError('Notification acknowledgement invalid')
        return
    context = ssl.create_default_context()
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    if config['tls_mode'] == 'implicit':
        client = smtplib.SMTP_SSL(config['smtp_host'], config['smtp_port'], timeout=20, context=context)
    else:
        client = smtplib.SMTP(config['smtp_host'], config['smtp_port'], timeout=20)
    try:
        client.ehlo()
        if config['tls_mode'] == 'starttls':
            # smtplib raises if STARTTLS is not supported, before any login.
            client.starttls(context=context)
            client.ehlo()
        client.login(config['username'], config['password'])
        rejected = client.send_message(mail)
        if rejected:
            raise RuntimeError('Recipient rejected')
    finally:
        client.close()


def run(config, role, state_path, test=False):
    state_path = Path(state_path)
    state_path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    lock_fd = os.open(state_path.parent / 'lock', os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    with os.fdopen(lock_fd, 'w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        previous = json.loads(state_path.read_text()) if state_path.exists() else {}
        issues = inspect(role)
        now = time.time()
        kind, digest = plan(previous, issues, now, test)
        if kind is None:
            return {'action': 'suppressed', 'issue_count': len(issues)}
        deliver(config, message(config, role, kind, issues))
        # A test never silences an incident or advances the operational heartbeat.
        if not test:
            temporary = state_path.with_suffix('.new')
            fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600)
            with os.fdopen(fd, 'w') as handle:
                json.dump({'digest': digest, 'had_issues': bool(issues), 'sent_at': now}, handle)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, state_path)
        return {'action': ('ntfy_accepted' if config.get('transport') == 'ntfy' else 'smtp_accepted'), 'kind': kind, 'issue_count': len(issues), 'inbox_arrival_verified': False}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--role', choices=UNITS, required=True)
    parser.add_argument('--inspect', action='store_true')
    parser.add_argument('--test', action='store_true')
    args = parser.parse_args()
    try:
        if args.inspect:
            issues = inspect(args.role)
            print(json.dumps({'role': args.role, 'issues': issues}))
            return int(bool(issues))
        credential_dir = os.environ.get('CREDENTIALS_DIRECTORY', '/etc/aitrust-id/alerts')
        config = load_config(Path(credential_dir) / 'delivery.json')
        state_dir = os.environ.get('STATE_DIRECTORY', '/var/lib/aitrust-alerts').split(':')[0]
        print(json.dumps(run(config, args.role, Path(state_dir) / 'sent.json', args.test)))
        return 0
    except Exception as error:
        # SMTP replies can contain addresses or credentials. Emit class only.
        print(json.dumps({'action': 'failed', 'error_class': type(error).__name__}), flush=True)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
