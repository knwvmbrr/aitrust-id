"""Change records: standard-library validation shared by writer, CI and tests."""
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile

_GIT_DIRS = {}

ROOT = Path(__file__).resolve().parents[1]
EVENT_DIR = 'runs/changes'
# These artifacts are generated or independently described by their events.
EXCLUDED = {'CHANGELOG.md'}
VALIDATION_CLAIM = re.compile(r'\b(?:independently validated|validated for release|release[- ]validated|release gate (?:passed|cleared|met)|certified accuracy)\b', re.I)

def git(root, *args):
    prefix = []
    env = None
    if root in _GIT_DIRS:
        git_dir, index_path = _GIT_DIRS[root]
        prefix = ['--git-dir', git_dir, '--work-tree', str(root)]
        env = dict(os.environ)
        for key in ('GIT_DIR', 'GIT_WORK_TREE', 'GIT_COMMON_DIR', 'GIT_PREFIX'):
            env.pop(key, None)
        env['GIT_INDEX_FILE'] = index_path
    return subprocess.check_output(['git', *prefix, *args], cwd=root, env=env).decode()

def safe_path(root, name):
    if not isinstance(name, str) or not name or '\\' in name or Path(name).is_absolute() or '..' in Path(name).parts:
        raise ValueError('Invalid repository-relative path: ' + str(name))
    p = root / name
    if not p.resolve().is_relative_to(root.resolve()):
        raise ValueError('Path escapes repository: ' + name)
    return p

def digest(root, name):
    p = safe_path(root, name)
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None

def ignored(name):
    return name in EXCLUDED or name.startswith(EVENT_DIR + '/') or name.startswith(('output/', 'site/dist/')) or 'node_modules' in Path(name).parts

def changes(root, base=None, head='HEAD'):
    if base:
        names = git(root, 'diff', '--no-renames', '--name-only', '-z', base, head).split('\0')
    else:
        names = git(root, 'diff', '--no-renames', '--name-only', '-z', 'HEAD').split('\0')
        names += git(root, 'ls-files', '--others', '--exclude-standard', '-z').split('\0')
    return sorted({n for n in names if n and not ignored(n)})

def known_scope(root):
    ids = {r['id'] for r in json.loads((root / 'docs/master-scope.json').read_text())['records']}
    ids.update(p['id'] for p in json.loads((root / 'docs/scope-delivery.json').read_text())['packages'])
    return ids

def entry(record, name):
    return (f"### {record['id']}\n\n"
            f"Recorded {record['recorded_at']} · Contributor: {record['author']} · {record['kind']}\n\n"
            f"- **Changed.** {record['changed']}\n"
            f"- **Evidence.** {record['proves']} [Change record](./{name}).\n"
            f"- **Not claimed.** {record['limits']}\n")

