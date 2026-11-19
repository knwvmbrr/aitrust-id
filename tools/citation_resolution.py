"""Offline caller-declared numbered-marker associations; never a FI assertion."""
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import stat

from protocol import corpus
from protocol.normalization import NORMALIZATION_ID, normalize_nfc

ROOT = Path(__file__).absolute().parents[1]
METHOD = 'declared-local-numbered-citations/1.0.0'
PROFILE = 'literal-ascii-brackets-1-to-9999/v1'
MAX_SUBJECT_BYTES = 32000
MAX_SUBJECT_CHARACTERS = 8000
MAX_MARKERS = 256
MAX_MAPPINGS = 128
MAX_SIDECAR_BYTES = 65536
MAX_REPORT_BYTES = 262144
SOURCES = ('tools/citation_resolution.py', 'scripts/citation-resolution.py',
           'protocol/corpus.py', 'protocol/normalization.py', 'protocol/unicode15-data.json')


class CitationError(ValueError):
    """Refusals never include caller-controlled values."""


class OutputCommitUncertain(CitationError):
    """A complete final output may exist; inspect it before attempting another write."""
    output_may_exist = True

    def __init__(self):
        super().__init__('Local citation output commit uncertain.')


def need(condition):
    if not condition:
        raise CitationError('Local citation evidence unavailable.')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def encoded(value):
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(',', ':'),
                      allow_nan=False).encode('ascii')


def snapshot(info):
    return (info.st_dev, info.st_ino, info.st_mode, info.st_nlink, info.st_size,
            info.st_mtime_ns, info.st_ctime_ns)


def identity(info):
    return info.st_dev, info.st_ino, info.st_mode


class Capture:
    """Retain no-follow directory/file handles and recheck before publication."""
    def __init__(self):
        self.fds = []
        self.directories = []
        self.files = []
        self.output_may_exist = False

    def parent(self, path):
        path = Path(path).absolute()
        need('..' not in path.parts and path.name not in ('', '.', '..'))
        flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_NONBLOCK
        fd = os.open(path.anchor, flags)
        self.fds.append(fd)
        for part in path.parts[1:-1]:
            child = os.open(part, flags, dir_fd=fd)
            self.fds.append(child)
            info = os.fstat(child)
            need(stat.S_ISDIR(info.st_mode))
            self.directories.append((fd, part, child, identity(info)))
            fd = child
        return fd, path.name

    def read(self, path, limit, private=True):
        need(type(limit) is int and 0 < limit <= corpus.MAX_STORE_BYTES)
        parent, name = self.parent(path)
        fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
        self.fds.append(fd)
        before = os.fstat(fd)
        need(stat.S_ISREG(before.st_mode) and before.st_nlink == 1 and 0 < before.st_size <= limit)
        if private:
            need(before.st_uid == os.getuid() and stat.S_IMODE(before.st_mode) == 0o600)
        raw = bytearray()
        while len(raw) <= limit:
            chunk = os.read(fd, min(65536, limit + 1 - len(raw)))
            if not chunk:
                break
            raw.extend(chunk)
        need(len(raw) == before.st_size and snapshot(before) == snapshot(os.fstat(fd)))
        self.files.append((parent, name, fd, snapshot(before)))
        return bytes(raw)

    def check(self):
        for parent, name, fd, expected in self.directories:
            need(identity(os.fstat(fd)) == expected == identity(os.stat(name, dir_fd=parent, follow_symlinks=False)))
        for parent, name, fd, expected in self.files:
            need(snapshot(os.fstat(fd)) == expected == snapshot(os.stat(name, dir_fd=parent, follow_symlinks=False)))

    def save(self, output, value, limit):
        path = Path(output).absolute()
        need(not path.is_relative_to(ROOT))
        raw = encoded(value) + b'\n'
        need(len(raw) <= limit)
        parent, name = self.parent(path)
        info = os.fstat(parent)
        need(info.st_uid == os.getuid() and stat.S_IMODE(info.st_mode) == 0o700)
        # Never follow or replace even a dangling existing destination.
        try:
            os.stat(name, dir_fd=parent, follow_symlinks=False)
        except FileNotFoundError:
            pass
        else:
            raise CitationError('Local citation evidence unavailable.')
        temporary = '.citation-' + secrets.token_hex(16)
        fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                     0o600, dir_fd=parent)
        self.fds.append(fd)
        error = None
        may_exist = False
        try:
            # Capture alone owns the raw handle, including construction failure.
            with os.fdopen(fd, 'wb', closefd=False) as stream:
                os.fchmod(stream.fileno(), 0o600)
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
            self.check()
            # Atomic no-replace publication of complete bytes. An unexpected
            # link error can itself have an uncertain filesystem outcome.
            try:
                os.link(temporary, name, src_dir_fd=parent, dst_dir_fd=parent, follow_symlinks=False)
            except FileExistsError:
                raise
            except BaseException:
                may_exist = self.output_may_exist = True
                raise
            may_exist = self.output_may_exist = True
        except BaseException as failure:
            error = failure
        # Attempt temporary cleanup exactly once. Never remove a final file or
        # assert rollback after crossing the publication boundary.
        try:
            os.unlink(temporary, dir_fd=parent)
        except BaseException as failure:
            if error is None:
                error = failure
        if error is None and may_exist:
            try:
                os.fsync(parent)
            except BaseException as failure:
                error = failure
        if error is not None:
            if may_exist:
                raise OutputCommitUncertain() from None
            raise error

    def close(self):
        owned = self.fds
        self.fds = []
        error = None
        for fd in reversed(owned):
            try:
                os.close(fd)
            except BaseException as failure:
                if error is None:
                    error = failure
        if error is not None:
            if self.output_may_exist:
                raise OutputCommitUncertain() from None
            raise CitationError('Local citation evidence unavailable.') from None

    def __enter__(self):
        return self

    def __exit__(self, kind, value, traceback):
        try:
            self.close()
        except BaseException:
            if self.output_may_exist:
                raise OutputCommitUncertain() from None
            if kind is None:
                raise
            # Keep a primary pre-publication refusal. All closes were attempted.
            return False
        if kind is not None and self.output_may_exist:
            raise OutputCommitUncertain() from None


