"""Bounded offline package-name resemblance, never a maliciousness verdict."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
from urllib.parse import urlsplit

from protocol.corpus import CorpusError, encoded, read_regular, unique_pairs

ROOT = Path(__file__).resolve().parents[1]
METHOD = 'package-proximity-levenshtein/1.0.0'
FORMAT = 'ranked-package-snapshot/v1'
MAX_BYTES = 1_000_000
MAX_PACKAGES = 2048
MAX_NAMES = 16
MAX_CHARACTERS = 4096


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def parse(raw):
    try:
        return json.loads(raw.decode('utf-8', errors='strict'),
                          object_pairs_hook=unique_pairs,
                          parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
    except (ValueError, UnicodeError, RecursionError):
        raise CorpusError('Invalid package reference JSON.') from None


def canonical(name, ecosystem):
    if not isinstance(name, str) or not name.isascii() or not 1 <= len(name) <= 128:
        raise CorpusError('Invalid or unsupported package name.')
    if ecosystem == 'pypi':
        if not re.fullmatch(r'[A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?', name):
            raise CorpusError('Invalid or unsupported package name.')
        return re.sub(r'[-_.]+', '-', name).lower()
    if ecosystem == 'npm':
        # Conservative supported subset of URL-safe npm names, not a registry validator.
        part = r'[a-z0-9][a-z0-9._-]*'
        scoped = r'@[a-z0-9._-]+/[a-z0-9._-]+'
        if not re.fullmatch(r'(?:' + part + r'|' + scoped + r')', name):
            raise CorpusError('Invalid or unsupported package name.')
        return name
    raise CorpusError('Unsupported package ecosystem.')


def instant(value):
    if not isinstance(value, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z', value):
        raise CorpusError('Measurement dates must use UTC seconds.')
    try:
        return datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError:
        raise CorpusError('Invalid measurement date.') from None


def validate_source(data):
    if not isinstance(data, dict) or set(data) != {'format', 'ecosystem', 'measurement', 'packages'} or data['format'] != 'ranked-package-input/v1':
        raise CorpusError('Invalid ranked package input.')
    if data['ecosystem'] not in ('pypi', 'npm'):
        raise CorpusError('Unsupported package ecosystem.')
    measurement = data['measurement']
    if not isinstance(measurement, dict) or set(measurement) != {'start', 'end', 'metric', 'source_url', 'synthetic'}:
        raise CorpusError('Missing measurement provenance.')
    if instant(measurement['start']) >= instant(measurement['end']) or type(measurement['synthetic']) is not bool:
        raise CorpusError('Invalid measurement interval or kind.')
    if measurement['metric'] != 'download_count_in_interval':
        raise CorpusError('Unsupported ranking metric.')
    source = measurement['source_url']
    if not isinstance(source, str) or len(source) > 512 or not source.isascii() or any(ord(c) < 33 for c in source):
        raise CorpusError('Invalid reference source URL.')
    try:
        url = urlsplit(source)
        if url.scheme != 'https' or not url.hostname or url.username or url.password or url.fragment or url.port not in (None, 443):
            raise ValueError()
    except ValueError:
        raise CorpusError('Invalid reference source URL.') from None
    packages = data['packages']
    if not isinstance(packages, list) or not 1 <= len(packages) <= MAX_PACKAGES:
        raise CorpusError('Invalid ranked package count.')
    names = set()
    previous = None
    for position, package in enumerate(packages, 1):
        if not isinstance(package, dict) or set(package) != {'rank', 'name', 'downloads'}:
            raise CorpusError('Invalid ranked package record.')
        rank, downloads = package['rank'], package['downloads']
        if type(rank) is not int or rank != position or type(downloads) is not int or not 0 <= downloads <= 10**15:
            raise CorpusError('Invalid package rank or count.')
        name = canonical(package['name'], data['ecosystem'])
        if name in names or previous is not None and downloads > previous:
            raise CorpusError('Duplicate names or inconsistent package ranking.')
        names.add(name)
        previous = downloads
    return data


def create(source, output):
    raw = read_regular(source, MAX_BYTES)
    data = validate_source(parse(raw))
    if instant(data['measurement']['end']) > datetime.now(timezone.utc):
        raise CorpusError('Future measurement cannot be imported.')
    content = {'format': FORMAT, 'source_sha256': sha(raw), 'input': data}
    record = dict(content, manifest_sha256=sha(encoded(content)))
    serialized = encoded(record)
    if len(serialized) > MAX_BYTES:
        raise CorpusError('Serialized package snapshot exceeds the limit.')
    target = Path(output).expanduser().absolute()
    if target.resolve().is_relative_to(ROOT):
        raise CorpusError('Keep supplied package snapshots outside source control.')
    target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    info = target.parent.lstat()
    if target.parent.is_symlink() or info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise CorpusError('Snapshot directory must be private and owner-held.')
    try:
        fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    except OSError:
        raise CorpusError('Choose a new private snapshot path.') from None
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(serialized)
            stream.flush()
            os.fsync(stream.fileno())
    except BaseException:
        target.unlink(missing_ok=True)
        raise
    return {'format': FORMAT, 'manifest_sha256': record['manifest_sha256'],
            'source_sha256': record['source_sha256'], 'packages': len(data['packages']),
            'synthetic': data['measurement']['synthetic'], 'network_used': False,
            'ranking_independently_verified': False, 'tags': []}


def validate_record(record):
    if not isinstance(record, dict) or set(record) != {'format', 'source_sha256', 'input', 'manifest_sha256'} or record['format'] != FORMAT:
        raise CorpusError('Invalid package snapshot envelope.')
    if not isinstance(record['source_sha256'], str) or not re.fullmatch(r'[0-9a-f]{64}', record['source_sha256']):
        raise CorpusError('Invalid source digest.')
    validate_source(record['input'])
    content = {key: value for key, value in record.items() if key != 'manifest_sha256'}
    if sha(encoded(content)) != record['manifest_sha256']:
        raise CorpusError('Package snapshot integrity check failed.')
    return record


def load(path):
    return validate_record(parse(read_regular(path, MAX_BYTES, private=True)))


def distance(left, right):
    """Exact Levenshtein up to 2; returns 3 when more distant. Five-cell band."""
    if abs(len(left) - len(right)) > 2:
        return 3
    previous = {i: i for i in range(min(len(right), 2) + 1)}
    for i, char in enumerate(left, 1):
        current = {}
        for j in range(max(0, i - 2), min(len(right), i + 2) + 1):
            if j == 0:
                current[j] = i
            else:
                current[j] = min(previous.get(j, 3) + 1,
                                 current.get(j - 1, 3) + 1,
                                 previous.get(j - 1, 3) + (char != right[j - 1]))
        if min(current.values(), default=3) > 2:
            return 3
        previous = current
    return min(3, previous.get(len(right), 3))


def observe(record, subject, top_n=None):
    # Validate even for in-process callers, not only CLI load().
    validate_record(record)
    data = record['input']
    if top_n is None:
        top_n = len(data['packages'])
    if type(top_n) is not int or not 1 <= top_n <= len(data['packages']):
        raise CorpusError('Invalid top-N selection.')
    if not isinstance(subject, str) or not subject.isascii() or not subject.strip() or len(subject) > MAX_CHARACTERS:
        raise CorpusError('Supply supported package names within the input limit.')
    units = []
    offset = 0
    for line in subject.splitlines(keepends=True):
        body = line.rstrip('\r\n')
        left, right = len(body) - len(body.lstrip(' \t')), len(body.rstrip(' \t'))
        if right > left:
            value = body[left:right]
            units.append((offset + left, offset + right, canonical(value, data['ecosystem'])))
        offset += len(line)
    if not 1 <= len(units) <= MAX_NAMES:
        raise CorpusError('Supply one to sixteen package-name lines.')
    reference = [(p, canonical(p['name'], data['ecosystem'])) for p in data['packages'][:top_n]]
    exact = {name for _, name in reference}
    findings, matches, exact_count = [], 0, 0
    for start, end, name in units:
        if name in exact:
            exact_count += 1
            continue
        for package, candidate in reference:
            separation = distance(name, candidate)
            if separation in (1, 2):
                matches += 1
                findings.append({'id': 'sig.typosquat.v1', 'spans': [[start, end]],
                                 'distance': separation, 'reference_rank': package['rank'],
                                 'reference_name': package['name'], 'meaning': 'name_similarity_only'})
    findings.sort(key=lambda f: (f['distance'], f['spans'][0][0], f['reference_rank']))
    return {'format': 'package-proximity-observation/v1', 'method': METHOD,
            'method_sha256': sha(Path(__file__).read_bytes()), 'subject_sha256': sha(subject.encode('ascii')),
            'subject_characters': len(subject), 'offset_unit': 'original_unicode_codepoint',
            'ecosystem': data['ecosystem'], 'manifest_sha256': record['manifest_sha256'],
            'source_sha256': record['source_sha256'], 'measurement': data['measurement'],
            'top_n': top_n, 'checked_names': len(units), 'exact_reference_matches': exact_count,
            'state': 'SIMILAR_NAME' if matches else 'NO_SIMILAR_NAME',
            'findings': findings[:32], 'total_matches': matches, 'maximum_findings': 32,
            'reference_freshness': 'unestablished', 'ranking_independently_verified': False,
            'maliciousness_established': False, 'independent_accuracy_evidence': False,
            'network_used': False, 'tags': []}
