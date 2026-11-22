"""Closed source-copy obligation profile; not legal clearance or a release signer.

SPDX-License-Identifier: Apache-2.0
"""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
POLICY = 'eval/dependencies/source-snapshot-release.json'
PROFILE = 'source-snapshot-copy-obligations/v1'
POLICY_SHA256 = '2e555a5dc31a9d92b0982a9dba1fefea9376a45bb0d4c99625332b59965c6645'
WORKER_SHA256 = '9411406936c9757a67306211a695cbe54c0e318ca1d7e6c9229d24103baeb7a3'
MAX_POLICY = 12_000_000
MAX_LISTING = 2_000_000
MAX_FILES = 16_384
MAX_FILE = 32_000_000
MAX_TOTAL = 256_000_000
MAX_CHANGED_TEXT = MAX_FILE
MAX_INSPECTED_TEXT = 64_000_000
DEADLINE_SECONDS = 30
OID = re.compile(r'[a-f0-9]{40}')
SHA = re.compile(r'[a-f0-9]{64}')
MARKERS = re.compile(r'^\s*(?:[#/*;]+\s*)?(?:SPDX-License-Identifier:.*|Copyright\b.*|Licensed under\b.*)$', re.I | re.M)

# Literal owned program: copied source is hashed/decoded, never evaluated.
# Its Git child stays in the supervisor's process group, without a new session.
BLOB_WORKER = r'''
import hashlib,json,os,re,subprocess,sys
child=None
result={'pass':False,'reason':'unavailable'}
try:
    root,oid,size=sys.argv[1:]
    assert re.fullmatch('[a-f0-9]{40}',oid)
    assert re.fullmatch('0|[1-9][0-9]*',size)
    size=int(size);assert 0<=size<=32000000
    child=subprocess.Popen(['/usr/bin/git','--no-replace-objects','-c','protocol.allow=never',
                            '-C',root,'cat-file','blob',oid],stdin=subprocess.DEVNULL,
                           stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,
                           close_fds=True,start_new_session=False)
    raw=bytearray()
    while True:
        block=child.stdout.read(min(65536,size+1-len(raw)))
        if not block:break
        assert len(raw)+len(block)<=size
        raw.extend(block)
    assert child.wait(timeout=5)==0 and len(raw)==size
    actual=hashlib.sha1(b'blob '+str(size).encode()+b'\0'+raw).hexdigest()
    assert actual==oid and b'\0'not in raw
    text=raw.decode('utf-8','strict')
    lines=re.findall(r'^\s*(?:[#/*;]+\s*)?(?:SPDX-License-Identifier:.*|Copyright\b.*|Licensed under\b.*)$',text,re.I|re.M)
    marker=hashlib.sha256('\n'.join(line.strip()for line in lines).encode()).hexdigest()
    allowed=('SPDX-License-Identifier: Apache-2.0',
             'Licensed under the Apache License, Version 2.0.',
             'Copyright 2026 Michael Raashad McGuire and AITrust-ID contributors.')
    introduced=all(line.strip().lstrip('#/*; ').rstrip('*/ ').strip()in allowed for line in lines)
    result={'pass':True,'oid':actual,'bytes':size,'markers':marker,'introduced_markers_allowed':introduced}
except (OSError,ValueError,AssertionError,subprocess.SubprocessError):
    pass
finally:
    try:
        if child is not None and child.returncode is None:
            try:child.kill()
            except ProcessLookupError:pass
            child.wait(timeout=5)
    finally:
        if child is not None and child.stdout is not None:child.stdout.close()
print(json.dumps(result,separators=(',',':')))
'''


class Refused(ValueError):
    def __init__(self, code):
        self.code = code
        super().__init__('Source-copy profile unavailable.')


def need(value, code='invalid_profile'):
    if not value:
        raise Refused(code)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def markers(raw):
    need(type(raw) is bytes and b'\0' not in raw, 'unsupported_first_party_text')
    try:
        text = raw.decode('utf-8', 'strict')
    except UnicodeError:
        raise Refused('unsupported_first_party_text') from None
    return sha('\n'.join(line.strip() for line in MARKERS.findall(text)).encode())


def path_name(name):
    need(type(name) is str and 0 < len(name.encode('utf-8')) <= 1000)
    p = Path(name)
    need(not p.is_absolute() and all(x not in ('', '.', '..', '.git') for x in name.split('/'))
         and not any(ord(x) < 32 for x in name) and '\\' not in name)
    return name


