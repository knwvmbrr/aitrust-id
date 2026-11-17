"""No-network synthetic moderation engine. Not public authentication or a tag issuer."""
import copy
import hashlib
import html
import json
import re
import uuid

FORMAT = 'community-workbench/v1'
REQUEST = 'community-workbench-request/v1'
PUBLIC = 'community-public-projection/v1'
ACTORS = {'user-one': 'member', 'user-two': 'member', 'mod-one': 'moderator',
          'mod-two': 'moderator', 'official-one': 'official', 'admin-one': 'administrator'}
REASONS = ('privacy', 'conduct', 'off_scope', 'incorrect', 'author_request')
MAX_POSTS, MAX_REPORTS, MAX_APPEALS = 256, 128, 128
MAX_EVENTS, MAX_REQUESTS, MAX_AUDIT = 128, 256, 4096
MAX_BODY = 2000


class Refused(ValueError):
    """Never reflects a request value or private text."""


def require(ok):
    if not ok:
        raise Refused('Community workbench operation unavailable or refused.')


def encode(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False).encode()


def unique(pairs):
    value = {}
    for key, item in pairs:
        require(key not in value); value[key] = item
    return value


def parse(raw, limit=16384):
    require(type(raw) is bytes and 0 < len(raw) <= limit)
    try:
        return json.loads(raw.decode('utf-8', 'strict'), object_pairs_hook=unique,
                          parse_constant=lambda _: require(False))
    except (UnicodeError, ValueError, RecursionError):
        raise Refused('Community workbench operation unavailable or refused.') from None


def identity(value):
    require(type(value) is str)
    try:
        item = uuid.UUID(value)
    except (ValueError, AttributeError):
        require(False)
    require(str(item) == value and item.version == 4)
    return value


def body(value):
    require(type(value) is str and 0 < len(value.strip()) <= MAX_BODY and value == value.strip())
    require(not any(ord(c) < 32 and c not in '\n\t' or 0x7f <= ord(c) <= 0x9f
                    or 0xd800 <= ord(c) <= 0xdfff or c in '\u202a\u202b\u202c\u202d\u202e\u2066\u2067\u2068\u2069' for c in value))
    return value


def initial():
    return {'format': FORMAT, 'synthetic_only': True, 'clock': 0, 'revision': 0,
            'public_sequence': 0, 'posting_paused': False,
            'actors': {k: {'role': v, 'restriction': 'active'} for k, v in ACTORS.items()},
            'posts': {}, 'reports': {}, 'appeals': {}, 'events': [], 'audit': [], 'requests': {}, 'rates': {}}


