"""Finite source-copy obligations v2; no archive, runtime or release approval.

SPDX-License-Identifier: Apache-2.0
"""
import argparse
import builtins
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
PROFILE = 'source-snapshot-copy-obligations/v2'
POLICY = 'eval/dependencies/source-snapshot-release-v2.json'
POLICY_SHA256 = '2c6bc3c14c8825f8fdd583e42adb1df39e7983ee6f2bac96004231a3dbd6543d'
LEGACY = 'eval/dependencies/source-snapshot-release.json'
LEGACY_SHA256 = '2e555a5dc31a9d92b0982a9dba1fefea9376a45bb0d4c99625332b59965c6645'
LEGACY_HELPER_SHA256 = '897d287a1dc91c441db54237b0b80dfe634521ecc6b644944d04a63623b591b6'
WORKER_SHA256 = '9411406936c9757a67306211a695cbe54c0e318ca1d7e6c9229d24103baeb7a3'
PROTECTED = '085106c1d40e86b071a25a7b9e4e56b965a31044'
SELECTED_PROTECTED = '6d752cd0ae127e7d1ebe93499ab6fd83f55dcafd'
BINDING_SHA256 = 'c219f326861c2634e930d7c0b74c0abad9859b3abe746a77464ece5ba8fceffb'
MAX_ARCHIVE = 64_000_000
MARKER_TRANSITIONS = {
    'docs/legal/execution-packet.md': (
        '9f14375e8c076fece26dc61be21b55233061469a91b9c678beb056b570d13a98',
        'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
        '43de8e5eef89a493a8439f383c8a9e92c3f1e22e'),
}
MAX_FILES, MAX_FILE, MAX_TOTAL = 16384, 32_000_000, 256_000_000
MAX_POLICY, MAX_LISTING, MAX_CHANGED_TEXT = 12_000_000, 2_000_000, 2_000_000
MAX_INSPECTED_TEXT, DEADLINE = 64_000_000, 30
OID = re.compile(r'[a-f0-9]{40}')
SHA = re.compile(r'[a-f0-9]{64}')
MARKERS = re.compile(r'^\s*(?:[#/*;]+\s*)?(?:SPDX-License-Identifier:.*|Copyright\b.*|Licensed under\b.*)$', re.I | re.M)
FALSE_CLAIMS = ('legal_clearance', 'compiled_runtime_permission', 'source_archive_admitted',
                'release_authorized', 'accuracy', 'complete_F057_X02')
CODES = frozenset({'invalid_request', 'policy_changed', 'foundation_changed', 'invalid_profile',
    'source_unavailable', 'source_changed', 'resource_limit', 'git_unavailable', 'unknown_path',
    'missing_path', 'grant_changed', 'third_party_or_asset_changed', 'license_declaration_changed',
    'unsupported_source_commit', 'unsupported_git_entry', 'unsupported_first_party_text',
    'archive_refused', 'deadline', 'unavailable'})

# No inherited Git configuration, replacement database, credential helper or lazy
# network access. Preserve the existing HOME value without reading any home file.
GIT_EXEC = r'''
import os,sys
clean={'PATH':'/usr/bin:/bin','LC_ALL':'C','GIT_CONFIG_NOSYSTEM':'1',
       'GIT_CONFIG_SYSTEM':'/dev/null','GIT_CONFIG_GLOBAL':'/dev/null',
       'GIT_NO_LAZY_FETCH':'1','GIT_TERMINAL_PROMPT':'0','GIT_OPTIONAL_LOCKS':'0'}
if 'HOME' in os.environ: clean['HOME']=os.environ['HOME']
os.execve('/usr/bin/git',['git','--no-replace-objects','-c','protocol.allow=never',
                        '-c','core.useReplaceRefs=false',*sys.argv[1:]],clean)
'''


class Refused(ValueError):
    def __init__(self, code):
        self.code = code if code in CODES else 'unavailable'
        super().__init__('Source-copy v2 unavailable.')


def need(value, code='invalid_profile'):
    if not value:
        raise Refused(code)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def path_name(name):
    need(type(name) is str and 0 < len(name.encode()) <= 1000)
    need(not name.startswith('/') and '\\' not in name and
         all(x not in ('', '.', '..', '.git') for x in name.split('/')) and
         not any(ord(x) < 32 for x in name))
    return name


