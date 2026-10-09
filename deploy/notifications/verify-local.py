#!/usr/bin/env python3
"""Actual topic authorization checks; credentials and bodies never emitted."""
import json
import argparse
from pathlib import Path
import urllib.request
import urllib.error

parser = argparse.ArgumentParser()
parser.add_argument('--https', action='store_true')
parser.add_argument('--credentials', type=Path, default=Path('/var/lib/aitrust-id/notification-provision.json'))
args = parser.parse_args()
identity = json.loads(args.credentials.read_text())
base = 'https://notify.aitrustid.com' if args.https else 'http://127.0.0.1:2586'
class RejectRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError('Redirect rejected')
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), RejectRedirect())
checks = []

def request(method, topic, name=None):
    url = base + '/' + topic + ('/json?poll=1' if method == 'GET' else '')
    headers = {'Authorization': 'Bearer ' + identity[name]['token']} if name else {}
    req = urllib.request.Request(url, data=b'AI Trust ID synthetic notification boundary check' if method == 'POST' else None, method=method, headers=headers)
    try:
        with opener.open(req, timeout=10) as response:
            return response.status, response.read(65536)
    except urllib.error.HTTPError as error:
        return error.code, b''

for label, method, topic, name, expected in (
    ('anonymous publish denied','POST','aitrust-primary-ops',None,403),
    ('anonymous read denied','GET','aitrust-primary-ops',None,403),
    ('primary may publish own topic','POST','aitrust-primary-ops','primary-publisher',200),
    ('backup may publish own topic','POST','aitrust-backup-ops','backup-publisher',200),
    ('primary cannot impersonate backup topic','POST','aitrust-backup-ops','primary-publisher',403),
    ('backup cannot read notifications','GET','aitrust-backup-ops','backup-publisher',403),
    ('reader cannot publish','POST','aitrust-primary-ops','owner-reader',403),
    ('reader may read primary','GET','aitrust-primary-ops','owner-reader',200),
    ('reader may read backup','GET','aitrust-backup-ops','owner-reader',200),
    ('reader cannot access unrelated topics','GET','unrelated-topic','owner-reader',403),
):
    status, body = request(method, topic, name)
    checks.append({'check':label,'status':status,'expected':expected,'pass':status==expected})
if args.https:
    for role in ('primary', 'backup'):
        status, body = request('GET', 'aitrust-' + role + '-ops', 'owner-reader')
        events = [json.loads(line) for line in body.splitlines()]
        found = any(event.get('event') == 'message' and
                    ('AI Trust ID operational heartbeat\nHost role: ' + role + '\n') in event.get('message', '')
                    for event in events)
        checks.append({'check':role + ' host heartbeat readable over HTTPS', 'pass':status==200 and found})
print(json.dumps({'transport':'verified_https' if args.https else 'loopback', 'checks':checks,'pass':all(c['pass'] for c in checks)}))
raise SystemExit(0 if all(c['pass'] for c in checks) else 1)