def file_bytes(path, limit):
    """Single raw-descriptor owner, no fdopen, no retry after a close error."""
    path = Path(path)
    need(not path.is_symlink() and not any(p.is_symlink() for p in path.parents), 'source_unavailable')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(fd)
        need(stat.S_ISREG(before.st_mode) and before.st_nlink == 1 and 0 <= before.st_size <= limit,
             'resource_limit')
        output = bytearray()
        while True:
            chunk = os.read(fd, min(65_536, limit + 1 - len(output)))
            if not chunk:
                break
            need(len(output) + len(chunk) <= limit, 'resource_limit')
            output.extend(chunk)
        after = os.fstat(fd)
        fingerprint = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
        need(fingerprint(before) == fingerprint(after) and len(output) == before.st_size,
             'source_changed')
        named = path.lstat()
        need((after.st_dev, after.st_ino) == (named.st_dev, named.st_ino), 'source_changed')
        return bytes(output)
    finally:
        os.close(fd)


def policy(raw):
    need(sha(raw) == POLICY_SHA256, 'policy_changed')
    def unique(pairs):
        result = {}
        for k, v in pairs:
            need(k not in result)
            result[k] = v
        return result
    def bad(_):
        raise Refused('invalid_profile')
    d = json.loads(raw.decode('utf-8', 'strict'), object_pairs_hook=unique,
                   parse_constant=bad, parse_float=bad)
    need(type(d) is dict and set(d) == {'profile', 'base_commit', 'base_tree', 'files',
         'categories', 'introduced_first_party', 'grant_anchors', 'scope', 'claims'})
    need(d['profile'] == PROFILE and OID.fullmatch(d['base_commit']) and OID.fullmatch(d['base_tree']))
    need(type(d['files']) is list and 0 < len(d['files']) <= MAX_FILES)
    need(type(d['categories']) is dict and 0 < len(d['categories']) <= 64)
    need(type(d['introduced_first_party']) is dict and len(d['introduced_first_party']) <= 32)
    need(type(d['grant_anchors']) is dict and 0 < len(d['grant_anchors']) <= 256)
    expected = set()
    for row in d['files']:
        need(type(row) is list and len(row) == 6)
        name, mode, oid, size, category, marker = row
        path_name(name)
        need(name not in expected and mode in ('100644', '100755') and OID.fullmatch(oid)
             and type(size) is int and 0 <= size <= MAX_FILE and category in d['categories'])
        expected.add(name)
        need(marker is None or type(marker) is str and SHA.fullmatch(marker))
        need((marker is not None) == d['categories'][category]['mutable_project_text'])
    for category, row in d['categories'].items():
        need(type(category) is str and type(row) is dict and
             set(row) in ({'license', 'evidence_paths', 'copy_scope', 'obligations', 'mutable_project_text'},
                          {'license', 'evidence_paths', 'copy_scope', 'obligations', 'mutable_project_text', 'reviewed_components'}))
        need(type(row['mutable_project_text']) is bool and
             (not row['mutable_project_text'] or category == 'project-text' and row['license'] == 'Apache-2.0'))
        need(type(row['license']) is str and 0 < len(row['license']) <= 4096 and
             type(row['copy_scope']) is str and 0 < len(row['copy_scope']) <= 2000)
        need(type(row['evidence_paths']) is list and 0 < len(row['evidence_paths']) <= MAX_FILES and
             len(set(row['evidence_paths'])) == len(row['evidence_paths']) and
             all(n in expected for n in row['evidence_paths']))
        need(type(row['obligations']) is list and 0 < len(row['obligations']) <= 16 and
             all(type(n) is str and 0 < len(n) <= 2000 for n in row['obligations']))
    for name, category in d['introduced_first_party'].items():
        path_name(name)
        need(name not in expected and category in d['categories']
             and d['categories'][category]['mutable_project_text'])
    for name, oid in d['grant_anchors'].items():
        path_name(name)
        need(name in expected and type(oid) is str and OID.fullmatch(oid))
    need(d['claims'] == {'legal_clearance': False, 'complete_project_obligations': False,
                         'compiled_runtime_permission': False, 'accuracy': False})
    need(all(type(v) is bool for v in d['claims'].values()))
    return d


