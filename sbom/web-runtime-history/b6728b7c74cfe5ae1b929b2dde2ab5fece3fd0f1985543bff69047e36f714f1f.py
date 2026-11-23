"""Finite five-file browser-runtime notices/source-offer construction and checking.

This does not admit a distribution route or authorize a release. Only pinned,
trusted project producer code executes; publisher source/package code never does.
"""
import builtins
import hashlib
import io
import json
import os
from pathlib import Path
import re
import stat
import time
import types
import zipfile
from tools import artifact_evidence_io as evidence

ROOT = Path(__file__).resolve().parents[1]
PROFILE = 'five-file-browser-runtime-obligations/v1'
MANIFEST = 'sbom/web-runtime/manifest.json'
MANIFEST_SHA256 = '5d662e2a8c1feeb35465370a01eab9a192c21b0d1eb5c60cbc7021c92e592184'
MAX_READS = 128
MAX_READ_BYTES = 64_000_000
MAX_CACHE = 16_000_000
MAX_OUTPUT = 8_000_000
MAX_FDS = 128
DEADLINE = 60
PAYLOAD_RESERVATION = 123_314_272
MAX_PAYLOAD = 128_000_000
CLAIMS = {'distribution_route_admitted': False, 'signature_verified': False,
          'all_project_obligations_complete': False, 'binary_object_closure_proved': False,
          'compiler_reproduced': False, 'legal_clearance': False, 'accuracy_validated': False}
RUNTIME = frozenset(('pyodide.mjs', 'pyodide.asm.mjs', 'pyodide.asm.wasm',
                     'python_stdlib.zip', 'pyodide-lock.json'))
NOTICE_INPUTS = ('sbom/web-runtime/CPYTHON-EMBEDDED-NOTICES.txt',
                'sbom/web-runtime/EMSCRIPTEN-SYSTEM-NOTICES.txt',
                'sbom/web-runtime/EXTERNAL-RUNTIME-NOTICES.txt')
LEGACY_LICENSES = {
 'device-licenses/pyodide-MPL-2.0.txt': 'site/public/device-licenses/pyodide-MPL-2.0.txt',
 'device-licenses/python-license.txt': 'site/public/device-licenses/python-license.txt',
 'device-licenses/source.txt': 'site/public/device-licenses/source.txt',
 'device-licenses/unicode-license.txt': 'site/public/device-licenses/unicode-license.txt',
 'device-licenses/python-stdlib-notices.txt': 'sbom/nested-runtime/PYTHON-STDLIB-NOTICES.txt'}


class Unavailable(ValueError):
    def __init__(self): super().__init__('Selected runtime obligations unavailable.')


class OutputUncertain(Unavailable):
    output_may_exist = True
    def __init__(self): ValueError.__init__(self, 'Private runtime outputs may exist; inspect before retrying.')


def need(ok):
    if not ok: raise Unavailable()


def sha(raw): return hashlib.sha256(raw).hexdigest()


def encoded(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=True, allow_nan=False,
                      separators=(',', ':')).encode('ascii')


def safe(name):
    need(type(name) is str and len(name) <= 240 and name.isascii()
         and re.fullmatch(r'[A-Za-z0-9_.\-/]+', name) and not name.startswith('/')
         and all(p not in ('', '.', '..') for p in name.split('/')))
    return name


