"""Nonoperating reference-programme applications and replayable review workflow.

Declared roles and evidence are not authenticated people, executions or authority.
No input supplies code, a policy, an executable, an endpoint or an approval flag.
"""
from datetime import datetime, timezone, timedelta
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import stat

from tools.citation_resolution import Capture, OutputCommitUncertain

ROOT = Path(__file__).resolve().parents[1]
PROFILE = 'reference-programme-review/v1'
POLICY = 'eval/certification-programme.json'
POLICY_SHA = '852df2d38ba5de55b2ffd0e8bbcc0fd293d27579ca1171c5528c95e1773588a6'
MAX_INPUT = 1_000_000
MAX_OUTPUT = 2_000_000
MAX_ACTIONS = 32
ID = re.compile(r'[a-z][a-z0-9_-]{0,63}\Z')
SHA = re.compile(r'[a-f0-9]{64}\Z')
ROLES = ('applicant', 'assessor', 'decision_reviewer', 'appeal_reviewer')
SOURCES = (POLICY, 'tools/certification_programme.py',
           'scripts/certification-programme.py', 'tools/citation_resolution.py',
           'protocol/corpus.py', 'protocol/normalization.py',
           'protocol/unicode15-data.json', 'scripts/verify-conformance-delivery.py',
           'GOVERNANCE.md', 'MAINTAINERS.md', 'docs/mark-usage.md',
           'docs/certification-programme.md', 'docs/certification-programme-guide.md',
           'docs/certification-programme-plan.md')


class Refusal(ValueError):
    pass


def need(ok):
    if not ok:
        raise Refusal('Reference programme unavailable.')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=True, allow_nan=False).encode('ascii')


def parse(raw):
    need(type(raw) is bytes and 0 < len(raw) <= MAX_INPUT)
    def unique(pairs):
        result = {}
        for key, value in pairs:
            need(key not in result)
            result[key] = value
        return result
    def reject(_):
        raise Refusal('Reference programme unavailable.')
    value = json.loads(raw.decode('utf-8', 'strict'), object_pairs_hook=unique,
                       parse_constant=reject, parse_float=reject,
                       parse_int=lambda s: int(s) if len(s) <= 12 else reject(s))
    count = 0
    def visit(item, depth=0):
        nonlocal count
        count += 1
        need(depth <= 16 and count <= 20000)
        if type(item) is dict:
            need(len(item) <= 256)
            for key, child in item.items():
                need(type(key) is str and len(key) <= 256)
                visit(child, depth+1)
        elif type(item) is list:
            need(len(item) <= 256)
            for child in item:
                visit(child, depth+1)
        elif type(item) is str:
            need(len(item) <= 8192 and '\0' not in item)
        else:
            need(item is None or type(item) in (int, bool))
    visit(value)
    return value


def keys(value, fields):
    need(type(value) is dict and set(value) == set(fields))


def token(value):
    need(type(value) is str and ID.fullmatch(value))


def stamp(value):
    need(type(value) is str and 20 <= len(value) <= 32)
    result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    need(result.tzinfo is not None and result.utcoffset() == timedelta(0))
    return result