def file_bytes(path, limit):
    path = Path(path)
    need(not path.is_symlink() and not any(p.is_symlink() for p in path.parents), 'source_unavailable')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(fd)
        need(stat.S_ISREG(before.st_mode) and before.st_nlink == 1 and
             0 <= before.st_size <= limit, 'resource_limit')
        output = bytearray()
        while True:
            block = os.read(fd, min(65536, limit + 1 - len(output)))
            if not block:
                break
            need(len(output) + len(block) <= limit, 'resource_limit')
            output.extend(block)
        after = os.fstat(fd)
        key = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
        named = path.lstat()
        need(key(before) == key(after) and len(output) == before.st_size and
             (after.st_dev, after.st_ino) == (named.st_dev, named.st_ino), 'source_changed')
        return bytes(output)
    finally:
        os.close(fd)


def parse(raw):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            need(key not in result)
            result[key] = value
        return result
    def bad(_):
        raise Refused('invalid_profile')
    return json.loads(raw.decode('utf-8', 'strict'), object_pairs_hook=unique,
                      parse_constant=bad, parse_float=bad)


def policy(raw, legacy_raw):
    need(sha(raw) == POLICY_SHA256 and sha(legacy_raw) == LEGACY_SHA256, 'policy_changed')
    d, legacy = parse(raw), parse(legacy_raw)
    keys = {'profile', 'protected_baseline_commit', 'protected_baseline_tree', 'selected_commit',
            'selected_tree', 'selected_is_protected_release', 'legacy_policy_sha256',
            'legacy_helper_sha256', 'selected_files', 'selected_raw_bytes', 'delta', 'origins',
            'named_first_party_extensions', 'claims'}
    need(type(d) is dict and set(d) == keys and d['profile'] == PROFILE)
    need(d['protected_baseline_commit'] == PROTECTED and
         d['legacy_policy_sha256'] == LEGACY_SHA256 and
         d['legacy_helper_sha256'] == LEGACY_HELPER_SHA256 and
         d['selected_is_protected_release'] is True and
         d['selected_commit'] == SELECTED_PROTECTED)
    need(all(type(d[k]) is str and OID.fullmatch(d[k]) for k in
             ('protected_baseline_tree', 'selected_commit', 'selected_tree')))
    need(type(d['selected_files']) is int and 0 < d['selected_files'] <= MAX_FILES and
         type(d['selected_raw_bytes']) is int and 0 <= d['selected_raw_bytes'] <= MAX_TOTAL)
    need(type(d['claims']) is dict and set(d['claims']) == set(FALSE_CLAIMS) and
         all(d['claims'][k] is False for k in FALSE_CLAIMS))
    need(type(d['delta']) is list and 0 < len(d['delta']) <= 2048 and
         type(d['origins']) is dict and 0 < len(d['origins']) <= 1024)
    baseline = {r[0]: r for r in legacy['files']}
    expected = {n: (r[1], r[2], r[3], r[4], r[5]) for n, r in baseline.items()}
    delta_names = set()
    categories = set(legacy['categories']) | {'cffi-retained-source', 'rust-retained-source',
                 'mcp-retained-notices', 'mcp-obligation-index'}
    for row in d['delta']:
        need(type(row) is list and len(row) == 7)
        name, mode, oid, size, category, origin, marker = row
        path_name(name)
        need(name not in delta_names and mode in ('100644', '100755') and
             type(oid) is str and OID.fullmatch(oid) and type(size) is int and
             0 <= size <= MAX_FILE and category in categories and origin in d['origins'])
        need(type(marker) is str and bool(SHA.fullmatch(marker))
             if category == 'project-text' else marker is None)
        if name in baseline:
            need(category == baseline[name][4])
            if category == 'project-text':
                need(marker == baseline[name][5] or
                     MARKER_TRANSITIONS.get(name) == (baseline[name][5], marker, oid))
        delta_names.add(name)
        expected[name] = (mode, oid, size, category, marker)
    need(len(expected) == d['selected_files'] and sum(r[2] for r in expected.values()) == d['selected_raw_bytes'])
    for identity, origin in d['origins'].items():
        need(type(identity) is str and 0 < len(identity) <= 1000 and type(origin) is dict and
             set(origin) == {'license', 'evidence_paths', 'upstream_or_authorship', 'copy_scope'})
        need(all(type(origin[k]) is str and 0 < len(origin[k]) <= 4000 for k in
                 ('license', 'upstream_or_authorship', 'copy_scope')))
        need(type(origin['evidence_paths']) is list and 0 < len(origin['evidence_paths']) <= 1024 and
             len(set(origin['evidence_paths'])) == len(origin['evidence_paths']) and
             all(p in expected for p in origin['evidence_paths']))
    extensions = d['named_first_party_extensions']
    need(type(extensions) is list and 0 < len(extensions) <= 32 and len(set(extensions)) == len(extensions))
    for name in extensions:
        path_name(name)
        need(name not in expected)
    for name, oid in legacy['grant_anchors'].items():
        need(expected[name][1] == oid, 'grant_changed')
    return d, legacy, expected