class Budget:
    def __init__(self, root):
        self.root = Path(root).absolute()
        self.capture = evidence.Capture()
        self.started = time.monotonic()
        self.reads = self.read_bytes = self.cache_bytes = self.nodes = 0
        self.cache = {}
        self.allowed = {}
        self.closed = False
        need(PAYLOAD_RESERVATION <= MAX_PAYLOAD)

    def tick(self): need(time.monotonic() - self.started < DEADLINE)

    def capacity(self, path, file=True):
        path = Path(path).absolute()
        missing = sum(1 for i in range(1, len(path.parts))
                      if path.parts[:i] not in self.capture.directory_cache)
        need(len(self.capture.fds) + missing + int(file) <= MAX_FDS)

    def charge(self, size):
        self.tick()
        need(type(size) is int and 0 < size and self.reads < MAX_READS
             and self.read_bytes + size <= MAX_READ_BYTES)
        self.reads += 1
        self.read_bytes += size

    def read(self, root, name, limit=200_000):
        need(Path(root).absolute() == self.root)
        safe(name)
        need(type(limit) is int and 0 < limit <= 2_000_000 and name in self.allowed)
        row = self.allowed[name]
        need(row['bytes'] <= limit)
        self.charge(row['bytes'])
        if name not in self.cache:
            need(self.cache_bytes + row['bytes'] <= MAX_CACHE)
            self.capacity(self.root/name)
            raw = self.capture.read(self.root/name, limit, private=False)
            need(len(raw) == row['bytes'] and sha(raw) == row['sha256'])
            self.cache[name] = raw
            self.cache_bytes += len(raw)
        self.tick()
        return self.cache[name]

    def parse(self, raw, limit=512_000):
        self.tick(); need(type(raw) is bytes and 0 < len(raw) <= limit)
        def pairs(rows):
            result = {}
            for key, value in rows:
                need(key not in result); result[key] = value
            return result
        value = json.loads(raw.decode('utf8'), object_pairs_hook=pairs,
                           parse_constant=lambda _: need(False))
        def visit(v, depth=0):
            self.nodes += 1
            need(depth <= 32 and self.nodes <= 100_000)
            if type(v) is dict:
                for key, child in v.items(): key.encode('utf8'); visit(child, depth+1)
            elif type(v) is list:
                for child in v: visit(child, depth+1)
            elif type(v) is str: v.encode('utf8')
        visit(value); self.tick(); return value

    def initialize(self):
        self.capacity(self.root/MANIFEST)
        self.charge((self.root/MANIFEST).lstat().st_size)
        raw = self.capture.read(self.root/MANIFEST, 512_000, private=False)
        need(sha(raw) == MANIFEST_SHA256)
        m = self.parse(raw)
        need(m['profile'] == PROFILE and m['claims'] == CLAIMS
             and all(type(v) is bool and v is False for v in m['claims'].values())
             and type(m['inputs']) is dict and len(m['inputs']) == 67
             and set(m['runtime']) == RUNTIME)
        for name, row in m['inputs'].items():
            safe(name)
            need(type(row) is dict and set(row) == {'bytes', 'sha256'}
                 and type(row['bytes']) is int and 0 < row['bytes'] <= 2_000_000
                 and type(row['sha256']) is str and re.fullmatch('[0-9a-f]{64}', row['sha256']))
        self.allowed = m['inputs']
        self.read(self.root, 'tools/artifact_evidence_io.py', 2_000_000)
        return m

    def finish(self):
        self.tick(); self.capture.check(); self.tick()

    def close(self):
        if not self.closed:
            self.closed = True; self.capture.close()


def private_producers(budget):
    """Execute captured trusted project functions with one bounded read provider."""
    standard = builtins.__import__
    def js_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == 'tools.dependency_policy': return types.SimpleNamespace(read=budget.read)
        return standard(name, globals, locals, fromlist, level)
    js_name = 'tools/pyodide_js_sources.py'
    js_ns = {'__name__': '_runtime_pinned_js', '__file__': str(budget.root/js_name),
             '__builtins__': {**vars(builtins), '__import__': js_import}}
    exec(compile(budget.read(budget.root, js_name), '<pinned-js-producer>', 'exec'), js_ns)
    js = types.SimpleNamespace(**js_ns)
    def z_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == 'tools': return types.SimpleNamespace(pyodide_js_sources=js)
        return standard(name, globals, locals, fromlist, level)
    z_name = 'tools/zlib_source_delivery.py'
    z_ns = {'__name__': '_runtime_pinned_zlib', '__file__': str(budget.root/z_name),
            '__builtins__': {**vars(builtins), '__import__': z_import}}
    exec(compile(budget.read(budget.root, z_name), '<pinned-zlib-producer>', 'exec'), z_ns)
    return js, z_ns


def zip_bytes(members):
    need(len(members) <= 32 and sum(map(len, members.values())) < 1_000_000)
    out = io.BytesIO()
    with zipfile.ZipFile(out, 'w', compression=zipfile.ZIP_STORED, allowZip64=False) as archive:
        for name, raw in sorted(members.items()):
            safe(name); entry = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
            entry.create_system = 3; entry.external_attr = 0o100644 << 16
            archive.writestr(entry, raw)
    return out.getvalue()