def validate(state):
    require(type(state) is dict and set(state) == set(initial())
            and state['format'] == FORMAT and state['synthetic_only'] is True)
    for key in ('clock', 'revision', 'public_sequence'):
        require(type(state[key]) is int and 0 <= state[key] <= 2**53 - 1)
    require(type(state['posting_paused']) is bool and type(state['actors']) is dict and set(state['actors']) == set(ACTORS))
    for name, role in ACTORS.items():
        a = state['actors'][name]
        require(type(a) is dict and set(a) == {'role', 'restriction'} and a['role'] == role
                and a['restriction'] in ('active', 'restricted', 'suspended'))
        require(role == 'member' or a['restriction'] == 'active')
    for key, maximum in [('posts', MAX_POSTS), ('reports', MAX_REPORTS), ('appeals', MAX_APPEALS), ('requests', MAX_REQUESTS), ('rates', len(ACTORS))]:
        require(type(state[key]) is dict and len(state[key]) <= maximum)
    for pid, p in state['posts'].items():
        identity(pid)
        require(type(p) is dict and set(p) == {'owner', 'body', 'state', 'version', 'created', 'updated', 'was_public', 'approved_by', 'last_moderator', 'supersedes', 'supersedes_version', 'replacement', 'public_reason', 'updated_at', 'restriction', 'reply_to'})
        require(p['owner'] in ACTORS and ACTORS[p['owner']] in ('member', 'official'))
        require(p['state'] in ('queued', 'published', 'retracted', 'superseded'))
        require(type(p['version']) is int and 1 <= p['version'] <= MAX_AUDIT)
        require(all(type(p[k]) is int and 0 < p[k] <= state['revision'] for k in ('created', 'updated')))
        require(p['restriction'] in ('none', 'restricted', 'suspended'))
        require(type(p['was_public']) is bool and p['public_reason'] in (None, *REASONS, 'corrected', 'review_pending'))
        require(type(p['updated_at']) is int and 0 < p['updated_at'] <= state['clock'])
        require(p['approved_by'] is None or ACTORS.get(p['approved_by']) == 'moderator')
        require(p['last_moderator'] is None or ACTORS.get(p['last_moderator']) == 'moderator')
        if p['state'] in ('queued', 'published'): body(p['body'])
        else: require(p['body'] is None)
        if p['state'] == 'published': require(p['was_public'] and p['approved_by'] is not None and p['approved_by'] != p['owner'])
        for field in ('supersedes', 'replacement', 'reply_to'):
            require(p[field] is None or p[field] in state['posts'] and p[field] != pid)
        require(p['supersedes_version'] is None or type(p['supersedes_version']) is int and p['supersedes_version'] > 0)
    for rid, report in state['reports'].items():
        identity(rid)
        require(type(report) is dict and set(report) == {'reporter', 'target', 'category', 'state', 'created', 'disposition', 'replacement', 'reviewed_by'})
        require(report['reporter'] in ACTORS and report['category'] in ('wrong_result', 'privacy', 'conduct', 'security'))
        identity(report['target']); require(report['state'] in ('open', 'reviewed'))
        require(report['disposition'] in (None, 'needs_evidence', 'no_change', 'correction_referenced'))
        require(report['replacement'] is None or type(report['replacement']) is str and identity(report['replacement']))
        require(report['reviewed_by'] is None or ACTORS.get(report['reviewed_by']) == 'moderator' and report['reviewed_by'] != report['reporter'])
        require(type(report['created']) is int and 0 < report['created'] <= state['revision'])
    for aid, appeal in state['appeals'].items():
        identity(aid)
        require(type(appeal) is dict and set(appeal) == {'owner', 'post', 'moderator', 'version', 'state', 'resolved_by'})
        require(appeal['owner'] in ACTORS and appeal['post'] in state['posts'] and ACTORS.get(appeal['moderator']) == 'moderator')
        require(type(appeal['version']) is int and appeal['version'] > 0 and appeal['state'] in ('open', 'upheld', 'reconsider'))
        require(appeal['resolved_by'] is None or ACTORS.get(appeal['resolved_by']) == 'moderator' and appeal['resolved_by'] != appeal['moderator'])
    require(type(state['events']) is list and len(state['events']) <= MAX_EVENTS)
    previous = max(0, state['public_sequence'] - len(state['events']))
    for event in state['events']:
        require(type(event) is dict and set(event) == {'sequence', 'post'} and event['post'] in state['posts'])
        require(type(event['sequence']) is int and event['sequence'] == previous + 1); previous += 1
    require(previous == state['public_sequence'])
    require(type(state['audit']) is list and len(state['audit']) <= MAX_AUDIT)
    for row in state['audit']:
        require(type(row) is dict and set(row) == {'revision', 'actor', 'operation', 'target', 'reason', 'at'})
        require(type(row['at']) is int and 0 < row['at'] <= state['clock'])
        require(row['actor'] in ACTORS and row['operation'] in OPERATIONS and row['reason'] in (None, *REASONS))
        require(type(row['revision']) is int and 0 < row['revision'] <= state['revision'])
        require(row['target'] is None or type(row['target']) is str and len(row['target']) <= 64)
    for key, row in state['requests'].items():
        identity(key)
        require(type(row) is dict and set(row) == {'actor', 'digest', 'result', 'post'})
        require(row['actor'] in ACTORS and (row['digest'] is None or type(row['digest']) is str and re.fullmatch('[a-f0-9]{64}', row['digest'])))
        require(type(row['result']) is dict and set(row['result']) == {'operation', 'id', 'version', 'synthetic_only'} and row['result']['operation'] in OPERATIONS and row['result']['synthetic_only'] is True)
        identity(row['result']['id']); require(type(row['result']['version']) is int and row['result']['version'] > 0)
        require(row['post'] is None or row['post'] in state['posts'])
    for actor, times in state['rates'].items():
        require(actor in ACTORS and type(times) is list and len(times) <= 8 and all(type(t) is int and 0 < t <= state['clock'] for t in times))
    return state