def tree_rows(raw):
    need(type(raw) is bytes and 0 < len(raw) <= MAX_LISTING, 'resource_limit')
    parts = raw.split(b'\0')
    need(parts[-1:] == [b''] and 0 < len(parts) - 1 <= MAX_FILES, 'resource_limit')
    result = {}
    total = 0
    for part in parts[:-1]:
        meta, name = part.split(b'\t', 1)
        mode, kind, oid, size = meta.decode('ascii').split()
        name = path_name(name.decode('utf-8', 'strict'))
        need(mode in ('100644', '100755') and kind == 'blob' and OID.fullmatch(oid)
             and re.fullmatch(r'0|[1-9][0-9]*', size), 'unsupported_git_entry')
        size = int(size)
        need(name not in result and size <= MAX_FILE, 'resource_limit')
        total += size
        need(total <= MAX_TOTAL, 'resource_limit')
        result[name] = (mode, oid, size)
    return result, total


def blob_summary(run_worker, oid, size, timeout):
    need(type(oid) is str and OID.fullmatch(oid) and type(size) is int and 0 <= size <= MAX_FILE)
    argv = ['/usr/bin/env', '-i', 'PATH=/usr/bin:/bin:/usr/sbin:/sbin', 'LANG=C', 'LC_ALL=C',
            'GIT_NO_LAZY_FETCH=1', 'GIT_TERMINAL_PROMPT=0', sys.executable, '-I', '-S', '-B',
            '-c', BLOB_WORKER, str(ROOT), oid, str(size)]
    value = run_worker(argv, input=b'', timeout=timeout, output_limit=1024)
    need(value.returncode == 0, 'blob_unavailable')
    info = json.loads(value.stdout)
    need(type(info) is dict and set(info) == {'pass', 'oid', 'bytes', 'markers',
                                             'introduced_markers_allowed'} and
         info['pass'] is True and info['oid'] == oid and type(info['bytes']) is int and
         info['bytes'] == size and type(info['markers']) is str and SHA.fullmatch(info['markers']) and
         type(info['introduced_markers_allowed']) is bool, 'unsupported_first_party_text')
    return info


def checked(d, observed, read_blob, tick):
    baseline = {row[0]: row for row in d['files']}
    permitted = baseline.keys() | d['introduced_first_party'].keys()
    need(observed.keys() <= permitted, 'unknown_path')
    need(baseline.keys() <= observed.keys(), 'missing_path')
    for name, oid in d['grant_anchors'].items():
        need(observed[name][1] == oid, 'grant_changed')
    changed = 0
    introduced = 0
    inspected = 0
    counts = {}
    for name, current in observed.items():
        tick()
        row = baseline.get(name)
        category = row[4] if row else d['introduced_first_party'][name]
        c = d['categories'][category]
        counts[category] = counts.get(category, 0) + 1
        if row and current == tuple(row[1:4]):
            continue
        need(c['mutable_project_text'], 'third_party_or_asset_changed')
        need(current[2] <= MAX_CHANGED_TEXT or name == POLICY, 'resource_limit')
        inspected += current[2]
        need(inspected <= MAX_INSPECTED_TEXT, 'resource_limit')
        value = read_blob(name, current[1], current[2])
        if type(value) is bytes:  # Pure validator controls; production uses the owned summary worker.
            raw = value
            need(len(raw) == current[2], 'source_changed')
            actual = hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
            marker = markers(raw)
            declarations = [line.strip().lstrip('#/*; ').rstrip('*/ ').strip()
                            for line in MARKERS.findall(raw.decode('utf-8'))]
            allowed = all(line in ('SPDX-License-Identifier: Apache-2.0',
                                  'Licensed under the Apache License, Version 2.0.',
                                  'Copyright 2026 Michael Raashad McGuire and AITrust-ID contributors.')
                          for line in declarations)
        else:
            need(type(value) is dict and set(value) == {'pass', 'oid', 'bytes', 'markers',
                                                        'introduced_markers_allowed'}, 'invalid_worker')
            need(value['pass'] is True and type(value['bytes']) is int and value['bytes'] == current[2]
                 and type(value['markers']) is str and SHA.fullmatch(value['markers'])
                 and type(value['introduced_markers_allowed']) is bool, 'invalid_worker')
            actual, marker, allowed = value['oid'], value['markers'], value['introduced_markers_allowed']
        need(actual == current[1], 'source_changed')
        if row:
            need(marker == row[5], 'license_declaration_changed')
            changed += 1
        else:
            need(allowed, 'license_declaration_changed')
            introduced += 1
    return {'files': len(observed), 'changed_project_text_files': changed,
            'introduced_named_project_text_files': introduced, 'category_counts': counts}


