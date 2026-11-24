"""Three exact release README grants and assembled notice delivery; no SDK authority."""
from contextlib import contextmanager
import hashlib
import io
import json
import math
import os
from pathlib import Path
import signal
import stat
import sys
import time
import tomllib
import zipfile

from tools.artifact_evidence_io import Capture, snapshot

ROOT = Path(__file__).resolve().parents[1]
DATA = 'sbom/c2pa-native/project-grants.json'
DATA_SHA256 = '65f2b475e2377bc4c739e8f26906ad64de7139cd29d24bd3cf4ca54079c027a8'
PACKAGES = ('btree-range-map@0.7.2', 'range-traits@0.3.2', 'static-regular-grammar@2.0.2')
PROFILE = 'c2pa-three-project-notice-delivery/v1'
MAX_READS = 16
MAX_INPUT = 8_000_000
MAX_ARTIFACT = 131072
MAX_MEMBER = 32768
MAX_FDS = 80
SECONDS = 10
CLAIMS = {'route_admitted': False, 'native_incorporation_complete': False,
          'legal_clearance': False, 'upstream_notice_file_recovered': False}


class Unavailable(ValueError):
    def __init__(self):
        super().__init__('C2PA project notice delivery unavailable.')


class OutputUncertain(Unavailable):
    output_may_exist = True

    def __init__(self):
        ValueError.__init__(self, 'C2PA notice output may exist; inspect before using a new destination.')


def need(value):
    if not value:
        raise Unavailable()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def encoded(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode()


def parse(raw):
    def pairs(rows):
        result = {}
        for key, value in rows:
            need(key not in result)
            result[key] = value
        return result
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=lambda _: need(False))


@contextmanager
def critical():
    old = signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGALRM, signal.SIGINT})
    try:
        yield
    finally:
        signal.pthread_sigmask(signal.SIG_SETMASK, old)


def close_owned(capture, original_mask):
    error = None
    if original_mask is not None:
        try:
            signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGALRM, signal.SIGINT})
        except BaseException as failure:
            error = failure
    try:
        capture.close()
    except BaseException as failure:
        if error is None:
            error = failure
    if original_mask is not None:
        try:
            signal.pthread_sigmask(signal.SIG_SETMASK, original_mask)
        except BaseException as failure:
            if error is None:
                error = failure
    if error is not None:
        raise error


@contextmanager
def custody():
    capture = Capture()
    capture.grant_entry_clock = time.monotonic()
    original_mask = None
    try:
        # Empty blocking observes the caller mask without changing it.
        original_mask = signal.pthread_sigmask(signal.SIG_BLOCK, set())
        yield capture
    finally:
        close_owned(capture, original_mask)


class Budget:
    def __init__(self, capture):
        self.capture = capture
        self.start = getattr(capture, 'grant_entry_clock', None)
        if self.start is None:
            self.start = time.monotonic()
        self.last = self.start
        self.reads = self.bytes = 0
        self.tick()

    def tick(self):
        now = time.monotonic()
        need(type(now) in (float, int) and math.isfinite(now)
             and type(self.start) in (float, int) and math.isfinite(self.start)
             and self.last <= now < self.start + SECONDS)
        self.last = now

    def room(self, path, file=True):
        self.tick()
        parts = Path(path).absolute().parts
        need('..' not in parts)
        parents = parts[:-1] if file else parts
        missing = sum(parts[:i] not in self.capture.directory_cache
                      for i in range(1, len(parents) + 1))
        count = 0
        with os.scandir('/dev/fd' if sys.platform == 'darwin' else '/proc/self/fd') as entries:
            for _ in entries:
                count += 1
                need(count + missing + int(file) <= MAX_FDS)

    def read(self, path, size, digest=None, private=False):
        need(type(size) is int and 0 < size <= 4_000_000)
        need(self.reads < MAX_READS and self.bytes + size <= MAX_INPUT)
        self.room(path)
        self.reads += 1
        self.bytes += size
        with critical():
            raw = self.capture.read(path, size, private=private)
        need(len(raw) == size and (digest is None or sha(raw) == digest))
        self.tick()
        return raw

    def source(self, row):
        need(type(row) is dict and set(row) >= {'path', 'bytes', 'sha256'})
        name = row['path']
        need(type(name) is str and not name.startswith('/') and '..' not in Path(name).parts)
        return self.read(ROOT / name, row['bytes'], row['sha256'])