def tree_rows(raw):
    need(type(raw) is bytes and 0 < len(raw) <= MAX_LISTING, 'resource_limit')
    parts = raw.split(b'\0')
    need(parts[-1:] == [b''] and 0 < len(parts) - 1 <= MAX_FILES, 'resource_limit')
    rows, total = {}, 0
    for part in parts[:-1]:
        meta, name = part.split(b'\t', 1)
        mode, kind, oid, size = meta.decode('ascii').split()
        name = path_name(name.decode('utf-8', 'strict'))
        need(mode in ('100644', '100755') and kind == 'blob' and OID.fullmatch(oid) and
             re.fullmatch('0|[1-9][0-9]*', size), 'unsupported_git_entry')
        size = int(size)
        total += size
        need(name not in rows and size <= MAX_FILE and total <= MAX_TOTAL, 'resource_limit')
        rows[name] = (mode, oid, size)
    return rows, total


def markers(raw):
    need(type(raw) is bytes and b'\0' not in raw, 'unsupported_first_party_text')
    text = raw.decode('utf-8', 'strict')
    lines = MARKERS.findall(text)
    return sha('\n'.join(x.strip() for x in lines).encode()), lines


def checked(d, legacy, expected, observed, read_blob, tick):
    need(observed.keys() <= expected.keys() | set(d['named_first_party_extensions']), 'unknown_path')
    need(expected.keys() <= observed.keys(), 'missing_path')
    for name, oid in legacy['grant_anchors'].items():
        need(observed[name][1] == oid, 'grant_changed')
    changed = introduced = inspected = 0
    for name, current in observed.items():
        tick()
        need(type(current) in (tuple, list) and len(current) == 3 and
             current[0] in ('100644', '100755') and type(current[1]) is str and
             bool(OID.fullmatch(current[1])) and type(current[2]) is int and
             0 <= current[2] <= MAX_FILE, 'unsupported_git_entry')
        row = expected.get(name)
        if row and current == row[:3]:
            continue
        need(row is None or row[3] == 'project-text', 'third_party_or_asset_changed')
        need(current[2] <= MAX_CHANGED_TEXT, 'resource_limit')
        inspected += current[2]
        need(inspected <= MAX_INSPECTED_TEXT, 'resource_limit')
        raw = read_blob(current[1], current[2])
        need(len(raw) == current[2] and
             hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest() == current[1],
             'source_changed')
        marker, lines = markers(raw)
        if row:
            need(marker == row[4], 'license_declaration_changed')
            changed += 1
        else:
            allowed = {'SPDX-License-Identifier: Apache-2.0',
                       'Licensed under the Apache License, Version 2.0.',
                       'Copyright 2026 Michael Raashad McGuire and AITrust-ID contributors.'}
            need(all(x.strip().lstrip('#/*; ').rstrip('*/ ').strip() in allowed for x in lines),
                 'license_declaration_changed')
            introduced += 1
    return {'files': len(observed), 'changed_named_project_text_files': changed,
            'introduced_named_project_text_files': introduced}


def worker():
    raw = file_bytes(ROOT / 'scripts/worker_process.py', 100000)
    need(sha(raw) == WORKER_SHA256, 'foundation_changed')
    original = builtins.__import__
    def standard(name, globals=None, locals=None, fromlist=(), level=0):
        need(level == 0 and name in {'math', 'os', 'selectors', 'signal', 'subprocess', 'time'},
             'foundation_changed')
        return original(name, globals, locals, fromlist, level)
    namespace = {'__name__': '_trusted_source_copy_v2_worker',
                 '__builtins__': {**vars(builtins), '__import__': standard}}
    exec(compile(raw, '<captured-source-copy-supervisor>', 'exec'), namespace)
    return namespace['run_worker']


