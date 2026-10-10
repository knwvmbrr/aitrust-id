"""Bounded pinned input/hashed lock synchronization, using the standard library."""
import re
from pathlib import Path
from urllib.parse import urlsplit


def pin(requirement):
    match = re.fullmatch(r'([A-Za-z0-9](?:[A-Za-z0-9_.-]*[A-Za-z0-9])?)(?:\[([A-Za-z0-9_,.-]+)\])?(?:==([^\s]+)| @ (https://\S+))', requirement)
    if not match:
        raise ValueError('Unsupported or unpinned Python input')
    name = re.sub(r'[-_.]+', '-', match[1]).lower()
    extras = tuple(sorted(match[2].lower().split(','))) if match[2] else ()
    if extras and (name, extras) != ('uvicorn', ('standard',)):
        raise ValueError('Unreviewed Python extras')
    if match[3]:
        value = match[3]
        if not re.fullmatch(r'[0-9]+(?:\.[0-9]+)*(?:(?:a|b|rc)[0-9]+)?(?:\.post[0-9]+)?(?:\.dev[0-9]+)?(?:\+[A-Za-z0-9]+(?:[-_.][A-Za-z0-9]+)*)?', value):
            raise ValueError('Unsupported Python version pin')
        kind = 'version'
    else:
        value = match[4]
        url = urlsplit(value)
        if (not url.hostname or url.username or url.password or url.query
                or url.fragment and not re.fullmatch(r'sha256=[a-f0-9]{64}', url.fragment)):
            raise ValueError('Unsafe Python source URL')
        kind = 'url'
    return {'name': name, 'kind': kind, 'value': value, 'extras': extras}


def pinned_inputs(text):
    rows = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        row = pin(line.split(' #', 1)[0].rstrip())
        if row['name'] in rows:
            raise ValueError('Duplicate normalized Python input')
        rows[row['name']] = row
    if not rows:
        raise ValueError('Empty Python input')
    return rows


def python_lock(text):
    blocks, current = [], []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        if line.endswith('\\'):
            current.append(line[:-1].strip())
            continue
        current.append(line)
        blocks.append(' '.join(current))
        current = []
    if current:
        raise ValueError('Unfinished requirement')
    rows, names = [], set()
    for block in blocks:
        parts = block.split(' --hash=')
        requirement, hashes = parts[0], parts[1:]
        if not hashes or any(not re.fullmatch(r'sha256:[a-f0-9]{64}', x) for x in hashes):
            raise ValueError('Missing or malformed package hashes')
        parsed = pin(requirement)
        name = parsed['name']
        if name in names:
            raise ValueError('Duplicate requirement')
        names.add(name)
        if parsed['kind'] == 'url':
            fragment = urlsplit(parsed['value']).fragment
            if fragment and fragment not in {h.replace(':', '=') for h in hashes}:
                raise ValueError('URL artifact hash disagrees')
        rows.append({'name': name, 'requirement': requirement, 'artifact_hashes': sorted(set(hashes))})
    if not rows:
        raise ValueError('Empty lock')
    return rows


def verify_inputs(manifest, lock, frozen=None):
    direct = pinned_inputs(manifest)
    locked = {row['name']: pin(row['requirement']) for row in python_lock(lock)}
    fixed = pinned_inputs(frozen) if frozen is not None else None

    def same(expected, actual):
        return actual is not None and (expected['kind'], expected['value']) == (actual['kind'], actual['value'])

    for name, expected in direct.items():
        if not same(expected, locked.get(name)):
            raise ValueError('Python manifest and installed lock disagree: ' + name)
        if fixed is not None and not same(expected, fixed.get(name)):
            raise ValueError('Python manifest and frozen input disagree: ' + name)
        if expected['extras']:
            required = {'httptools', 'python-dotenv', 'pyyaml', 'uvloop', 'watchfiles', 'websockets'}
            if not required <= locked.keys():
                raise ValueError('Accepted uvicorn standard extra is incomplete')
    if fixed is not None:
        for name, expected in fixed.items():
            if not same(expected, locked.get(name)):
                raise ValueError('Frozen Python input and installed lock disagree: ' + name)
    return {'direct_pins': len(direct), 'frozen_pins': len(fixed) if fixed is not None else None,
            'manifest_matches_install_lock': True, 'frozen_input_checked': fixed is not None}


def verify_root_inputs(root):
    """Same four active inputs at review, inventory and deployment boundaries."""
    root = Path(root)
    results = {}

    def read(name):
        path = root / name
        for candidate in (path, *path.parents):
            if candidate.is_symlink():
                raise ValueError('Python dependency input symlink refused')
            if candidate == root:
                break
        if not path.is_file() or path.stat().st_size > 500_000:
            raise ValueError('Python dependency input missing or oversized')
        return path.read_text()

    for directory in ['eval', 'services/gateway', 'services/evaluator', 'services/anonymizer']:
        results[directory] = verify_inputs(read(directory + '/requirements.txt'),
                                          read(directory + '/requirements.lock'),
                                          read(directory + '/requirements.freeze') if directory.startswith('services/') else None)
    return results