def _expected(budget):
    # The code-derived index pin is independent of a received carrying manifest.
    own = Path(__file__)
    method = budget.read(own, own.stat().st_size)
    data = parse(budget.read(ROOT / DATA, 4810, DATA_SHA256))
    need(set(data) == {'profile', 'source_manifest', 'apache_fulltext', 'packages', 'claims'}
         and data['profile'] == 'c2pa-three-project-grant-inputs/v1'
         and data['claims'] == CLAIMS and all(v is False for v in data['claims'].values()))
    original = parse(budget.source(data['source_manifest']))
    need(original['profile'] == 'c2pa-native-dependency-observations/v1'
         and type(original['packages']) is list and len(original['packages']) == 441)
    license_text = budget.source(data['apache_fulltext'])
    need(sha(b' '.join(license_text.split())) == data['apache_fulltext']['whitespace_token_sha256'])
    need(type(data['packages']) is list and tuple(r['id'] for r in data['packages']) == PACKAGES)
    files, carrying = {}, []
    for row in data['packages']:
        matches = [p for p in original['packages'] if p['id'] == row['id']]
        need(len(matches) == 1)
        package = matches[0]
        need(package['name'] == row['name'] and package['version'] == row['version']
             and package['archive_sha256'] == row['archive_sha256']
             and package['source_identity']['url'] == row['archive_url']
             and package['source_identity']['vcs_declaration']['git']['sha1'] == row['vcs_commit']
             and package['license_declared'] == row['declared_license'] == 'MIT/Apache-2.0'
             and package['notice_paths'] == row['upstream_notice_paths_observed'] == []
             and package['supplemental_source_notices'] == []
             and row['selected_license'] == 'Apache-2.0')
        members = {r['member']: r for r in package['retained_members']}
        for key, member in (('readme', 'README.md'), ('cargo_orig', 'Cargo.toml.orig')):
            need(row[key] == {k: members[member][k] for k in ('path', 'bytes', 'sha256')})
        readme = budget.source(row['readme']).decode('utf8', 'strict')
        cargo = tomllib.loads(budget.source(row['cargo_orig']).decode('utf8', 'strict'))['package']
        need(cargo['repository'] == row['repository'] and cargo['authors'] == row['authors']
             and cargo['license'] == 'MIT/Apache-2.0')
        grant = readme[readme.index('## License'):]
        need('Licensed under either of' in grant and 'Apache License, Version 2.0' in grant
             and 'at your option.' in grant and len(grant.encode()) == row['grant_section_bytes']
             and sha(grant.encode()) == row['grant_section_sha256'])
        name = row['id'].replace('@', '-') + '-APACHE-2.0.txt'
        header = ('AITrust-ID assembled project-grant carrying: ' + row['id'] + '\n\n'
                  'Not an upstream LICENSE or NOTICE filename. Apache-2.0 selected from the exact release README choice.\n'
                  'Publisher-declared authors (not a new copyright ownership/year assertion):\n'
                  + '\n'.join(row['authors']) + '\nRepository: ' + row['repository']
                  + '\nRelease archive: ' + row['archive_url'] + '\nArchive SHA256: ' + row['archive_sha256']
                  + '\nREADME SHA256: ' + row['readme']['sha256']
                  + '\n\nComplete unmodified release grant/contribution section:\n\n').encode()
        notice = header + grant.encode() + b'\n\nComplete unmodified Apache-2.0 text:\n\n' + license_text
        need(len(notice) <= MAX_MEMBER)
        files[name] = notice
        carrying.append({'package': row['id'], 'selected_license': 'Apache-2.0',
                         'path': name, 'bytes': len(notice), 'sha256': sha(notice),
                         'README': row['readme'], 'Cargo_orig': row['cargo_orig'],
                         'upstream_notice_paths_observed': [], 'assembled_carrying': True})
    manifest = {'profile': PROFILE, 'producer_source_sha256': sha(method),
                'input_index_sha256': DATA_SHA256, 'packages': carrying,
                'standard_license': data['apache_fulltext'], 'claims': CLAIMS}
    files['C2PA-PROJECT-GRANTS.json'] = encoded(manifest)
    need(len(files) == 4 and max(map(len, files.values())) <= MAX_MEMBER
         and sum(map(len, files.values())) <= MAX_ARTIFACT)
    budget.capture.check()
    budget.tick()
    return files


