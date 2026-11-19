#!/usr/bin/env python3
"""Build release drafts and validate exact owner-approved handoffs. Never sends."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sys
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
PLATFORMS = ('bluesky', 'linkedin', 'instagram', 'youtube', 'x')


def digest(data):
    return hashlib.sha256(json.dumps(data, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode()).hexdigest()


def read(path):
    def unique(pairs):
        value = {}
        for key, item in pairs:
            if key in value:
                raise ValueError('Duplicate field')
            value[key] = item
        return value
    if path.stat().st_size > 1_000_000:
        raise ValueError('File outside budget')
    return json.loads(path.read_text(), object_pairs_hook=unique)


def drafts(root=ROOT):
    rows = []
    for path in sorted((root / 'communications/releases').glob('*.json')):
        brief = read(path)
        if set(brief) != {'id', 'version', 'title', 'use_case', 'summary', 'limits', 'url', 'evidence'}:
            raise ValueError('Release brief fields differ')
        if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', brief['id']) or path.stem != brief['id']:
            raise ValueError('Invalid release identity')
        for key in ('version', 'title', 'use_case', 'summary', 'limits', 'url'):
            if not isinstance(brief[key], str) or not brief[key].strip() or len(brief[key]) > 1200:
                raise ValueError('Invalid public copy')
        url = urlsplit(brief['url'])
        if url.scheme != 'https' or url.netloc != 'aitrustid.com' or url.query or url.fragment:
            raise ValueError('Official public URL required')
        if not isinstance(brief['evidence'], list) or not 1 <= len(brief['evidence']) <= 20:
            raise ValueError('Evidence required')
        evidence = {}
        for name in brief['evidence']:
            if not isinstance(name, str) or Path(name).is_absolute() or '..' in Path(name).parts:
                raise ValueError('Public repository evidence only')
            source = (root / name).resolve()
            if not source.is_relative_to(root.resolve()) or not source.is_file():
                raise ValueError('Evidence missing')
            evidence[name] = hashlib.sha256(source.read_bytes()).hexdigest()
        text = '\n\n'.join((brief['title'], brief['version'], brief['use_case'], brief['summary'], brief['limits'], brief['url']))
        body = {'id': brief['id'], 'version': brief['version'], 'text': text, 'evidence': evidence,
                'release_asserted': False, 'independent_accuracy_asserted': False}
        rows.append({**body, 'draft_sha256': digest(body), 'status': 'awaiting_owner_review'})
    if not rows:
        raise ValueError('No public release briefs')
    return {'format': 'ai-trust-id-announcement-queue/v1', 'brand': 'AI Trust ID',
            'requested_handle': 'AITRUSTID', 'network_post_performed': False, 'drafts': rows}


def handoff(queue, accounts, approval, now=None):
    if set(approval) != {'draft_sha256', 'platform', 'handle', 'approved_by', 'approved_at', 'expires_at'}:
        raise ValueError('Exact approval record required')
    if approval['approved_by'] != 'Michael' or approval['platform'] not in PLATFORMS:
        raise ValueError('Owner approval and supported platform required')
    now = now or datetime.now(timezone.utc)
    approved = datetime.fromisoformat(approval['approved_at'])
    expires = datetime.fromisoformat(approval['expires_at'])
    if approved.tzinfo is None or expires.tzinfo is None or not approved <= now < expires:
        raise ValueError('Approval time invalid or expired')
    if (expires - approved).total_seconds() > 7 * 86400:
        raise ValueError('Approval may last at most seven days')
    selected = [row for row in queue['drafts'] if row['draft_sha256'] == approval['draft_sha256']]
    if len(selected) != 1:
        raise ValueError('Draft or evidence changed; review again')
    destination = [row for row in accounts['accounts'] if row.get('platform') == approval['platform']
                   and row.get('handle') == approval['handle'] and row.get('connection_verified') is True]
    if len(destination) != 1:
        raise ValueError('Destination is not uniquely connected and verified')
    result = {'format': 'ai-trust-id-approved-social-handoff/v1', 'draft_sha256': approval['draft_sha256'],
              'platform': approval['platform'], 'handle': approval['handle'], 'text': selected[0]['text'],
              'approved_by': 'Michael', 'approved_at': approval['approved_at'], 'expires_at': approval['expires_at'],
              'network_post_performed': False}
    result['idempotency_key'] = digest(result)
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--approval', type=Path, help='Existing exact owner approval; absence generates drafts only')
    args = p.parse_args()
    try:
        queue = drafts()
        result = handoff(queue, read(ROOT / 'communications/accounts.json'), read(args.approval)) if args.approval else queue
        print(json.dumps(result, indent=2))
    except (OSError, ValueError, TypeError, KeyError):
        p.exit(1, 'Announcement refused: check the public brief, evidence, connected destination and current exact owner approval.\n')


if __name__ == '__main__':
    main()