def verify(root=ROOT, source_commit=None):
    result = {'profile': PROFILE, 'pass': False, 'status': 'UNAVAILABLE',
              'source_copy_profile_satisfied': False, **{k: False for k in FALSE_CLAIMS}}
    try:
        need(Path(root).resolve() == ROOT, 'source_unavailable')
        deadline = time.monotonic() + DEADLINE
        def tick():
            need(time.monotonic() < deadline, 'deadline')
        run = worker()
        raw = file_bytes(ROOT / POLICY, MAX_POLICY)
        legacy_raw = file_bytes(ROOT / LEGACY, MAX_POLICY)
        need(sha(file_bytes(ROOT / 'tools/source_release_policy.py', 100000)) == LEGACY_HELPER_SHA256,
             'foundation_changed')
        method = sha(file_bytes(Path(__file__), 100000))
        d, legacy, expected = policy(raw, legacy_raw)
        def git(args, limit=MAX_LISTING):
            tick()
            value = run([sys.executable, '-I', '-S', '-B', '-c', GIT_EXEC, '-C', str(ROOT), *args],
                        input=b'', timeout=min(20, deadline - time.monotonic()), output_limit=limit)
            need(value.returncode == 0, 'git_unavailable')
            tick()
            return value.stdout
        head = git(['rev-parse', '--verify', 'HEAD^{commit}'], 100).decode('ascii').strip()
        need(bool(OID.fullmatch(head)), 'git_unavailable')
        commit = head if source_commit is None else source_commit
        need(type(commit) is str and bool(OID.fullmatch(commit)), 'unsupported_source_commit')
        need(git(['cat-file', '-t', commit], 100) == b'commit\n', 'unsupported_source_commit')
        git(['merge-base', '--is-ancestor', d['selected_commit'], commit], 100)
        need(git(['rev-parse', d['selected_commit'] + '^{tree}'], 100).decode().strip() ==
             d['selected_tree'] and
             git(['rev-parse', PROTECTED + '^{tree}'], 100).decode().strip() ==
             d['protected_baseline_tree'], 'source_changed')
        observed, total = tree_rows(git(['ls-tree', '-r', '-l', '-z', '--full-tree', commit]))
        facts = checked(d, legacy, expected, observed,
                        lambda oid, size: git(['cat-file', 'blob', oid], min(size + 1, MAX_CHANGED_TEXT)), tick)
        need(git(['rev-parse', '--verify', 'HEAD^{commit}'], 100).decode().strip() == head,
             'source_changed')
        need(file_bytes(ROOT / POLICY, MAX_POLICY) == raw and
             file_bytes(ROOT / LEGACY, MAX_POLICY) == legacy_raw and
             sha(file_bytes(ROOT / 'tools/source_release_policy.py', 100000)) == LEGACY_HELPER_SHA256 and
             sha(file_bytes(ROOT / 'scripts/worker_process.py', 100000)) == WORKER_SHA256 and
             sha(file_bytes(Path(__file__), 100000)) == method, 'source_changed')
        tick()
        result.update({'pass': True, 'status': 'SOURCE_COPY_PROFILE_SATISFIED',
                       'source_copy_profile_satisfied': True, 'source_commit': commit,
                       'checkout_commit': head, 'source_bytes': total, **facts,
                       'policy_sha256': POLICY_SHA256, 'method_sha256': method,
                       'legacy_policy_sha256': LEGACY_SHA256,
                       'protected_baseline_commit': PROTECTED,
                       'selected_profile_base_is_protected_release': d['selected_is_protected_release']})
    except (OSError, ValueError, TypeError, KeyError, OverflowError, RecursionError, RuntimeError,
            subprocess.SubprocessError) as failure:
        result['reason'] = failure.code if isinstance(failure, Refused) else 'unavailable'
    return result