def _archive(files):
    target = io.BytesIO()
    with zipfile.ZipFile(target, 'w', compression=zipfile.ZIP_STORED) as stream:
        for name in sorted(files):
            info = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            info.compress_type = zipfile.ZIP_STORED
            stream.writestr(info, files[name])
    raw = target.getvalue()
    need(0 < len(raw) <= MAX_ARTIFACT)
    return raw


def _inspect(raw, files):
    # Canonical equality precedes all received ZIP interpretation/allocation.
    need(type(raw) is bytes and raw == _archive(files))
    with zipfile.ZipFile(io.BytesIO(raw)) as stream:
        need(stream.namelist() == sorted(files))
        for info in stream.infolist():
            need(info.file_size == info.compress_size == len(files[info.filename])
                 and info.compress_type == zipfile.ZIP_STORED
                 and stream.read(info) == files[info.filename])
    return {'profile': PROFILE, 'pass': True, 'packages': 3, 'members': 4,
            'bytes': len(raw), 'sha256': sha(raw), 'claims': dict(CLAIMS)}


def expected():
    try:
        with custody() as capture:
            budget = Budget(capture)
            files = _expected(budget)
            capture.check()
        budget.tick()
        return files
    except (Exception, KeyboardInterrupt, SystemExit):
        raise Unavailable() from None


def inspect(artifact):
    try:
        with custody() as capture:
            budget = Budget(capture)
            files = _expected(budget)
            canonical = _archive(files)
            raw = budget.read(artifact, len(canonical))
            result = _inspect(raw, files)
            capture.check()
        budget.tick()
        return result
    except (Exception, KeyboardInterrupt, SystemExit):
        raise Unavailable() from None


def prepare(output):
    possible_creation = False
    try:
        with custody() as capture:
            budget = Budget(capture)
            files = _expected(budget)
            raw = _archive(files)
            budget.room(output)
            with critical():
                parent, name = capture.parent(output)
            try:
                os.stat(name, dir_fd=parent, follow_symlinks=False)
            except FileNotFoundError:
                pass
            else:
                raise Unavailable()
            info = os.fstat(parent)
            need(info.st_uid == os.getuid() and stat.S_IMODE(info.st_mode) == 0o700)
            budget.room(output)
            possible_creation = True
            with critical():
                fd = os.open(name, os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600, dir_fd=parent)
                try:
                    capture.fds.append(fd)
                except BaseException:
                    os.close(fd)
                    raise
            at = 0
            while at < len(raw):
                budget.tick()
                count = os.write(fd, raw[at:at + 65536])
                need(count > 0)
                at += count
            os.fsync(fd)
            capture.files.append((parent, name, fd, snapshot(os.fstat(fd))))
            need(budget.read(output, len(raw), private=True) == raw)
            result = _inspect(raw, files)
            os.fsync(parent)
            capture.parent(output)
            capture.check()
        budget.tick()
        return result
    except BaseException:
        if possible_creation:
            raise OutputUncertain() from None
        raise Unavailable() from None