OPERATIONS = {'submit', 'reply', 'edit', 'approve', 'retract', 'supersede', 'report', 'review_report',
              'warn', 'restrict', 'suspend', 'appeal', 'resolve_appeal', 'pause'}


class Community:
    def __init__(self, state=None):
        self.state = copy.deepcopy(validate(initial() if state is None else state))

    def apply(self, actor, request, now):
        require(actor in ACTORS and type(now) is int and self.state['clock'] <= now <= 2**53 - 1 and now > 0)
        require(type(request) is dict and set(request) == {'format', 'synthetic_only', 'request_id', 'operation', 'data'}
                and request['format'] == REQUEST and request['synthetic_only'] is True)
        rid = identity(request['request_id']); operation = request['operation']; data = request['data']
        require(type(operation) is str and operation in OPERATIONS and type(data) is dict)
        digest = hashlib.sha256(encode(request)).hexdigest()
        cached = self.state['requests'].get(rid)
        if cached:
            require(cached['actor'] == actor and cached['digest'] == digest)
            return copy.deepcopy(cached['result'])
        working = Community(self.state)
        result, post = working._apply(actor, rid, operation, data, now)
        state = working.state
        state['requests'][rid] = {'actor': actor, 'digest': digest, 'result': result, 'post': post}
        if len(state['requests']) > MAX_REQUESTS:
            del state['requests'][next(iter(state['requests']))]
        validate(state); self.state = state
        return copy.deepcopy(result)

    def _apply(self, actor, rid, op, d, now):
        s = self.state; role = ACTORS[actor]; moderator = role == 'moderator'
        require(len(s['audit']) < MAX_AUDIT)
        # Reserve one slot per removable post and one to pause admissions.
        is_emergency_pause = op == 'pause' and d.get('paused') is True and not s['posting_paused']
        require(len(s['audit']) < MAX_AUDIT - MAX_POSTS - 1 or op == 'retract' or is_emergency_pause)
        if op in ('submit', 'reply', 'edit', 'supersede', 'report', 'appeal'):
            require(not s['posting_paused'])
            times = [t for t in s['rates'].get(actor, []) if now - t < 60]
            require(len(times) < 8); s['rates'][actor] = [*times, now]
        s['clock'] = now; s['revision'] += 1; revision = s['revision']; target = None; reason = None

        def fields(*names): require(set(d) == set(names))
        def selected():
            p = s['posts'].get(identity(d.get('post_id'))); require(p is not None)
            require(type(d.get('version')) is int and d['version'] == p['version']); return p
        def touch(pid, p):
            p['version'] += 1; p['updated'] = revision; p['updated_at'] = now
            if p['was_public']:
                s['public_sequence'] += 1; s['events'].append({'sequence': s['public_sequence'], 'post': pid})
                s['events'] = s['events'][-MAX_EVENTS:]
        def scrub(pid, p, status):
            p['body'] = None; p['state'] = status
            for row in s['requests'].values():
                if row['post'] == pid: row['digest'] = None
            touch(pid, p)
        if op in ('submit', 'reply', 'supersede'):
            fields('body', 'consent_public', *(['post_id', 'version'] if op in ('reply', 'supersede') else []))
            require(role in ('member', 'official') and s['actors'][actor]['restriction'] == 'active' and d['consent_public'] is True)
            body(d['body']); require(len(s['posts']) < MAX_POSTS and rid not in s['posts'])
            prior = selected() if op in ('reply', 'supersede') else None
            if prior: require(prior['state'] == 'published')
            if op == 'supersede': require(prior['owner'] == actor)
            target = rid
            s['posts'][rid] = {'owner': actor, 'body': d['body'], 'state': 'queued', 'version': 1,
                'created': revision, 'updated': revision, 'was_public': False, 'approved_by': None,
                'last_moderator': None, 'supersedes': d['post_id'] if op == 'supersede' else None,
                'supersedes_version': d['version'] if op == 'supersede' else None, 'replacement': None, 'public_reason': None, 'updated_at': now, 'restriction': 'none',
                'reply_to': d['post_id'] if op == 'reply' else prior['reply_to'] if prior else None}
        elif op == 'edit':
            fields('post_id', 'version', 'body', 'consent_public'); p = selected(); target = d['post_id']
            require(p['owner'] == actor and s['actors'][actor]['restriction'] == 'active' and p['state'] in ('queued', 'published') and d['consent_public'] is True)
            body(d['body']); p.update(body=d['body'], state='queued', approved_by=None, public_reason='review_pending'); touch(target, p)
            for row in s['requests'].values():
                if row['post'] == target: row['digest'] = None
        elif op == 'approve':
            fields('post_id', 'version'); p = selected(); target = d['post_id']
            require(moderator and p['owner'] != actor and p['state'] == 'queued' and s['actors'][p['owner']]['restriction'] == 'active' and not s['posting_paused'])
            if p['supersedes']:
                old = s['posts'][p['supersedes']]
                require(old['state'] == 'published' and old['version'] == p['supersedes_version'])
                old['replacement'] = target; old['public_reason'] = 'corrected'; scrub(p['supersedes'], old, 'superseded')
            p.update(state='published', was_public=True, approved_by=actor, public_reason=None); touch(target, p)
        elif op in ('retract', 'warn', 'restrict', 'suspend'):
            fields('post_id', 'version', 'reason'); p = selected(); target = d['post_id']; reason = d['reason']
            require(reason in REASONS and (moderator or op == 'retract' and p['owner'] == actor))
            require(p['state'] in ('published', 'queued'))
            if op != 'retract':
                require(moderator and ACTORS[p['owner']] == 'member')
                if op != 'warn':
                    p['restriction'] = 'restricted' if op == 'restrict' else 'suspended'
                    active = [x['restriction'] for x in s['posts'].values() if x['owner'] == p['owner']]
                    s['actors'][p['owner']]['restriction'] = 'suspended' if 'suspended' in active else 'restricted'
            p['public_reason'] = reason
            if moderator: p['last_moderator'] = actor
            if op == 'warn': touch(target, p)
            else: scrub(target, p, 'retracted')
        elif op == 'report':
            fields('target_id', 'category', 'consent_private_metadata')
            identity(d['target_id']); require(d['category'] in ('wrong_result', 'privacy', 'conduct', 'security') and d['consent_private_metadata'] is True)
            require(len(s['reports']) < MAX_REPORTS and rid not in s['reports']); target = rid
            s['reports'][rid] = {'reporter': actor, 'target': d['target_id'], 'category': d['category'], 'state': 'open', 'created': revision, 'disposition': None, 'replacement': None, 'reviewed_by': None}
        elif op == 'review_report':
            fields('report_id', 'disposition', 'replacement_record_id'); target = identity(d['report_id']); report = s['reports'].get(target)
            require(moderator and report is not None and report['state'] == 'open' and report['reporter'] != actor
                    and d['disposition'] in ('needs_evidence', 'no_change', 'correction_referenced'))
            replacement = d['replacement_record_id']
            if d['disposition'] == 'correction_referenced':
                identity(replacement); require(replacement != report['target'])
            else: require(replacement is None)
            report.update(state='reviewed', disposition=d['disposition'], replacement=replacement, reviewed_by=actor)
        elif op == 'appeal':
            fields('post_id', 'version'); p = selected(); target = rid
            require(p['owner'] == actor and p['last_moderator'] is not None and p['state'] == 'retracted' and len(s['appeals']) < MAX_APPEALS and rid not in s['appeals'])
            require(not any(a['post'] == d['post_id'] and a['version'] == d['version'] for a in s['appeals'].values()))
            s['appeals'][rid] = {'owner': actor, 'post': d['post_id'], 'version': d['version'], 'moderator': p['last_moderator'], 'state': 'open', 'resolved_by': None}
        elif op == 'resolve_appeal':
            fields('appeal_id', 'decision'); target = identity(d['appeal_id']); a = s['appeals'].get(target)
            require(moderator and a is not None and a['state'] == 'open' and a['moderator'] != actor and d['decision'] in ('upheld', 'reconsider'))
            a.update(state=d['decision'], resolved_by=actor)
            if d['decision'] == 'reconsider':
                s['posts'][a['post']]['restriction'] = 'none'
                active = [x['restriction'] for x in s['posts'].values() if x['owner'] == a['owner']]
                s['actors'][a['owner']]['restriction'] = 'suspended' if 'suspended' in active else 'restricted' if 'restricted' in active else 'active'
        else:
            fields('paused'); require(role == 'administrator' and type(d['paused']) is bool); s['posting_paused'] = d['paused']; target = rid
        s['audit'].append({'revision': revision, 'actor': actor, 'operation': op, 'target': target, 'reason': reason, 'at': now})
        p = s['posts'].get(target)
        return {'operation': op, 'id': target, 'version': p['version'] if p else revision, 'synthetic_only': True}, target if p else None

    def public_item(self, pid):
        p = self.state['posts'][pid]
        if not p['was_public']: return None
        result = {'id': pid, 'version': p['version'], 'state': p['state'] if p['state'] != 'queued' else 'review_pending',
                  'body': p['body'] if p['state'] == 'published' else None,
                  'official': ACTORS[p['owner']] == 'official', 'replacement': p['replacement'], 'reply_to': p['reply_to'],
                  'reason_category': p['public_reason'], 'updated_at': p['updated_at'],
                  'appeal': 'independent_review_requested_privately' if p['last_moderator'] and p['state'] == 'retracted' else None}
        return result

    def public(self, after=0, limit=20):
        require(type(after) is int and 0 <= after <= self.state['revision'] and type(limit) is int and 1 <= limit <= 20)
        rows = [(pid, p) for pid, p in self.state['posts'].items() if p['was_public'] and p['created'] > after]
        rows.sort(key=lambda row: row[1]['created']); rows = rows[:limit]
        return {'format': PUBLIC, 'sequence': self.state['public_sequence'], 'items': [self.public_item(pid) for pid, _ in rows],
                'next_page': rows[-1][1]['created'] if len(rows) == limit else None, 'cache_control': 'no-store', 'training_consent': False}

    def replay(self, after=0, limit=20):
        require(type(after) is int and 0 <= after <= self.state['public_sequence'] and type(limit) is int and 1 <= limit <= 20)
        events = self.state['events']; floor = events[0]['sequence'] - 1 if events else 0
        if after < floor:
            return {'format': PUBLIC, 'reset_required': True, 'sequence': self.state['public_sequence'], 'events': [], 'cache_control': 'no-store'}
        selected = [e for e in events if e['sequence'] > after][:limit]
        return {'format': PUBLIC, 'reset_required': False, 'sequence': selected[-1]['sequence'] if selected else after,
                'events': [{'sequence': e['sequence'], 'item': self.public_item(e['post'])} for e in selected], 'cache_control': 'no-store'}

    def private(self, actor):
        require(actor in ACTORS); moderator = ACTORS[actor] == 'moderator'
        return {'synthetic_only': True, 'posts': {k: copy.deepcopy(v) for k, v in self.state['posts'].items() if moderator or v['owner'] == actor},
                'reports': {k: copy.deepcopy(v) for k, v in self.state['reports'].items() if moderator or v['reporter'] == actor},
                'appeals': {k: copy.deepcopy(v) for k, v in self.state['appeals'].items() if moderator or v['owner'] == actor}}

    def audit(self, actor):
        require(ACTORS.get(actor) in ('moderator', 'administrator'))
        return {'synthetic_only': True, 'audit': copy.deepcopy(self.state['audit']), 'bodies_included': False, 'public_export': False}