def verify(root=ROOT, source_commit=None):
    report = {'profile': PROFILE, 'pass': False, 'source_copy_profile_satisfied': False,
              'status': 'UNAVAILABLE', 'legal_clearance': False, 'release_authorized': False,
              'complete_project_obligations': False, 'compiled_runtime_permission': False,
              'independent_accuracy_evidence': False}
    try:
        need(Path(root).resolve() == ROOT, 'untrusted_checkout')
        deadline = time.monotonic() + DEADLINE_SECONDS
        def tick():
            need(time.monotonic() < deadline, 'deadline')
        worker_path = ROOT / 'scripts/worker_process.py'
        need(sha(file_bytes(worker_path, 100_000)) == WORKER_SHA256, 'worker_changed')
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        run_worker = importlib.import_module('scripts.worker_process').run_worker
        raw = file_bytes(ROOT / POLICY, MAX_POLICY)
        d = policy(raw)
        method_path = Path(__file__)
        method = sha(file_bytes(method_path, 100_000))
        def git(args, limit=MAX_LISTING):
            tick()
            argv = ['/usr/bin/env', '-i', 'PATH=/usr/bin:/bin:/usr/sbin:/sbin', 'LANG=C',
                    'LC_ALL=C', 'GIT_NO_LAZY_FETCH=1', 'GIT_TERMINAL_PROMPT=0', '/usr/bin/git',
                    '--no-replace-objects', '-c', 'protocol.allow=never', '-C', str(ROOT), *args]
            value = run_worker(argv, input=b'', timeout=min(20, deadline-time.monotonic()), output_limit=limit)
            need(value.returncode == 0, 'git_unavailable')
            tick()
            return value.stdout
        head = git(['rev-parse', '--verify', 'HEAD^{commit}'], 100).decode('ascii').strip()
        need(OID.fullmatch(head))
        commit = head if source_commit is None else source_commit
        need(type(commit) is str and OID.fullmatch(commit), 'unsupported_source_commit')
        need(git(['cat-file', '-t', commit], 100) == b'commit\n', 'unsupported_source_commit')
        observed, total = tree_rows(git(['ls-tree', '-r', '-l', '-z', '--full-tree', commit]))
        def blob(name, oid, size):
            # The policy's own bytes are already trusted and may exceed the
            # changed-text child-output cap; bind them to the selected Git blob.
            if name == POLICY:
                need(hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest() == oid,
                     'policy_changed')
                return raw
            tick()
            info = blob_summary(run_worker, oid, size, min(20, deadline-time.monotonic()))
            tick()
            return info
        facts = checked(d, observed, blob, tick)
        need(git(['rev-parse', '--verify', 'HEAD^{commit}'], 100).decode('ascii').strip() == head,
             'source_changed')
        need(file_bytes(ROOT / POLICY, MAX_POLICY) == raw and
             sha(file_bytes(method_path, 100_000)) == method and
             sha(file_bytes(worker_path, 100_000)) == WORKER_SHA256, 'source_changed')
        tick()
        report.update({'pass': True}, source_copy_profile_satisfied=True, status='SOURCE_COPY_PROFILE_SATISFIED',
                      source_commit=commit, checkout_commit=head, source_bytes=total, **facts,
                      policy_sha256=POLICY_SHA256, method_sha256=method,
                      worker_sha256=WORKER_SHA256)
    except (OSError, ValueError, TypeError, KeyError, OverflowError, RecursionError,
            RuntimeError, subprocess.SubprocessError) as failure:
        report['reason'] = failure.code if isinstance(failure, Refused) else 'unavailable'
    return report


class Parser(argparse.ArgumentParser):
    def error(self, message):
        self.exit(2, 'Source-copy profile request refused.\n')


def main():
    p = Parser(description=__doc__)
    p.add_argument('--source-commit')
    args = p.parse_args()
    value = verify(source_commit=args.source_commit)
    print(json.dumps(value, sort_keys=True))
    return 0 if value['pass'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