def verify_archive(raw, *, source_commit):
    """Copy obligations plus exact trusted Git bytes; never authenticity/admission.

    Classification precedes archive interpretation. The binding worker executes
    captured hash-pinned code, not a reopened script or archive-selected module.
    """
    result = {'profile': 'source-copy-archive-obligations/v2', 'pass': False,
              'status': 'UNAVAILABLE', 'source_copy_profile_satisfied': False,
              'trusted_git_bytes_matched': False, 'signature_verified': False,
              **{k: False for k in FALSE_CLAIMS}}
    try:
        need(type(raw) is bytes and 0 < len(raw) <= MAX_ARCHIVE and
             type(source_commit) is str and bool(OID.fullmatch(source_commit)), 'invalid_request')
        deadline = time.monotonic() + 95
        copy = verify(source_commit=source_commit)
        need(copy.get('pass') is True and copy.get('source_copy_profile_satisfied') is True,
             copy.get('reason', 'unavailable'))
        source = file_bytes(ROOT / 'tools/source_snapshot_binding.py', 100000)
        need(sha(source) == BINDING_SHA256, 'foundation_changed')
        method = sha(file_bytes(Path(__file__), 100000))
        # sys.argv comes from fixed literal --binding-worker and caller-selected
        # root/commit. The original module's private entrypoint reads stdin only.
        program = 'exec(compile(' + repr(source) + ", '<captured-source-binding>', 'exec'), " + repr({
            '__name__': '__main__', '__file__': str(ROOT / 'tools/source_snapshot_binding.py')}) + ')'
        remaining = min(60, deadline - time.monotonic())
        need(remaining > 0, 'deadline')
        completed = worker()([sys.executable, '-I', '-S', '-B', '-c', program,
                              '--binding-worker', str(ROOT), source_commit],
                             input=raw, timeout=remaining, output_limit=4096)
        need(completed.returncode == 0, 'archive_refused')
        body = parse(completed.stdout)
        keys = {'profile', 'pass', 'source_commit', 'source_tree', 'source_files', 'source_bytes',
                'archive_sha256', 'trusted_git_bytes_matched', 'signature_verified',
                'rights_approved', 'release_authorized'}
        need(type(body) is dict and set(body) == keys and
             body['profile'] == 'source-snapshot-trusted-git-binding/v1' and body['pass'] is True and
             body['source_commit'] == source_commit and type(body['source_tree']) is str and
             bool(OID.fullmatch(body['source_tree'])) and type(body['source_files']) is int and
             body['source_files'] == copy['files'] and type(body['source_bytes']) is int and
             body['source_bytes'] == copy['source_bytes'] and body['archive_sha256'] == sha(raw) and
             body['trusted_git_bytes_matched'] is True and all(body[k] is False for k in
             ('signature_verified', 'rights_approved', 'release_authorized')), 'archive_refused')
        need(file_bytes(ROOT / 'tools/source_snapshot_binding.py', 100000) == source and
             sha(file_bytes(ROOT / POLICY, MAX_POLICY)) == POLICY_SHA256 and
             sha(file_bytes(ROOT / LEGACY, MAX_POLICY)) == LEGACY_SHA256 and
             sha(file_bytes(ROOT / 'tools/source_release_policy.py', 100000)) == LEGACY_HELPER_SHA256 and
             sha(file_bytes(ROOT / 'scripts/worker_process.py', 100000)) == WORKER_SHA256 and
             sha(file_bytes(Path(__file__), 100000)) == method, 'source_changed')
        need(time.monotonic() < deadline, 'deadline')
        result.update({'pass': True, 'status': 'COPY_OBLIGATIONS_AND_GIT_BYTES_BOUND',
                       'source_copy_profile_satisfied': True, 'trusted_git_bytes_matched': True,
                       'source_commit': source_commit, 'source_tree': body['source_tree'],
                       'source_files': body['source_files'], 'source_bytes': body['source_bytes'],
                       'archive_sha256': body['archive_sha256'], 'archive_bytes': len(raw),
                       'policy_sha256': POLICY_SHA256, 'method_sha256': method,
                       'binding_method_sha256': BINDING_SHA256})
    except (OSError, ValueError, TypeError, KeyError, OverflowError, RecursionError, RuntimeError,
            subprocess.SubprocessError) as failure:
        result['reason'] = failure.code if isinstance(failure, Refused) else 'unavailable'
    return result


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise Refused('invalid_request')


def main(argv=None):
    try:
        parser = Parser(description=__doc__)
        parser.add_argument('--source-commit')
        parser.add_argument('--archive', type=Path)
        args = parser.parse_args(argv)
        if args.archive is None:
            result = verify(source_commit=args.source_commit)
        else:
            need(args.source_commit is not None, 'invalid_request')
            result = verify_archive(file_bytes(args.archive, MAX_ARCHIVE), source_commit=args.source_commit)
    except Refused as error:
        result = {'profile': PROFILE, 'pass': False, 'status': 'UNAVAILABLE',
                  'reason': error.code, **{k: False for k in FALSE_CLAIMS}}
    print(json.dumps(result, sort_keys=True))
    return 0 if result['pass'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