def render(public):
    require(type(public) is dict and public.get('format') == PUBLIC and type(public.get('items')) is list)
    parts = ['<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><meta http-equiv="Content-Security-Policy" content="default-src &#39;none&#39;; style-src &#39;unsafe-inline&#39;"><title>AI Trust ID — synthetic community view</title><main><h1>AI Trust ID</h1><p>Synthetic offline community snapshot. Refresh from current records; saved copies cannot be recalled.</p>']
    for row in public['items']:
        require(type(row) is dict and set(row) == {'id', 'version', 'state', 'body', 'official', 'replacement', 'reason_category', 'updated_at', 'appeal', 'reply_to'})
        identity(row['id']); require(type(row['version']) is int and row['version'] > 0 and type(row['official']) is bool)
        require(row['state'] in ('published', 'review_pending', 'retracted', 'superseded'))
        require(row['reason_category'] in (None, *REASONS, 'corrected', 'review_pending') and type(row['updated_at']) is int and row['updated_at'] > 0
                and row['appeal'] in (None, 'independent_review_requested_privately'))
        require(row['reply_to'] is None or type(row['reply_to']) is str and identity(row['reply_to']))
        require(row['replacement'] is None or type(row['replacement']) is str and identity(row['replacement']))
        text = body(row['body']) if row['state'] == 'published' else 'This message is not currently published.'
        if row['state'] != 'published': require(row['body'] is None)
        parts.append('<article><h2>' + ('Official reply' if row['official'] else 'Community message') + '</h2><p>' + html.escape(text) + '</p><p>Revision ' + str(row['version']) + ' · ' + row['state'] + '</p><p>Reason: ' + (row['reason_category'] or 'none') + '</p>' + ('<p>Ask privately for an independent review.</p>' if row['appeal'] else '') + '</article>')
    return ''.join(parts) + '</main></html>'


def update_cache(cache, batch):
    """Future-client contract: discard on replay gap; current revisions replace old bodies."""
    require(type(cache) is dict and set(cache) == {'sequence', 'items'} and type(cache['sequence']) is int and type(cache['items']) is dict)
    require(type(batch) is dict and batch.get('format') == PUBLIC and type(batch.get('reset_required')) is bool and type(batch.get('sequence')) is int and type(batch.get('events')) is list)
    if batch['reset_required']: return {'sequence': 0, 'items': {}}
    current = copy.deepcopy(cache)
    for e in batch['events']:
        require(type(e) is dict and set(e) == {'sequence', 'item'} and e['sequence'] == current['sequence'] + 1)
        item = e['item']; render({'format': PUBLIC, 'items': [item]})
        old = current['items'].get(item['id'])
        require(old is None or item['version'] >= old['version'])
        current['items'][item['id']] = copy.deepcopy(item); current['sequence'] = e['sequence']
    require(current['sequence'] == batch['sequence']); return current