def delivery():
    # Literal repository-owned module, never an import/path supplied by an input.
    spec = importlib.util.spec_from_file_location('reference_conformance_delivery',
                                                 ROOT/'scripts/verify-conformance-delivery.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sources(capture):
    engine = delivery()
    names = tuple(dict.fromkeys((*SOURCES, *engine.identity())))
    need(len(names) <= 32)
    bound = {name: sha(capture.read(ROOT/name, 2_000_000, private=False)) for name in names}
    need(bound[POLICY] == POLICY_SHA)
    return bound


def programme(capture):
    raw = capture.read(ROOT/POLICY, 65536, private=False)
    need(sha(raw) == POLICY_SHA)
    return parse(raw)


def private_path(capture, path):
    path = Path(path).absolute()
    need(not path.is_relative_to(ROOT) and '..' not in path.parts)
    parent, _ = capture.parent(path)
    info = os.fstat(parent)
    need(info.st_uid == os.getuid() and stat.S_IMODE(info.st_mode) == 0o700)
    # Retained handles and Capture.check bind directory names. Recheck markers
    # before and after publication; a Git worktree file is a marker too.
    for ancestor in path.parents:
        try:
            os.lstat(ancestor/'.git')
        except FileNotFoundError:
            continue
        raise Refusal('Reference programme unavailable.')
    return path


def read(capture, path):
    return capture.read(private_path(capture, path), MAX_INPUT)


def application(value, policy):
    keys(value, ('profile', 'application_id', 'purpose', 'scope', 'implementation',
                 'roles', 'conflicts', 'documents', 'requirements', 'interface_evidence',
                 'valid_until'))
    need(value['profile'] == 'reference-programme-application/v1')
    token(value['application_id'])
    need(value['purpose'] in ('reference-exercise', 'preparation'))
    need(value['scope'] in policy['scopes'])
    keys(value['implementation'], ('id', 'source_sha256'))
    token(value['implementation']['id'])
    identity = value['implementation']['source_sha256']
    need(type(identity) is dict and 0 < len(identity) <= 32)
    need(all(type(k) is str and 0 < len(k) <= 256 and type(v) is str and SHA.fullmatch(v)
             for k,v in identity.items()))
    keys(value['roles'], ROLES)
    actors = list(value['roles'].values())
    for actor in actors:
        if actor is not None:
            token(actor)
    need(len([a for a in actors if a is not None]) == len(set(a for a in actors if a is not None)))
    keys(value['conflicts'], ROLES[1:])
    need(all(type(v) is bool or v is None for v in value['conflicts'].values()))
    docs = value['documents']
    need(type(docs) is list and len(docs) <= 64)
    names = set()
    for doc in docs:
        keys(doc, ('id', 'text'))
        token(doc['id']); need(doc['id'] not in names)
        names.add(doc['id'])
        need(type(doc['text']) is str and 0 < len(doc['text'].strip()) <= 4000)
    wanted = [r['id'] for r in policy['requirements']]
    keys(value['requirements'], wanted)
    for refs in value['requirements'].values():
        need(type(refs) is list and len(refs) <= 8 and len(refs) == len(set(refs)))
        need(all(type(n) is str and n in names for n in refs))
    stamp(value['valid_until'])
    evidence = value['interface_evidence']
    if evidence is not None:
        need(type(evidence) is dict)
        # Reuse the actual current 28-case/source/refusal contract, not a new
        # all-pass flag or a total which could omit inconvenient categories.
        delivery().verify(evidence)
        need(value['implementation']['id'] == 'reference' and identity == evidence['sources'])
    return value


def gaps(app, policy, at):
    missing = [r['id'] for r in policy['requirements'] if not app['requirements'][r['id']]]
    for role, actor in app['roles'].items():
        if actor is None:
            missing.append('unfilled_'+role)
    for role, conflict in app['conflicts'].items():
        if conflict is not False:
            missing.append('conflict_or_unknown_'+role)
    if not at < stamp(app['valid_until']) <= at + timedelta(days=365):
        missing.append('reference_validity')
    if app['scope'] == 'software-interface':
        if app['interface_evidence'] is None:
            missing.append('selected_28_interface_checks')
    else:
        # Presence of a document is not proof of independent accuracy, accepted
        # organization ownership or applicable actual operating agreements.
        missing.extend(policy['scopes'][app['scope']]['additional_requirements'])
    return sorted(missing)


def event(value, policy):
    keys(value, ('kind', 'actor', 'at', 'data'))
    need(value['kind'] in ('assess', 'decide', 'appeal', 'appeal_decide', 'correct',
                          'withdraw', 'suspend', 'renew'))
    token(value['actor']); stamp(value['at'])
    data = value['data']
    kind = value['kind']
    if kind in ('assess', 'decide', 'appeal_decide'):
        keys(data, ('disposition', 'checked_requirements', 'reason'))
        need(type(data['checked_requirements']) is list and
             data['checked_requirements'] == [v['id'] for v in policy['requirements']])
        need(type(data['reason']) is str and 0 < len(data['reason'].strip()) <= 2000)
        allowed = {'assess': ('recommend', 'changes', 'recuse'),
                   'decide': ('complete', 'changes', 'refuse'),
                   'appeal_decide': ('remand', 'uphold')}
        need(data['disposition'] in allowed[kind])
    elif kind in ('appeal', 'withdraw', 'suspend'):
        keys(data, ('reason',))
        need(type(data['reason']) is str and 0 < len(data['reason'].strip()) <= 2000)
    elif kind == 'correct':
        keys(data, ('application', 'reason'))
        application(data['application'], policy)
        need(type(data['reason']) is str and 0 < len(data['reason'].strip()) <= 2000)
    else:
        keys(data, ('valid_until', 'reason'))
        stamp(data['valid_until'])
        need(type(data['reason']) is str and 0 < len(data['reason'].strip()) <= 2000)
    return value


def replay(app, actions, policy, opened):
    application(app, policy)
    need(type(actions) is list and len(actions) <= MAX_ACTIONS)
    # JSON copy prevents an input or returned state from mutating the base.
    current = json.loads(encoded(app)); state = 'APPLICATION_RECORDED'
    last = stamp(opened); prior_appeal = None
    for action in actions:
        event(action, policy); when = stamp(action['at']); need(when >= last)
        last = when
        need(state != 'WITHDRAWN')
        kind, data, actor = action['kind'], action['data'], action['actor']
        role = {'assess':'assessor', 'decide':'decision_reviewer',
                'appeal_decide':'appeal_reviewer', 'suspend':'decision_reviewer'}.get(kind, 'applicant')
        need(actor == current['roles'][role])
        if role != 'applicant' and kind != 'assess':
            need(current['conflicts'][role] is False)
        missing = gaps(current, policy, when)
        if kind == 'assess':
            need(state in ('APPLICATION_RECORDED', 'CHANGES_REQUIRED', 'REVIEW_EXPIRED'))
            if data['disposition'] == 'recuse':
                state = 'RECUSED'
            else:
                need(current['conflicts']['assessor'] is False)
                if data['disposition'] == 'recommend':
                    need(not missing); state = 'ASSESSOR_RECOMMENDED'
                else:
                    state = 'CHANGES_REQUIRED'
        elif kind == 'decide':
            need(state == 'ASSESSOR_RECOMMENDED')
            if data['disposition'] == 'complete':
                need(not missing); state = 'REFERENCE_REVIEW_COMPLETE'
            else:
                state = 'CHANGES_REQUIRED' if data['disposition'] == 'changes' else 'REFERENCE_REFUSED'
        elif kind == 'appeal':
            need(state in ('REFERENCE_REVIEW_COMPLETE','CHANGES_REQUIRED','REFERENCE_REFUSED','SUSPENDED','RECUSED'))
            prior_appeal = state; state = 'APPEAL_PENDING'
        elif kind == 'appeal_decide':
            need(state == 'APPEAL_PENDING' and prior_appeal is not None)
            if data['disposition'] == 'remand':
                state = 'CHANGES_REQUIRED'
            else:
                need(prior_appeal != 'REFERENCE_REVIEW_COMPLETE' or not missing)
                state = prior_appeal
            prior_appeal = None
        elif kind == 'correct':
            need(state != 'APPEAL_PENDING')
            new = data['application']
            need(new['application_id'] == app['application_id'])
            current = json.loads(encoded(new)); state = 'CHANGES_REQUIRED'
        elif kind == 'renew':
            need(state != 'APPEAL_PENDING')
            current['valid_until'] = data['valid_until']; state = 'CHANGES_REQUIRED'
        elif kind == 'withdraw':
            state = 'WITHDRAWN'
        else:
            need(state in ('REFERENCE_REVIEW_COMPLETE','ASSESSOR_RECOMMENDED'))
            state = 'SUSPENDED'
    return current, state, last


def record(app, actions, opened, bound, policy, predecessor):
    current, state, last = replay(app, actions, policy, opened)
    missing = gaps(current, policy, last)
    need(predecessor is None or type(predecessor) is str and SHA.fullmatch(predecessor))
    value = {'profile':PROFILE, 'programme_sha256':POLICY_SHA, 'source_sha256':bound,
             'opened_at':opened, 'application':json.loads(encoded(app)),
             'actions':json.loads(encoded(actions)),
             'predecessor_sha256':predecessor, 'state':state,
             'missing_requirements':missing, 'claims':json.loads(encoded(policy['claims'])),
             'evidence_authenticity_verified':False, 'declared_roles_only':True}
    need(len(encoded(value))+1 <= MAX_INPUT)
    return value


def check_record(value, bound, policy):
    keys(value, ('profile','programme_sha256','source_sha256','opened_at','application',
                 'actions','predecessor_sha256','state','missing_requirements','claims',
                 'evidence_authenticity_verified','declared_roles_only'))
    need(encoded(value) == encoded(record(value['application'], value['actions'], value['opened_at'],
                         bound, policy, value['predecessor_sha256'])))
    return value


def brief(value, policy, now):
    current, state, last = replay(value['application'], value['actions'], policy, value['opened_at'])
    need(stamp(now) >= last)
    missing = gaps(current, policy, stamp(now))
    if state == 'REFERENCE_REVIEW_COMPLETE' and missing:
        state = 'REVIEW_EXPIRED'
    return {'state':state, 'checklist_complete':not missing,
            'missing_requirement_count':len(missing), 'actions_recorded':len(value['actions']),
            'scope':current['scope'], **policy['claims'],
            'evidence_authenticity_verified':False, 'declared_roles_only':True}


def practice(policy, evidence, now):
    # Invented preparation example, not a person or accepted accreditation role.
    docs = [{'id':r['id'], 'text':'Invented reference exercise: '+r['requirement']}
            for r in policy['requirements']]
    return {'profile':'reference-programme-application/v1','application_id':'practice',
            'purpose':'reference-exercise','scope':'software-interface',
            'implementation':{'id':'reference','source_sha256':evidence['sources']},
            'roles':{role:'example_'+role for role in ROLES},
            'conflicts':{role:False for role in ROLES[1:]},'documents':docs,
            'requirements':{r['id']:[r['id']] for r in policy['requirements']},
            'interface_evidence':evidence,
            'valid_until':(stamp(now)+timedelta(days=30)).isoformat()}


def execute(operation, inputs, output=None):
    now = datetime.now(timezone.utc).isoformat()
    need(operation in ('practice','start','advance','inspect','revalidate'))
    expected = {'practice':set(), 'start':{'application'}, 'advance':{'record','event'},
                'inspect':{'record'}, 'revalidate':{'record','application'}}[operation]
    need(set(inputs) == expected)
    with Capture() as capture:
        bound = sources(capture); policy = programme(capture)
        private_inputs = list(inputs.values())
        raws = {name:read(capture,path) for name,path in inputs.items()}
        need(sum(map(len,raws.values())) <= 2_000_000)
        if operation == 'practice':
            path = ROOT/delivery().EVIDENCE
            evidence = parse(capture.read(path, MAX_INPUT, private=False))
            app = practice(policy, evidence, now); value = app
            application(value, policy)
            summary = {'state':'PRACTICE_APPLICATION_SAVED','synthetic_only':True,
                       **policy['claims']}
        elif operation == 'start':
            value = record(parse(raws['application']), [], now, bound, policy, None)
            summary = brief(value, policy, now)
        elif operation == 'revalidate':
            previous = parse(raws['record'])
            # Preserve older record bytes only as a predecessor observation. Do
            # not import an older method's approval, events or unknown policy.
            keys(previous, ('profile','programme_sha256','source_sha256','opened_at','application',
                 'actions','predecessor_sha256','state','missing_requirements','claims',
                 'evidence_authenticity_verified','declared_roles_only'))
            need(previous['profile']==PROFILE and encoded(previous['claims'])==encoded(policy['claims'])
                 and previous['evidence_authenticity_verified'] is False
                 and previous['declared_roles_only'] is True)
            fresh = application(parse(raws['application']), policy)
            previous_id = previous['application']['application_id']
            token(previous_id)
            if (previous['programme_sha256']==POLICY_SHA
                    and previous['source_sha256']==bound):
                check_record(previous,bound,policy)
                if previous['state']=='WITHDRAWN':
                    need(fresh['application_id'] != previous_id)
                else:
                    need(fresh['application_id'] == previous_id)
            else:
                # Unknown older sources cannot establish a terminal state.
                # Start a different application, never resume its identity.
                need(fresh['application_id'] != previous_id)
            value = record(fresh, [], now, bound, policy, sha(raws['record']))
            summary = brief(value, policy, now)
        else:
            value = check_record(parse(raws['record']), bound, policy)
            if operation == 'advance':
                action = parse(raws['event']); need(stamp(action['at']) <= stamp(now))
                need(len(value['actions']) < MAX_ACTIONS)
                value = record(value['application'], [*value['actions'], action],
                               value['opened_at'], bound, policy, sha(raws['record']))
            summary = brief(value, policy, now)
        need(len(encoded(value))+1 <= MAX_INPUT)
        capture.check()
        for path in private_inputs:
            private_path(capture,path)
        if output is not None:
            private_path(capture,output); capture.save(output,value,MAX_OUTPUT)
            need(capture.read(output,MAX_INPUT) == encoded(value)+b'\n')
            for path in [*private_inputs,output]:
                private_path(capture,path)
        else:
            need(operation == 'inspect')
        capture.check()
    return summary