def current_sources(capture):
    return {name: sha(capture.read(ROOT / name, 1000000, private=False)) for name in SOURCES}


def subject(raw):
    need(type(raw) is bytes and 0 < len(raw) <= MAX_SUBJECT_BYTES)
    text = raw.decode('utf-8', 'strict')
    need(bool(text.strip()) and '\0' not in text and len(text) <= MAX_SUBJECT_CHARACTERS)
    normalized = normalize_nfc(text)
    need(len(normalized) <= MAX_SUBJECT_CHARACTERS)
    return normalized


def markers(text):
    """Return every bracket occurrence; never salvage an inner numeric token."""
    result = []
    at = 0
    while at < len(text):
        if text[at] not in '[]':
            at += 1
            continue
        start = at
        reason = 'unmatched_bracket'
        if text[at] == ']':
            at += 1
        else:
            depth = 1
            at += 1
            nested = False
            while at < len(text) and depth:
                if text[at] == '[':
                    depth += 1
                    nested = True
                elif text[at] == ']':
                    depth -= 1
                at += 1
            token = text[start:at]
            match = re.fullmatch(r'\[([1-9][0-9]{0,3})\]', token, re.ASCII)
            tail = text[at:]
            if depth:
                reason = 'unmatched_bracket'
            elif nested:
                reason = 'nested_brackets'
            elif start and text[start - 1] == '\\':
                reason = 'escaped_bracket'
            elif tail.startswith(('(', ':', '[')):
                reason = 'link_or_definition_syntax'
            elif not match:
                reason = 'unsupported_bracket_syntax'
            else:
                reason = None
            # A balanced label's target is opaque even when the label was
            # already rejected as nested/escaped. Never salvage target numbers.
            if not depth and tail.startswith(('(', ':', '[')):
                if tail[0] in '([':
                    opening = tail[0]
                    closing = ')' if opening == '(' else ']'
                    level = 1
                    at += 1
                    while at < len(text) and level:
                        if text[at] == opening:
                            level += 1
                        elif text[at] == closing:
                            level -= 1
                        at += 1
                else:
                    end = text.find('\n', at)
                    at = len(text) if end == -1 else end
        need(len(result) < MAX_MARKERS)
        result.append({'span': [start, at], 'number': int(match.group(1)) if reason is None else None,
                       'unsupported_reason': reason})
    return result


def mapping_pairs(pairs, documents):
    need(type(pairs) is list and len(pairs) <= MAX_MAPPINGS)
    result = []
    seen = set()
    for pair in pairs:
        need(type(pair) in (list, tuple) and len(pair) == 2)
        number, document_id = pair
        need(type(number) is int and 1 <= number <= 9999 and number not in seen)
        need(type(document_id) is str and corpus.valid_id(document_id) and document_id in documents)
        seen.add(number)
        document = documents[document_id]
        result.append({'number': number, 'document_id': document_id,
                       'document_sha256': document['sha256'],
                       'normalized_document_sha256': sha(normalize_nfc(document['text']).encode('utf-8'))})
    return sorted(result, key=lambda row: row['number'])


