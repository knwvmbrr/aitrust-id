"""Finite conditional source-copy additions over immutable V2; no release approval.

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
import types

ROOT = Path(__file__).resolve().parents[1]
PROFILE = 'source-copy-additions/v3'
POLICY = 'eval/dependencies/source-snapshot-additions-v3.json'
POLICY_SHA256 = '3bd727fef18736bcd259fa4f1e21fd25fa8629f361b25289dc0016f48394db3e'
V2_METHOD_SHA256 = '6642ab4ec688754ed5234027bdf029fd2a100b77d262fc98b958e1aed7c7126c'
V2_POLICY_SHA256 = '2c6bc3c14c8825f8fdd583e42adb1df39e7983ee6f2bac96004231a3dbd6543d'
BASE = '6d752cd0ae127e7d1ebe93499ab6fd83f55dcafd'
MAX_FILES, MAX_TOTAL, MAX_ARCHIVE = 16384, 256_000_000, 64_000_000
MAX_POLICY, MAX_COPIED, MAX_PROJECT, MAX_ORIGINS = 12_000_000, 256, 160, 256
OID = re.compile(r'[a-f0-9]{40}')
SHA = re.compile(r'[a-f0-9]{64}')
FALSE_CLAIMS = ('legal_clearance', 'compiled_runtime_permission', 'source_archive_admitted',
                'release_authorized', 'accuracy', 'complete_F057_X02')
METADATA_LEAVES = {
    'sbom/reviews/zlib-runtime/manifest.json': ('producer_sha256', 'tools/dependency_policy.py'),
    'site/public/web-licenses/packages.json': ('sources_sha256', 'tools/dependency_policy.py'),
    'site/public/web-licenses/web-runtime.spdx.json': ('documentNamespace',),
}
CODES = frozenset({'invalid_request', 'foundation_changed', 'policy_changed', 'invalid_profile',
    'source_unavailable', 'source_changed', 'resource_limit', 'git_unavailable', 'unknown_path',
    'missing_path', 'grant_changed', 'grant_unavailable', 'third_party_or_asset_changed',
    'license_declaration_changed', 'unsupported_source_commit', 'unsupported_git_entry',
    'unsupported_first_party_text', 'archive_refused', 'deadline', 'unavailable'})


class Refused(ValueError):
    def __init__(self, code):
        self.code = code if code in CODES else 'unavailable'
        super().__init__('Source-copy V3 unavailable.')


def need(value, code='invalid_profile'):
    if not value:
        raise Refused(code)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def capture(path, limit):
    path = Path(path)
    need(not path.is_symlink() and not any(p.is_symlink() for p in path.parents), 'source_unavailable')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(fd)
        need(stat.S_ISREG(before.st_mode) and before.st_nlink == 1 and 0 <= before.st_size <= limit,
             'resource_limit')
        chunks = bytearray()
        while len(chunks) <= limit:
            raw = os.read(fd, min(65536, limit + 1 - len(chunks)))
            if not raw:
                break
            chunks.extend(raw)
        after = os.fstat(fd)
        key = lambda x: (x.st_dev, x.st_ino, x.st_size, x.st_mtime_ns, x.st_ctime_ns)
        need(len(chunks) == before.st_size and key(before) == key(after) == key(path.lstat()),
             'source_changed')
        return bytes(chunks)
    finally:
        os.close(fd)


def pinned_v2():
    raw = capture(ROOT/'tools/source_release_policy_v2.py', 100000)
    need(sha(raw) == V2_METHOD_SHA256, 'foundation_changed')
    original = builtins.__import__
    def standard(name, globals=None, locals=None, fromlist=(), level=0):
        need(level == 0 and name in {'argparse', 'builtins', 'hashlib', 'json', 'os', 'pathlib',
             're', 'stat', 'subprocess', 'sys', 'time'}, 'foundation_changed')
        return original(name, globals, locals, fromlist, level)
    namespace = {'__name__': '_captured_source_copy_v2',
                 '__file__': str(ROOT/'tools/source_release_policy_v2.py'),
                 '__builtins__': {**vars(builtins), '__import__': standard}}
    exec(compile(raw, '<pinned-source-copy-v2>', 'exec'), namespace)
    return types.SimpleNamespace(**namespace), raw


def overlay(raw, base, v2):
    need(sha(raw) == POLICY_SHA256, 'policy_changed')
    d = v2.parse(raw)
    need(type(d) is dict and set(d) == {'profile', 'base_commit', 'v2_method_sha256',
         'v2_policy_sha256', 'source_observation', 'copied_files', 'project_files', 'origins',
         'metadata_transitions', 'claims'})
    need(d['profile'] == PROFILE and d['base_commit'] == BASE and
         d['v2_method_sha256'] == V2_METHOD_SHA256 and d['v2_policy_sha256'] == V2_POLICY_SHA256)
    need(type(d['claims']) is dict and set(d['claims']) == set(FALSE_CLAIMS) and
         all(d['claims'][k] is False for k in FALSE_CLAIMS))
    need(type(d['source_observation']) is dict and
         d['source_observation'].get('candidate_is_protected') is False)
    need(type(d['copied_files']) is list and len(d['copied_files']) <= MAX_COPIED and
         type(d['project_files']) is list and len(d['project_files']) <= MAX_PROJECT and
         type(d['origins']) is dict and len(d['origins']) <= MAX_ORIGINS)
    copied = {}
    for r in d['copied_files']:
        need(type(r) is dict and set(r) == {'path', 'mode', 'git_blob_oid', 'sha256', 'bytes', 'origin'})
        n = v2.path_name(r['path'])
        need(n not in base and n not in copied and r['mode'] in ('100644', '100755') and
             type(r['git_blob_oid']) is str and OID.fullmatch(r['git_blob_oid']) and
             type(r['sha256']) is str and SHA.fullmatch(r['sha256']) and
             type(r['bytes']) is int and 0 <= r['bytes'] <= v2.MAX_FILE and
             r['origin'] in d['origins'])
        copied[n] = r
    project = set()
    for n in d['project_files']:
        v2.path_name(n)
        need(n not in base and n not in copied and n not in project)
        project.add(n)
    for k, r in d['origins'].items():
        need(type(k) is str and 0 < len(k) <= 1000 and type(r) is dict and
             set(r) == {'license', 'source_evidence', 'copy_scope', 'required_anchors', 'unresolved'})
        need(all(type(r[f]) is str and 0 < len(r[f]) <= 8000 for f in
                 ('license', 'source_evidence', 'copy_scope')))
        need(type(r['unresolved']) is list and len(r['unresolved']) <= 32 and
             all(type(x) is str and 0 < len(x) <= 2000 for x in r['unresolved']))
        need(type(r['required_anchors']) is list and len(r['required_anchors']) <= 128 and
             (bool(r['required_anchors']) or bool(r['unresolved'])))
        names = set()
        for a in r['required_anchors']:
            need(type(a) is dict and set(a) == {'path', 'sha256'} and
                 type(a['sha256']) is str and SHA.fullmatch(a['sha256']))
            n = v2.path_name(a['path'])
            need(n not in names and n in base.keys() | copied.keys())
            names.add(n)
    transition_schema(d['metadata_transitions'], base, project, v2)
    return d, copied, project


def transition_schema(d, base, project, v2):
    need(type(d) is dict and set(d) == {'producer_path', 'old_producer_sha256',
         'new_producer_sha256', 'evidence', 'rows'})
    need(d['producer_path'] == 'tools/dependency_policy.py' and d['producer_path'] in base and
         all(type(d[k]) is str and SHA.fullmatch(d[k]) for k in
             ('old_producer_sha256', 'new_producer_sha256')) and
         d['old_producer_sha256'] != d['new_producer_sha256'])
    evidence = d['evidence']
    need(type(evidence) is dict and set(evidence) == {'path', 'sha256'} and
         v2.path_name(evidence['path']) in project and type(evidence['sha256']) is str and
         SHA.fullmatch(evidence['sha256']))
    need(type(d['rows']) is list and len(d['rows']) == 3)
    names = set()
    for r in d['rows']:
        need(type(r) is dict and set(r) == {'path', 'old', 'new', 'json_path', 'old_value', 'new_value'})
        n = r['path'];need(type(n) is str and n in METADATA_LEAVES and n not in names)
        names.add(n)
        need(type(r['json_path']) is list and r['json_path'] == list(METADATA_LEAVES[n]) and
             all(type(r[k]) is str for k in ('old_value', 'new_value')))
        old, new = r['old'], r['new']
        need(type(old) is dict and set(old) == {'mode', 'git_blob_oid', 'bytes', 'sha256', 'category', 'origin'} and
             type(new) is dict and set(new) == {'mode', 'git_blob_oid', 'bytes', 'sha256'})
        for record in (old, new):
            need(record['mode'] in ('100644', '100755') and type(record['git_blob_oid']) is str and
                 OID.fullmatch(record['git_blob_oid']) and type(record['sha256']) is str and
                 SHA.fullmatch(record['sha256']) and type(record['bytes']) is int and
                 0 <= record['bytes'] <= v2.MAX_CHANGED_TEXT)
        need((old['mode'], old['git_blob_oid'], old['bytes'], old['category']) == base[n][:4] and
             old['category'] == 'other-retained-terms' and type(old['origin']) is str and
             new['mode'] == old['mode'] and new['git_blob_oid'] != old['git_blob_oid'])
        if len(METADATA_LEAVES[n]) == 2:
            need(r['old_value'] == d['old_producer_sha256'] and r['new_value'] == d['new_producer_sha256'])
        else:
            need(all(x.startswith('urn:aitrustid:spdx:web-npm:') and SHA.fullmatch(x.rsplit(':', 1)[1])
                     for x in (r['old_value'], r['new_value'])))
    need(names == set(METADATA_LEAVES))


def json_differences(old, new, path=()):
    # Types participate in equality: bool/int aliases never hide a changed leaf.
    if type(old) is not type(new):
        return [(list(path), old, new)]
    if type(old) is dict:
        if old.keys() != new.keys():
            return [(list(path), old, new)]
        return [difference for k in sorted(old) for difference in json_differences(old[k], new[k], path+(k,))]
    if type(old) is list:
        if len(old) != len(new):
            return [(list(path), old, new)]
        return [difference for i in range(len(old)) for difference in json_differences(old[i], new[i], path+(i,))]
    return [] if old == new else [(list(path), old, new)]


def metadata_expected(v2, d2, legacy, base, additions, observed, read_blob, tick):
    d = additions['metadata_transitions'];rows = {r['path']: r for r in d['rows']}
    origins = {r[0]: r[5] for r in d2['delta']}
    selected_new = []
    for n, r in rows.items():
        tick();need(r['old']['origin'] == origins.get(n), 'grant_changed')
        need(n not in legacy['grant_anchors'], 'grant_changed')
        new = r['new'];state = observed[n]
        if state == (new['mode'], new['git_blob_oid'], new['bytes']):
            selected_new.append(n)
        else:
            need(state == base[n][:3], 'third_party_or_asset_changed')
    need(not selected_new or len(selected_new) == 3, 'source_changed')
    phase = 'new' if selected_new else 'old'
    producer = observed[d['producer_path']]
    need(sha(read_blob(producer[1], producer[2])) == d[phase+'_producer_sha256'], 'source_changed')
    if selected_new:
        evidence = d['evidence'];need(evidence['path'] in observed, 'missing_path')
        item = observed[evidence['path']]
        need(sha(read_blob(item[1], item[2])) == evidence['sha256'], 'source_changed')
    parsed = {'old': {}, 'new': {}}
    for n, r in rows.items():
        for key in ('old', 'new') if selected_new else ('old',):
            tick();item = r[key];raw = read_blob(item['git_blob_oid'], item['bytes'])
            need(sha(raw) == item['sha256'], 'source_changed');parsed[key][n] = v2.parse(raw)
        if selected_new:
            need(json_differences(parsed['old'][n], parsed['new'][n]) ==
                 [(r['json_path'], r['old_value'], r['new_value'])], 'grant_changed')
    package_path = 'site/public/web-licenses/packages.json'
    spdx_path = 'site/public/web-licenses/web-runtime.spdx.json'
    for key in ('old', 'new') if selected_new else ('old',):
        source_map = parsed[key][package_path]['sources_sha256']
        need(type(source_map) is dict and source_map['tools/dependency_policy.py'] == d[key+'_producer_sha256'],
             'source_changed')
        need(parsed[key]['sbom/reviews/zlib-runtime/manifest.json']['producer_sha256']['tools/dependency_policy.py'] ==
             d[key+'_producer_sha256'], 'source_changed')
        canonical = json.dumps(source_map, sort_keys=True, ensure_ascii=True, allow_nan=False,
                               separators=(',', ':')).encode()
        need(parsed[key][spdx_path]['documentNamespace'] == 'urn:aitrustid:spdx:web-npm:'+sha(canonical),
             'source_changed')
    expected = dict(base)
    if selected_new:
        for n, r in rows.items():
            new = r['new'];expected[n] = (new['mode'], new['git_blob_oid'], new['bytes'], *base[n][3:])
    return expected, len(selected_new)


def check(v2, d2, legacy, base, additions, copied, project, observed, read_blob, tick):
    need(0 < len(observed) <= v2.MAX_FILES, 'resource_limit')
    total = 0
    for row in observed.values():
        need(type(row) in (tuple, list) and len(row) == 3 and row[0] in ('100644', '100755') and
             type(row[1]) is str and OID.fullmatch(row[1]) and type(row[2]) is int and
             0 <= row[2] <= v2.MAX_FILE, 'unsupported_git_entry')
        total += row[2]
        need(total <= v2.MAX_TOTAL, 'resource_limit')
    # Check the full denominator before any phase filtering.
    need(observed.keys() <= base.keys() | copied.keys() | project |
         set(d2['named_first_party_extensions']), 'unknown_path')
    need(base.keys() <= observed.keys(), 'missing_path')
    present = {n: r for n, r in copied.items() if n in observed}
    for n, r in present.items():
        tick()
        need(observed[n] == (r['mode'], r['git_blob_oid'], r['bytes']), 'third_party_or_asset_changed')
        origin = additions['origins'][r['origin']]
        need(not origin['unresolved'], 'grant_unavailable')
        for a in origin['required_anchors']:
            need(a['path'] in observed, 'missing_path')
            need(sha(read_blob(observed[a['path']][1], observed[a['path']][2])) == a['sha256'],
                 'grant_changed')
        need(sha(read_blob(r['git_blob_oid'], r['bytes'])) == r['sha256'], 'source_changed')
    expected, transitioned = metadata_expected(v2, d2, legacy, base, additions, observed, read_blob, tick)
    for n, r in present.items():
        expected[n] = (r['mode'], r['git_blob_oid'], r['bytes'], 'v3-immutable-copied-source', None)
    new_project = observed.keys() & project
    # V2's policy array/global limits are not modified. Named V3 project text is
    # inspected separately using the very same operation-wide budget and clock.
    subset = {n: r for n, r in observed.items() if n not in new_project}
    facts = v2.checked(d2, legacy, expected, subset, read_blob, tick)
    allowed = {'SPDX-License-Identifier: Apache-2.0',
               'Licensed under the Apache License, Version 2.0.',
               'Copyright 2026 Michael Raashad McGuire and AITrust-ID contributors.'}
    for n in sorted(new_project):
        tick()
        raw = read_blob(observed[n][1], observed[n][2])
        _, lines = v2.markers(raw)
        need(all(x.strip().lstrip('#/*; ').rstrip('*/ ').strip() in allowed for x in lines),
             'license_declaration_changed')
    return {'files': len(observed), 'present_optional_copied_files': len(present),
            'generated_metadata_transitions': transitioned,
            'introduced_named_project_text_files': len(new_project) + facts['introduced_named_project_text_files'],
            'changed_named_project_text_files': facts['changed_named_project_text_files']}


def _blob_reader(v2, git, tick):
    """One cache and cumulative inspection budget across every classification phase."""
    cache, inspected = {}, 0
    def read_blob(oid, size):
        nonlocal inspected
        tick()
        need(type(size) is int and 0 <= size <= v2.MAX_CHANGED_TEXT, 'resource_limit')
        if oid in cache:
            need(len(cache[oid]) == size, 'source_changed');return cache[oid]
        inspected += size
        need(inspected <= v2.MAX_INSPECTED_TEXT, 'resource_limit')
        body = git(['cat-file', 'blob', oid], min(size+1, v2.MAX_CHANGED_TEXT))
        need(len(body) == size and hashlib.sha1(b'blob '+str(size).encode()+b'\0'+body).hexdigest() == oid,
             'source_changed')
        cache[oid] = body;return body
    return read_blob


def verify(root=ROOT, source_commit=None):
    result = {'profile': PROFILE, 'pass': False, 'status': 'UNAVAILABLE',
              'source_copy_profile_satisfied': False, **{k: False for k in FALSE_CLAIMS}}
    try:
        need(Path(root).resolve() == ROOT, 'source_unavailable')
        deadline = time.monotonic() + 30
        def tick(): need(time.monotonic() < deadline, 'deadline')
        v2, v2_raw = pinned_v2()
        raw = capture(ROOT/POLICY, MAX_POLICY)
        old_raw = v2.file_bytes(ROOT/v2.POLICY, v2.MAX_POLICY)
        legacy_raw = v2.file_bytes(ROOT/v2.LEGACY, v2.MAX_POLICY)
        d2, legacy, base = v2.policy(old_raw, legacy_raw)
        need(d2['selected_commit'] == BASE, 'foundation_changed')
        additions, copied, project = overlay(raw, base, v2)
        method = sha(capture(Path(__file__), 100000))
        run = v2.worker()
        def git(args, limit=v2.MAX_LISTING):
            tick()
            value = run([sys.executable, '-I', '-S', '-B', '-c', v2.GIT_EXEC,
                         '-C', str(ROOT), *args], input=b'',
                        timeout=min(20, deadline-time.monotonic()), output_limit=limit)
            need(value.returncode == 0, 'git_unavailable');tick();return value.stdout
        head = git(['rev-parse', '--verify', 'HEAD^{commit}'], 100).decode().strip()
        commit = head if source_commit is None else source_commit
        need(type(commit) is str and OID.fullmatch(commit), 'unsupported_source_commit')
        need(git(['cat-file', '-t', commit], 100) == b'commit\n', 'unsupported_source_commit')
        git(['merge-base', '--is-ancestor', BASE, commit], 100)
        need(git(['rev-parse', BASE+'^{tree}'],100).decode().strip()==d2['selected_tree'] and
             git(['rev-parse',v2.PROTECTED+'^{tree}'],100).decode().strip()==d2['protected_baseline_tree'],
             'source_changed')
        tree = git(['rev-parse', commit+'^{tree}'], 100).decode().strip()
        need(OID.fullmatch(tree), 'git_unavailable')
        observed, total = v2.tree_rows(git(['ls-tree', '-r', '-l', '-z', '--full-tree', commit]))
        read_blob = _blob_reader(v2, git, tick)
        facts = check(v2, d2, legacy, base, additions, copied, project, observed, read_blob, tick)
        need(git(['rev-parse', '--verify', 'HEAD^{commit}'], 100).decode().strip() == head,
             'source_changed')
        need(capture(ROOT/POLICY, MAX_POLICY) == raw and
             capture(ROOT/'tools/source_release_policy_v2.py', 100000) == v2_raw and
             v2.file_bytes(ROOT/v2.POLICY, v2.MAX_POLICY) == old_raw and
             v2.file_bytes(ROOT/v2.LEGACY, v2.MAX_POLICY) == legacy_raw and
             sha(v2.file_bytes(ROOT/'tools/source_release_policy.py', 100000)) == v2.LEGACY_HELPER_SHA256 and
             sha(v2.file_bytes(ROOT/'scripts/worker_process.py', 100000)) == v2.WORKER_SHA256 and
             sha(capture(Path(__file__), 100000)) == method, 'source_changed')
        tick()
        result.update({'pass': True, 'status': 'SOURCE_COPY_PROFILE_SATISFIED',
             'source_copy_profile_satisfied': True, 'source_commit': commit, 'source_tree': tree,
             'checkout_commit': head, 'source_bytes': total, **facts,
             'policy_sha256': POLICY_SHA256, 'method_sha256': method,
             'legacy_policy_sha256': v2.LEGACY_SHA256, 'v2_policy_sha256': V2_POLICY_SHA256,
             'protected_baseline_commit': BASE, 'selected_profile_base_is_protected_release': True,
             'selected_source_protected_release_claimed': commit == BASE})
    except (OSError, ValueError, TypeError, KeyError, OverflowError, RecursionError, RuntimeError,
            subprocess.SubprocessError) as failure:
        code = getattr(failure, 'code', 'unavailable')
        result['reason'] = code if code in CODES else 'unavailable'
    return result


def verify_archive(raw, *, source_commit):
    result = {'profile': 'source-copy-archive-obligations/v3', 'pass': False, 'status': 'UNAVAILABLE',
              'source_copy_profile_satisfied': False, 'trusted_git_bytes_matched': False,
              'signature_verified': False, **{k: False for k in FALSE_CLAIMS}}
    try:
        need(type(raw) is bytes and 0 < len(raw) <= MAX_ARCHIVE and
             type(source_commit) is str and OID.fullmatch(source_commit), 'invalid_request')
        deadline = time.monotonic()+95
        copy = verify(source_commit=source_commit)
        need(copy.get('pass') is True, copy.get('reason', 'unavailable'))
        v2, v2_raw = pinned_v2();source = v2.file_bytes(ROOT/'tools/source_snapshot_binding.py', 100000)
        need(sha(source) == v2.BINDING_SHA256, 'foundation_changed')
        method = sha(capture(Path(__file__), 100000))
        program = 'exec(compile('+repr(source)+", '<captured-source-binding>', 'exec'), "+repr({
            '__name__':'__main__','__file__':str(ROOT/'tools/source_snapshot_binding.py')})+')'
        remaining = min(60, deadline-time.monotonic());need(remaining > 0, 'deadline')
        summary = v2._binding_capture(source)([sys.executable,'-I','-S','-B','-c',program,
            '--binding-worker',str(ROOT),source_commit],raw,time.monotonic()+remaining,4096,new_session=True)
        body = v2.parse(summary)
        need(type(body) is dict and set(body) == {'profile','pass','source_commit','source_tree',
            'source_files','source_bytes','archive_sha256','trusted_git_bytes_matched',
            'signature_verified','rights_approved','release_authorized'} and
            body['profile']=='source-snapshot-trusted-git-binding/v1' and body['pass'] is True and
            body['source_commit']==source_commit and body['source_tree']==copy['source_tree'] and
            type(body['source_files']) is int and body['source_files']==copy['files'] and
            type(body['source_bytes']) is int and body['source_bytes']==copy['source_bytes'] and
            body['archive_sha256']==sha(raw) and body['trusted_git_bytes_matched'] is True and
            all(body[k] is False for k in ['signature_verified','rights_approved','release_authorized']),
            'archive_refused')
        need(capture(ROOT/'tools/source_release_policy_v2.py',100000)==v2_raw and
             sha(capture(ROOT/POLICY,MAX_POLICY))==POLICY_SHA256 and
             v2.file_bytes(ROOT/'tools/source_snapshot_binding.py',100000)==source and
             sha(v2.file_bytes(ROOT/v2.POLICY,v2.MAX_POLICY))==V2_POLICY_SHA256 and
             sha(v2.file_bytes(ROOT/v2.LEGACY,v2.MAX_POLICY))==v2.LEGACY_SHA256 and
             sha(v2.file_bytes(ROOT/'tools/source_release_policy.py',100000))==v2.LEGACY_HELPER_SHA256 and
             sha(v2.file_bytes(ROOT/'scripts/worker_process.py',100000))==v2.WORKER_SHA256 and
             sha(capture(Path(__file__),100000))==method,'source_changed')
        need(time.monotonic()<deadline,'deadline')
        result.update({'pass':True,'status':'COPY_OBLIGATIONS_AND_GIT_BYTES_BOUND',
            'source_copy_profile_satisfied':True,'trusted_git_bytes_matched':True,
            'source_commit':source_commit,'source_tree':body['source_tree'],
            'source_files':body['source_files'],'source_bytes':body['source_bytes'],
            'archive_sha256':body['archive_sha256'],'archive_bytes':len(raw),
            'policy_sha256':POLICY_SHA256,'method_sha256':method,
            'binding_method_sha256':v2.BINDING_SHA256})
    except (OSError, ValueError, TypeError, KeyError, OverflowError, RecursionError, RuntimeError,
            subprocess.SubprocessError) as failure:
        code=getattr(failure,'code','archive_refused')
        result['reason']=code if code in CODES else 'archive_refused'
    return result


class Parser(argparse.ArgumentParser):
    def error(self, message): raise Refused('invalid_request')


def main(argv=None):
    try:
        parser=Parser(description=__doc__);parser.add_argument('--source-commit');parser.add_argument('--archive',type=Path)
        args=parser.parse_args(argv)
        if args.archive is None:result=verify(source_commit=args.source_commit)
        else:
            need(args.source_commit is not None,'invalid_request')
            result=verify_archive(capture(args.archive,MAX_ARCHIVE),source_commit=args.source_commit)
    except (OSError,ValueError,TypeError) as failure:
        code=getattr(failure,'code','unavailable');result={'profile':PROFILE,'pass':False,'status':'UNAVAILABLE',
            'reason':code if code in CODES else 'unavailable',**{k:False for k in FALSE_CLAIMS}}
    print(json.dumps(result,sort_keys=True));return 0 if result['pass'] else 2


if __name__=='__main__':raise SystemExit(main())