def expected(budget, m):
    budget.tick()
    js, z = private_producers(budget)
    result = {'runtime-js-sources/'+n: b for n, b in js.outputs(budget.root).items()}
    budget.tick()
    result.update({'runtime-zlib-sources/'+n: b for n, b in z['outputs'](budget.root).items()})
    for output, source in LEGACY_LICENSES.items(): result[output] = budget.read(budget.root, source, 2_000_000)
    need(set(result) == set(m['legacy_outputs']))
    for name, raw in result.items():
        need({'bytes': len(raw), 'sha256': sha(raw)} == m['legacy_outputs'][name])
    # Verify ALL fixed retained inputs, including grants not reopened by legacy producers.
    for name in budget.allowed:
        if name not in budget.cache: budget.read(budget.root, name, 2_000_000)
    # Parse the fixed new facts once, cumulatively bounded; no supplied success flag can approve a changed table.
    for name in budget.allowed:
        if name.startswith('sbom/web-runtime/') and name.endswith('.json'):
            budget.parse(budget.cache[name])
    hi = budget.parse(budget.cache['sbom/web-runtime/hiwire-preferred-source.json'])
    need(hi['commit'] == '6a1e67280a15d929ebeceee54a6358c9c8d5f697' and len(hi['files']) == 13)
    source_members = {}
    for row in hi['files']:
        raw = budget.cache[row['path']]
        need(len(raw) == row['bytes'] and sha(raw) == row['sha256'])
        source_members['hiwire/'+safe(row['name'])] = raw
    recipe_raw = budget.cache['sbom/web-runtime/publisher-recipe-facts.json']
    recipe = budget.parse(recipe_raw)
    source_members['publisher/recipe-and-patch-identities.json'] = recipe_raw
    source_members['publisher/cpython-Makefile'] = recipe['files']['cpython/Makefile']['text'].encode()
    source_members['publisher/Makefile.envs'] = recipe['files']['Makefile.envs']['text'].encode()
    source_members['OBTAIN-SOURCE.txt'] = (hi['obtain_information']+'\n'+hi['parent_recipe_patches']+'\n'
      'The complete Pyodide archive and its nine CPython patches are also supplied unchanged in runtime-js-sources/PYODIDE-JS-SOURCES.zip.\n'
      'No covered source was changed by this packaging. Publisher recipe correspondence does not claim compiler reproduction.\n').encode()
    source_members['index.json'] = encoded({'profile': 'selected-hiwire-source-offer/v1',
      'commit': hi['commit'], 'members': {n: {'bytes': len(b), 'sha256': sha(b)} for n, b in sorted(source_members.items())},
      'claims': CLAIMS})+b'\n'
    offer = zip_bytes(source_members)
    notices = (b'Selected browser runtime: additional component notices and source access.\n'
      b'This is a finite exact-artifact check, not project-wide permission or legal clearance.\n'
      b'Pyodide MPL source: ../runtime-js-sources/PYODIDE-JS-SOURCES.zip.\n'
      b'Hiwire MPL source: HIWIRE-SOURCES.zip (preferred source, build files and full MPL license included).\n'
      b'Zlib source: ../runtime-zlib-sources/ZLIB-SOURCES.zip.\n'
      b'PSF/Unicode/stdlib grants: ../device-licenses/. No training, accuracy or authenticity assertion is made.\n')
    for name in NOTICE_INPUTS: notices += ('\n===== '+name+' =====\n').encode()+budget.cache[name]+b'\n'
    result['runtime-obligations/NOTICES.txt'] = notices
    result['runtime-obligations/HIWIRE-SOURCES.zip'] = offer
    result['runtime-obligations/obligations.json'] = encoded({'profile': PROFILE,
      'manifest_sha256': MANIFEST_SHA256, 'runtime': m['runtime'], 'obligations': m['obligations'],
      'companion_files': {n: {'bytes': len(b), 'sha256': sha(b)} for n, b in sorted(result.items())},
      'claims': CLAIMS})+b'\n'
    need(len(result) == 14 and sum(map(len, result.values())) <= MAX_OUTPUT)
    budget.finish(); return result


