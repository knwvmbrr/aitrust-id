"""Bounded owner-held literal reference corpus. Never classifies or fetches text."""
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import unicodedata

VERSION = 'local-reference-corpus/v1'
MAX_DOCUMENTS = 32
MAX_DOCUMENT_BYTES = 800_000
MAX_TOTAL_BYTES = 2_000_000
MAX_STORE_BYTES = 4_000_000
MAX_QUERY_CHARACTERS = 2_000
ROOT = Path(__file__).resolve().parents[1]


class CorpusError(ValueError):
    """Fixed error messages contain no source or credential values."""


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'),
                      allow_nan=False).encode('utf-8')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def text(raw):
    try:
        value = raw.decode('utf-8', errors='strict')
    except UnicodeDecodeError:
        raise CorpusError('Source must be valid UTF-8 text.') from None
    if not value.strip() or len(value) > 200_000 or '\x00' in value:
        raise CorpusError('Source must be nonempty text within the character limit.')
    return value


def read_regular(path, limit, private=False):
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except OSError:
        raise CorpusError('Cannot open a regular, non-symlink source.') from None
    with os.fdopen(fd, 'rb') as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode):
            raise CorpusError('Only regular files are supported.')
        if private and (info.st_uid != os.getuid() or info.st_mode & 0o077):
            raise CorpusError('Corpus must be owner-held and private (0600).')
        raw = stream.read(limit + 1)
    if len(raw) > limit:
        raise CorpusError('File exceeds the byte limit.')
    return raw


def valid_id(value):
    return isinstance(value, str) and re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}', value)


def create(sources, output):
    if not 1 <= len(sources) <= MAX_DOCUMENTS:
        raise CorpusError('Attach between one and 32 documents.')
    documents, ids, total = [], set(), 0
    for identity, path in sources:
        if not valid_id(identity) or identity in ids:
            raise CorpusError('Document IDs must be unique safe identifiers.')
        if Path(path).suffix.lower() not in ('.txt', '.md'):
            raise CorpusError('Only .txt and .md source files are supported.')
        raw = read_regular(path, MAX_DOCUMENT_BYTES)
        value = text(raw)
        total += len(raw)
        if total > MAX_TOTAL_BYTES:
            raise CorpusError('Corpus exceeds the total byte limit.')
        ids.add(identity)
        documents.append({'id': identity, 'sha256': sha(raw), 'text': value})
    content = {'format': VERSION, 'documents': sorted(documents, key=lambda d: d['id'])}
    record = dict(content, manifest_sha256=sha(encoded(content)))
    raw = encoded(record)
    if len(raw) > MAX_STORE_BYTES:
        raise CorpusError('Serialized corpus exceeds the storage limit.')
    output = Path(output).expanduser().absolute()
    if output.resolve().is_relative_to(ROOT):
        raise CorpusError('Keep reference text outside the source checkout.')
    output.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    info = output.parent.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise CorpusError('Corpus directory must be owner-held and private (0700).')
    # The directory owner controls it; O_EXCL avoids replacement and link following.
    try:
        fd = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    except OSError:
        raise CorpusError('Choose a new, writable private corpus path.') from None
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
    except BaseException:
        output.unlink(missing_ok=True)
        raise
    return summary(record)


def unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise CorpusError('Duplicate manifest keys are invalid.')
        result[key] = value
    return result


def load(path):
    raw = read_regular(Path(path).expanduser(), MAX_STORE_BYTES, private=True)
    try:
        record = json.loads(raw, object_pairs_hook=unique_pairs,
                            parse_constant=lambda _: (_ for _ in ()).throw(CorpusError('Invalid JSON number.')))
        if not isinstance(record, dict) or set(record) != {'format', 'documents', 'manifest_sha256'}:
            raise CorpusError('Invalid corpus envelope.')
        if record['format'] != VERSION or not isinstance(record['documents'], list):
            raise CorpusError('Unsupported corpus format.')
        docs = record['documents']
        if not 1 <= len(docs) <= MAX_DOCUMENTS:
            raise CorpusError('Invalid document count.')
        ids, total = [], 0
        for d in docs:
            if not isinstance(d, dict) or set(d) != {'id', 'sha256', 'text'} or not valid_id(d['id']) or not isinstance(d['text'], str):
                raise CorpusError('Invalid source record.')
            data = d['text'].encode('utf-8', errors='strict')
            text(data)
            if len(data) > MAX_DOCUMENT_BYTES or sha(data) != d['sha256']:
                raise CorpusError('Source integrity check failed.')
            total += len(data)
            ids.append(d['id'])
        if ids != sorted(set(ids)) or total > MAX_TOTAL_BYTES:
            raise CorpusError('Invalid source ordering, identity or size.')
        content = {'format': record['format'], 'documents': docs}
        if sha(encoded(content)) != record['manifest_sha256']:
            raise CorpusError('Manifest integrity check failed.')
        return record
    except (UnicodeError, json.JSONDecodeError, RecursionError, TypeError, KeyError):
        raise CorpusError('Invalid or corrupted corpus.') from None


def summary(record):
    return {'format': VERSION, 'manifest_sha256': record['manifest_sha256'],
            'documents': [{'id': d['id'], 'sha256': d['sha256'], 'characters': len(d['text'])}
                          for d in record['documents']], 'network_used': False,
            'tag_assertion': False}


def query(record, phrase):
    if not isinstance(phrase, str) or not phrase.strip() or len(phrase) > MAX_QUERY_CHARACTERS:
        raise CorpusError('Query must contain one to 2,000 characters.')
    try:
        phrase.encode('utf-8', errors='strict')
    except UnicodeError:
        raise CorpusError('Query must use valid Unicode.') from None
    needle = unicodedata.normalize('NFC', phrase)
    matches = []
    for document in record['documents']:
        normalized = unicodedata.normalize('NFC', document['text'])
        start = 0
        while len(matches) < 10:
            at = normalized.find(needle, start)
            if at < 0:
                break
            matches.append({'document_id': document['id'], 'document_sha256': document['sha256'],
                            'normalized_source_sha256': sha(normalized.encode('utf-8')),
                            'source_span': [at, at + len(needle)], 'query_span': [0, len(needle)],
                            'offset_unit': 'NFC_unicode_codepoint', 'passage': normalized[at:at+len(needle)]})
            start = at + len(needle)
        if len(matches) == 10:
            break
    return {'format': 'local-reference-match/v1', 'manifest_sha256': record['manifest_sha256'],
            'state': 'REFERENCE_MATCH' if matches else 'NO_REFERENCE_MATCH',
            'query_sha256': sha(needle.encode('utf-8')), 'matches': matches,
            'match_limit': 10, 'tag_assertion': False, 'independently_validated': False,
            'meaning': 'Literal reference match only; no truth or contradiction verdict.'}