def validate_record(root, record, name, current=False):
    errors = []
    try:
        if record['schema_version'] != 1 or record['claim_level'] != 'engineering_only' or record['independent_release_validated'] is not False:
            raise ValueError('Unsupported claim level; engineering checks cannot grant tag release validation')
        if record['kind'] not in ('change', 'retrospective'):
            raise ValueError('Invalid kind')
        if not re.fullmatch(r'[a-z0-9][a-z0-9-]{3,120}', record['id']) or name != EVENT_DIR + '/' + record['id'] + '.json':
            raise ValueError('ID/path mismatch')
        when = dt.datetime.fromisoformat(record['recorded_at'])
        if when.utcoffset() != dt.timedelta(0):
            raise ValueError('UTC timestamp required')
        if not isinstance(record['author'], str) or not record['author'].strip() or '\n' in record['author'] or len(record['author']) > 100:
            raise ValueError('Explicit contributor required')
        for field in ('changed', 'proves', 'limits'):
            if not isinstance(record[field], str) or not record[field].strip() or '\n' in record[field]:
                raise ValueError('Missing single-line ' + field)
        if VALIDATION_CLAIM.search(record['changed'] + ' ' + record['proves']):
            raise ValueError('Independent release claims require a separate acceptance contract, not this log')
        if not record['scope_ids'] or len(set(record['scope_ids'])) != len(record['scope_ids']) or not set(record['scope_ids']).issubset(known_scope(root)):
            raise ValueError('Missing, duplicate or unknown scope IDs')
        if not re.fullmatch(r'[0-9a-f]{40}', record['source_base']):
            raise ValueError('Missing source base')
        if record['kind'] == 'retrospective' and not re.fullmatch(r'[0-9a-f]{40}', record.get('historical_source_commit', '')):
            raise ValueError('Retrospective record must identify historical source, not invent a finish date')
        files = record['files']
        if not isinstance(files, dict) or (not files and record['kind'] == 'change'):
            raise ValueError('Changed file hashes required')
        for f, h in files.items():
            safe_path(root, f)
            if ignored(f) or (h is not None and not re.fullmatch(r'[0-9a-f]{64}', h)):
                raise ValueError('Invalid changed file/hash: ' + f)
            # Current matching is done by coverage; a subsequent event may supersede this one.
        if not record['evidence'] and not record['checks']:
            raise ValueError('Actual evidence or executed check required')
        for e in record['evidence']:
            safe_path(root, e['path'])
            if not re.fullmatch(r'[0-9a-f]{64}', e['sha256']):
                raise ValueError('Invalid evidence hash')
            if current and digest(root, e['path']) != e['sha256']:
                raise ValueError('Missing or changed evidence: ' + e['path'])
        for check in record['checks']:
            if not isinstance(check['argv'], list) or not check['argv'] or not all(isinstance(a, str) for a in check['argv']) or type(check['exit_status']) is not int or check['exit_status'] != 0 or check['pass'] is not True:
                raise ValueError('Check did not pass or has invalid argv')
            if dt.datetime.fromisoformat(check['finished_at']).utcoffset() != dt.timedelta(0):
                raise ValueError('Check timestamp needs UTC')
    except (KeyError, TypeError, ValueError) as exc:
        errors.append(f'{name}: {exc}')
    return errors

def verify(root=ROOT, base=None, head='HEAD'):
    errors = []
    records = {}
    log = (root / 'CHANGELOG.md').read_text()
    for p in sorted((root / EVENT_DIR).glob('*.json')):
        name = p.relative_to(root).as_posix()
        try:
            r = json.loads(p.read_text())
        except (ValueError, OSError) as exc:
            errors.append(name + ': ' + str(exc)); continue
        found = validate_record(root, r, name)
        errors += found
        if not found:
            records[name] = r
            if entry(r, name) not in log:
                errors.append(name + ': exact human entry missing or inconsistent')
    if not records:
        errors.append('No structured change records')
    previous = {}
    if base:
        old_names = git(root, 'ls-tree', '-r', '--name-only', base, EVENT_DIR).splitlines()
        for n in old_names:
            if n.endswith('.json'):
                previous[n] = git(root, 'show', base + ':' + n)
        for name, content in previous.items():
            if not (root / name).is_file() or (root / name).read_text() != content:
                errors.append('Historical change record was edited/deleted: ' + name)
    else:
        old_names = git(root, 'ls-tree', '-r', '--name-only', 'HEAD', EVENT_DIR).splitlines()
        for n in old_names:
            previous[n] = git(root, 'show', 'HEAD:' + n)
            if not (root / n).is_file() or (root / n).read_text() != previous[n]:
                errors.append('Committed change record was edited/deleted: ' + n)
    new = {n: r for n, r in records.items() if n not in previous}
    for name, r in new.items():
        errors += validate_record(root, r, name, current=True)
    changed = changes(root, base, head)
    for f in changed:
        if not any(r['kind'] == 'change' and f in r['files'] and r['files'][f] == digest(root, f) for r in new.values()):
            errors.append('New change missing fresh matching event: ' + f)
    return {'pass': not errors, 'changed_files': len(changed), 'new_records': len(new), 'total_records': len(records), 'base': base, 'head': head, 'errors': errors, 'independent_release_validated': False}


def verify_staged(root=ROOT):
    """Check exactly the index; unrelated drafts cannot be mistaken for this commit."""
    with tempfile.TemporaryDirectory(prefix='aitrust-change-index-') as directory:
        snapshot = Path(directory)
        git(root, 'checkout-index', '--all', '--prefix', directory + '/')
        index = Path(git(root, 'rev-parse', '--git-path', 'index').strip())
        if not index.is_absolute():
            index = root / index
        _GIT_DIRS[snapshot] = (git(root, 'rev-parse', '--absolute-git-dir').strip(), str(index.resolve()))
        try:
            result = verify(snapshot)
            result['mode'] = 'staged_index'
            return result
        finally:
            del _GIT_DIRS[snapshot]