def report(budget, m, outputs, received=False):
    return {'profile': PROFILE, 'pass': True, 'retained_facts_verified': True,
      'received_files_verified': 19 if received else 0, 'runtime_files': 5,
      'stdlib_inventory_members': 614, 'required_companions': 14,
      'source_offers': 3, 'manifest_sha256': MANIFEST_SHA256,
      'outputs': {n: {'bytes': len(b), 'sha256': sha(b)} for n, b in sorted(outputs.items())},
      'resources': {'read_calls': budget.reads, 'logical_read_bytes': budget.read_bytes,
                    'cached_bytes': budget.cache_bytes, 'held_fds': len(budget.capture.fds),
                    'logical_payload_reservation': PAYLOAD_RESERVATION}, 'claims': CLAIMS.copy()}


def unavailable_boundary(function):
    """Translate inherited fixed primitive refusals into this API's fixed type."""
    def operation(*args, **kwargs):
        try: return function(*args, **kwargs)
        except Unavailable: raise
        except Exception: raise Unavailable() from None
    return operation


@unavailable_boundary
def verify(root=ROOT):
    b = Budget(root)
    try:
        m = b.initialize(); outputs = expected(b, m); b.finish()
        return report(b, m, outputs)
    finally: b.close()


def membership(budget, directory, wanted):
    directory = Path(directory).absolute(); budget.capacity(directory/'_membership', file=False)
    parent, name = budget.capture.parent(directory/'_membership', private=False)
    need(set(os.listdir(parent)) == set(wanted)); budget.tick()
    return parent


@unavailable_boundary
def check_built(directory, root=ROOT):
    b = Budget(root)
    try:
        m = b.initialize(); outputs = expected(b, m); base = Path(directory).absolute()
        groups = {'runtime': set(RUNTIME)}
        for name in outputs:
            group, leaf = name.split('/', 1); groups.setdefault(group, set()).add(leaf)
        membership(b, base, groups)
        for group, names in groups.items(): membership(b, base/group, names)
        for name, row in m['runtime'].items():
            path = base/'runtime'/name; b.capacity(path); b.charge(row['bytes'])
            observed = b.capture.artifact(path, limit=12_000_000)
            need(observed == row); b.tick()
        for name, raw in outputs.items():
            b.capacity(base/name); b.charge(len(raw))
            got = b.capture.read(base/name, min(MAX_OUTPUT, max(len(raw), 1)), private=False)
            need(got == raw); b.tick()
        # Fixed hash of stdlib proves the same614 rows as the pinned immutable inventory;
        # no untrusted ZIP is interpreted before its complete runtime hash matches.
        nested = b.parse(b.cache['sbom/nested-runtime/manifest.json'])
        need(len(nested['members']) == 614 and nested['nested'] == {'member': 'package/python_stdlib.zip', **m['runtime']['python_stdlib.zip']})
        for group, names in groups.items(): membership(b, base/group, names)
        membership(b, base, groups)
        b.finish(); return report(b, m, outputs, received=True)
    finally: b.close()


@unavailable_boundary
def prepare(destination, root=ROOT):
    """Write fixed companions to a NEW owner-private directory, never remove failures."""
    b = Budget(root); created = False
    try:
        m = b.initialize(); outputs = expected(b, m); target = Path(destination).absolute()
        b.capacity(target/'_private', file=False)
        parent, leaf = b.capture.parent(target)
        os.mkdir(leaf, 0o700, dir_fd=parent); created = True
        fd = b.capture.directory(target)
        for group in sorted({n.split('/')[0] for n in outputs}): os.mkdir(group, 0o700, dir_fd=fd)
        for name, raw in sorted(outputs.items()):
            b.tick(); b.capacity(target/name)
            held_parent, leaf = b.capture.parent(target/name)
            out = os.open(leaf, os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=held_parent)
            try:
                at = 0
                while at < len(raw):
                    count = os.write(out, raw[at:at+65536]); need(count > 0); at += count; b.tick()
                evidence.verify_written(out, raw)
                os.fsync(out)
            finally: os.close(out)
        for path, (child, _) in b.capture.directory_cache.items():
            if Path(*path).is_relative_to(target): os.fsync(child)
        b.finish(); result = report(b, m, outputs); b.close(); return result
    except Exception:
        if created: raise OutputUncertain() from None
        raise
    finally: b.close()