def _prepare(corpus_raw, subject_raw, pairs, sources):
    attached = corpus.parse(corpus_raw)
    text = subject(subject_raw)
    # Refuse excessive bracket input when preparing, not only during checking.
    markers(text)
    mappings = mapping_pairs(pairs, {d['id']: d for d in attached['documents']})
    value = {'format': 'local-citation-sidecar/v1', 'method': METHOD, 'marker_profile': PROFILE,
             'raw_subject_sha256': sha(subject_raw), 'subject_sha256': sha(text.encode('utf-8')),
             'subject_characters': len(text), 'normalization_id': NORMALIZATION_ID,
             'offset_unit': 'NFC_unicode_codepoint', 'corpus_file_sha256': sha(corpus_raw),
             'corpus_manifest_sha256': attached['manifest_sha256'],
             'mappings': mappings, 'source_sha256': sources}
    need(len(encoded(value)) + 1 <= MAX_SIDECAR_BYTES)
    return value


def prepare(corpus_raw, subject_raw, pairs):
    """Create a sidecar value from captured bytes; source identities are current."""
    with Capture() as capture:
        value = _prepare(corpus_raw, subject_raw, pairs, current_sources(capture))
        capture.check()
        return value


def parse_sidecar(raw):
    need(type(raw) is bytes and 0 < len(raw) <= MAX_SIDECAR_BYTES)
    def integer(value):
        need(len(value) <= 5)
        return int(value)
    def unsupported(_):
        raise CitationError('Local citation evidence unavailable.')
    return json.loads(raw, object_pairs_hook=corpus.unique_pairs, parse_int=integer,
                      parse_float=unsupported, parse_constant=unsupported)


def _check(corpus_raw, subject_raw, sidecar_raw, sources):
    value = parse_sidecar(sidecar_raw)
    fields = {'format', 'method', 'marker_profile', 'raw_subject_sha256', 'subject_sha256',
              'subject_characters', 'normalization_id', 'offset_unit', 'corpus_file_sha256',
              'corpus_manifest_sha256', 'mappings', 'source_sha256'}
    need(type(value) is dict and set(value) == fields and type(value['subject_characters']) is int)
    need(type(value['mappings']) is list and len(value['mappings']) <= MAX_MAPPINGS)
    pairs = []
    for row in value['mappings']:
        need(type(row) is dict and set(row) == {'number', 'document_id', 'document_sha256', 'normalized_document_sha256'})
        pairs.append((row['number'], row['document_id']))
    expected = _prepare(corpus_raw, subject_raw, pairs, sources)
    need(encoded(value) == encoded(expected))
    text = subject(subject_raw)
    selected = {row['number']: row for row in value['mappings']}
    rows = []
    counts = {'resolved-in-attached-corpus': 0, 'unresolved-in-attached-corpus': 0, 'unsupported': 0}
    for marker in markers(text):
        association = selected.get(marker['number'])
        state = ('unsupported' if marker['unsupported_reason'] else
                 'resolved-in-attached-corpus' if association else 'unresolved-in-attached-corpus')
        counts[state] += 1
        rows.append({**marker, 'state': state, 'declaration': association})
    summary = {'format': 'local-citation-summary/v1', 'method': METHOD,
               'state': 'COMPLETE', 'marker_occurrences': len(rows), 'counts': counts,
               'network_used': False, 'inference_used': False, 'tags': [],
               'source_support_established': False, 'truth_established': False,
               'independent_accuracy_evidence': False, 'subject_text_included': False}
    detail = {**summary, 'format': 'local-citation-evidence/v1', 'bindings': value,
              'sidecar_file_sha256': sha(sidecar_raw), 'markers': rows,
              'quote_code_or_assertion_context_interpreted': False,
              'source_authenticity_or_freshness_established': False,
              'other_citation_forms_evaluated': False}
    need(len(encoded(detail)) + 1 <= MAX_REPORT_BYTES)
    return summary, detail


def check(corpus_raw, subject_raw, sidecar_raw):
    """Validate a captured sidecar and return text-free summary/private evidence."""
    with Capture() as capture:
        value = _check(corpus_raw, subject_raw, sidecar_raw, current_sources(capture))
        capture.check()
        return value
