"""Selected pinned Pyodide JS source/notice delivery; no global route clearance."""
import base64
import gzip
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import secrets
import shutil
import stat
import tarfile
import zipfile
import zlib
from tools.dependency_policy import read

ROOT = Path(__file__).resolve().parents[1]
BASE = 'sbom/reviews/pyodide-js'
MANIFEST = BASE + '/manifest.json'
RELEASE = 'sbom/nested-runtime/pyodide-wasm-release.json'
LOCK = 'site/package-lock.json'
VERSION = '314.0.7'
COMMIT = 'b1e4fcc2488962f6360a97f19b9982d6fdb5d16f'
PROFILE = 'selected-pyodide-js-source-notices/v1'
RUNTIME_NAMES = frozenset(('pyodide.mjs', 'pyodide.asm.mjs', 'pyodide.asm.wasm',
                           'python_stdlib.zip', 'pyodide-lock.json'))
# Exact observed five-file projection from the SHA512/SHA256-pinned npm archive.
# Rehashing mutable release/cohort metadata cannot replace this reviewed identity.
RUNTIME_PROJECTION_SHA256 = 'f494c20732352d023ff434923888381888e92c3a2984acdd0cc4e824965366b8'
SOURCES = ('tools/pyodide_js_sources.py', 'scripts/pyodide-js-sources.py')
PREFERRED = ('src/js/vendor/stackframe/stackframe.ts',
 'src/js/vendor/stackframe/error-stack-parser.ts', 'src/js/environments.ts',
 'src/js/compat.ts', 'src/js/nativefs.ts', 'src/core/jsverror.ts',
 'src/js/emscripten-settings.ts', 'src/js/version.ts', 'src/js/common/path.ts',
 'src/js/pyodide.ts')
LICENSES = ('LICENSE', 'src/js/vendor/stackframe/LICENSE')
CLAIMS = {'full_wasm_corresponding_source': False, 'all_dependency_obligations': False,
          'compiler_reproduced': False, 'signature_verified': False,
          'legal_clearance': False, 'distribution_route_admitted': False}
MAX_ARCHIVE = 8_000_000
MAX_EXPANDED = 24_000_000
MAX_JSON = 200_000
MAX_OUTPUT = 2_500_000
OUTPUT_NAMES = ('PYODIDE-JS-SOURCES.zip', 'NOTICES.txt', 'index.json')


class SourceError(ValueError):
    """Only fixed diagnostics cross the public command boundary."""


class OutputUncertain(SourceError):
    def __init__(self): super().__init__('Runtime source output may exist; inspect before retrying.')


def need(ok):
    if not ok: raise SourceError('Selected runtime source/notice check refused')


def sha(raw): return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=True, allow_nan=False,
                      separators=(',', ':')).encode()


def unique(rows):
    result = {}
    for key, value in rows:
        need(key not in result); result[key] = value
    return result


def parse(raw):
    need(type(raw) is bytes and 0 < len(raw) <= MAX_JSON)
    value = json.loads(raw.decode('utf-8', 'strict'), object_pairs_hook=unique,
                       parse_constant=lambda _: need(False))
    count = 0
    def walk(v, depth=0):
        nonlocal count
        count += 1; need(depth <= 20 and count <= 5000)
        if isinstance(v, dict):
            for k, child in v.items(): k.encode('utf-8', 'strict'); walk(child, depth+1)
        elif isinstance(v, list):
            for child in v: walk(child, depth+1)
        elif isinstance(v, str): v.encode('utf-8', 'strict')
    walk(value); return value


def safe_relative(name):
    need(type(name) is str and len(name) <= 240 and name.isascii()
         and re.fullmatch(r'[A-Za-z0-9_.\-/]+', name) and not name.startswith('/')
         and all(p not in ('', '.', '..') for p in name.split('/')))
    return name


def expanded_tar(raw):
    """Bound compression expansion AND PAX/longname metadata before tarfile."""
    need(type(raw) is bytes and 0 < len(raw) <= MAX_ARCHIVE)
    expanded = bytearray()
    with gzip.GzipFile(fileobj=io.BytesIO(raw)) as stream:
        while True:
            block = stream.read(min(65536, MAX_EXPANDED-len(expanded)+1))
            if not block: break
            need(len(block) <= MAX_EXPANDED-len(expanded)); expanded.extend(block)
    need(len(expanded) % 512 == 0)
    offset = entries = metadata = 0
    while offset + 512 <= len(expanded):
        header = expanded[offset:offset+512]
        if not any(header):
            need(len(expanded)-offset >= 1024 and not any(expanded[offset:])); break
        entries += 1; need(entries <= 2048)
        field = bytes(header[124:136]).strip(b' \0')
        need(bool(field) and re.fullmatch(b'[0-7]+', field))
        size = int(field, 8); kind = bytes(header[156:157])
        need(kind in (b'0', b'\0', b'5', b'2', b'x', b'g', b'L', b'K'))
        if kind in (b'x', b'g', b'L', b'K'):
            need(size <= 16384); metadata += size; need(metadata <= 1_000_000)
        else: need(size <= 12_000_000)
        end = offset+512+((size+511)//512)*512; need(end <= len(expanded))
        offset = end
    else: need(False)
    return bytes(expanded)


def selected_tar(raw, prefix, wanted, max_member=MAX_JSON):
    need(type(max_member) is int and 0 < max_member <= 12_000_000)
    wanted = set(wanted); found = {}; seen = set()
    expanded = expanded_tar(raw)
    with tarfile.open(fileobj=io.BytesIO(expanded), mode='r:') as archive:
        for count, entry in enumerate(archive):
            need(count < 1024 and entry.name not in seen); seen.add(entry.name)
            name = entry.name.rstrip('/'); safe_relative(name)
            need(name == prefix.rstrip('/') or name.startswith(prefix))
            relative = name[len(prefix):] if name.startswith(prefix) else ''
            if relative in wanted:
                need(entry.isfile() and relative not in found and 0 < entry.size <= max_member)
                with archive.extractfile(entry) as stream: value = stream.read(entry.size+1)
                need(len(value) == entry.size); found[relative] = value
    need(set(found) == wanted); return found


def source_path(raw, suffix): return BASE + '/sources/' + sha(raw) + suffix


def reviewed_runtime(value):
    need(type(value) is dict and set(value) == RUNTIME_NAMES)
    for row in value.values():
        need(type(row) is dict and set(row) == {'bytes', 'sha256'}
             and type(row['bytes']) is int and 0 < row['bytes'] <= 12_000_000
             and type(row['sha256']) is str
             and re.fullmatch('[a-f0-9]{64}', row['sha256']))
    need(sha(canonical(value)) == RUNTIME_PROJECTION_SHA256)
    return value


def release_inputs(root):
    release_raw = read(root, RELEASE, MAX_JSON)
    release = parse(release_raw)
    need(type(release) is dict)
    reviewed_runtime(release['runtime_members'])
    lock_raw = read(root, LOCK, 1_000_000)
    lock = json.loads(lock_raw, object_pairs_hook=unique)['packages']['node_modules/pyodide']
    need(release['pyodide_version'] == VERSION and release['pyodide_commit'] == COMMIT
         and lock['version'] == VERSION and lock['resolved'] == release['archives']['npm.tgz']['url'])
    need(release['archives']['source.tar.gz'] == {
        'url': 'https://codeload.github.com/pyodide/pyodide/tar.gz/'+COMMIT,
        'bytes': 1465591, 'sha256': 'a9c7ac66311ed7e0805b9970054ee5be4f69d02204d28bffe4b017310a24bad9'})
    need(release['archives']['npm.tgz']['sha256'] == '66b7949e5a0cba2250b586d7e368bf12fb482800748d182c4618254b685ffaa0')
    return release, lock, {'release_manifest_sha256': sha(release_raw),
                          'selected_lock_package_sha256': sha(canonical(lock))}


def inspect_archives(npm, source, root=ROOT):
    release, lock, inputs = release_inputs(root)
    for raw, name in ((npm, 'npm.tgz'), (source, 'source.tar.gz')):
        row = release['archives'][name]
        need(len(raw) == row['bytes'] and sha(raw) == row['sha256'])
    integrity = lock['integrity']; need(type(integrity) is str and integrity.startswith('sha512-'))
    need(base64.b64encode(hashlib.sha512(npm).digest()).decode() == integrity[7:])
    shipped = selected_tar(npm, 'package/', RUNTIME_NAMES | {'pyodide.mjs.map'}, max_member=12_000_000)
    # Actual cached publisher bytes prove every anchored member, not only loader.
    for name, row in reviewed_runtime(release['runtime_members']).items():
        need(len(shipped[name]) == row['bytes'] and sha(shipped[name]) == row['sha256'])
    source_files = selected_tar(source, 'pyodide-'+COMMIT+'/', (*PREFERRED, *LICENSES))
    source_map = parse(shipped['pyodide.mjs.map'])
    need(type(source_map) is dict and set(source_map) == {'version', 'sources', 'sourcesContent', 'mappings', 'names'}
         and type(source_map['version']) is int and source_map['version'] == 3
         and source_map['sources'] == ['../'+p for p in PREFERRED]
         and type(source_map['sourcesContent']) is list and len(source_map['sourcesContent']) == len(PREFERRED))
    for name, text in zip(PREFERRED, source_map['sourcesContent']):
        need(type(text) is str and text.encode('utf-8', 'strict') == source_files[name])
    runtime = release['runtime_members']['pyodide.mjs']
    need(len(shipped['pyodide.mjs']) == runtime['bytes'] and sha(shipped['pyodide.mjs']) == runtime['sha256']
         and shipped['pyodide.mjs'].endswith(b'//# sourceMappingURL=pyodide.mjs.map\n'))
    return release, inputs, shipped['pyodide.mjs.map'], source_files


def prepare_cohort(npm, source, root=ROOT):
    """Only exact already-pinned archive replay creates the scoped cohort."""
    release, inputs, source_map, files = inspect_archives(npm, source, root)
    retained = {source_path(source, '.tar.gz'): source,
                source_path(source_map, '.json'): source_map}
    preferred = []
    for name in PREFERRED:
        raw = files[name]; path = source_path(raw, '.ts'); retained[path] = raw
        preferred.append({'name': name, 'path': path, 'bytes': len(raw), 'sha256': sha(raw),
                          'license': 'MIT' if '/vendor/stackframe/' in name else 'MPL-2.0'})
    licenses = []
    for name, identifier in zip(LICENSES, ('MPL-2.0', 'MIT')):
        raw = files[name]; path = source_path(raw, '.txt'); retained[path] = raw
        licenses.append({'name': name, 'license': identifier, 'path': path,
                         'bytes': len(raw), 'sha256': sha(raw)})
    value = {'profile': PROFILE, 'version': VERSION, 'source_commit': COMMIT,
        'input_sha256': inputs, 'producer_sha256': {p: sha(read(root, p, MAX_JSON)) for p in SOURCES},
        'source_archive': {'path': source_path(source, '.tar.gz'), **release['archives']['source.tar.gz']},
        'source_map': {'path': source_path(source_map, '.json'), 'bytes': len(source_map), 'sha256': sha(source_map)},
        'preferred': preferred, 'licenses': licenses, 'runtime_members': release['runtime_members'],
        'claims': CLAIMS}
    retained[MANIFEST] = canonical(value)+b'\n'; return value, retained


def checked(root=ROOT, npm=None):
    release, _, inputs = release_inputs(root)
    manifest_raw = read(root, MANIFEST, MAX_JSON); m = parse(manifest_raw)
    need(type(m) is dict and set(m) == {'profile','version','source_commit','input_sha256',
        'producer_sha256','source_archive','source_map','preferred','licenses','runtime_members','claims'})
    need(m['profile'] == PROFILE and m['version'] == VERSION and m['source_commit'] == COMMIT
         and m['input_sha256'] == inputs and m['producer_sha256'] == {p: sha(read(root,p,MAX_JSON)) for p in SOURCES}
         and m['runtime_members'] == release['runtime_members'] and m['claims'] == CLAIMS
         and all(type(v) is bool for v in m['claims'].values()))
    source_entry = m['source_archive']; need(source_entry == {
        'path': BASE+'/sources/'+release['archives']['source.tar.gz']['sha256']+'.tar.gz', **release['archives']['source.tar.gz']})
    source = read(root, source_entry['path'], 2_000_000)
    need(len(source) == source_entry['bytes'] and sha(source) == source_entry['sha256'])
    files = selected_tar(source, 'pyodide-'+COMMIT+'/', (*PREFERRED,*LICENSES))
    retained = {source_entry['path']: source}; source_map = m['source_map']
    need(type(source_map) is dict and set(source_map) == {'path','bytes','sha256'}
         and type(source_map['bytes']) is int and 0 < source_map['bytes'] <= MAX_JSON
         and re.fullmatch('[a-f0-9]{64}', source_map['sha256'])
         and source_map['path'] == BASE+'/sources/'+source_map['sha256']+'.json')
    raw_map = read(root, source_map['path'], MAX_JSON)
    need(len(raw_map) == source_map['bytes'] and sha(raw_map) == source_map['sha256'])
    parsed_map = parse(raw_map)
    need(type(parsed_map) is dict and set(parsed_map) == {'version','sources','sourcesContent','mappings','names'}
         and type(parsed_map['version']) is int and parsed_map['version'] == 3
         and parsed_map['sources'] == ['../'+p for p in PREFERRED]
         and parsed_map['sourcesContent'] == [files[p].decode('utf-8','strict') for p in PREFERRED])
    # This is the observed map identity from the exact locked npm archive, not a
    # generic same-license substitute or a claim of rebuilt minification.
    need(sha(raw_map) == '0d97147b5f205398c614021ca450d1d95b87cdf8abd1b9ab4fc86c4169f88c36')
    retained[source_map['path']] = raw_map
    expected_preferred=[]; expected_licenses=[]
    for name in PREFERRED:
        raw=files[name]; path=source_path(raw,'.ts'); need(read(root,path,MAX_JSON)==raw); retained[path]=raw
        expected_preferred.append({'name':name,'path':path,'bytes':len(raw),'sha256':sha(raw),
                                   'license':'MIT' if '/vendor/stackframe/' in name else 'MPL-2.0'})
    for name,identifier in zip(LICENSES,('MPL-2.0','MIT')):
        raw=files[name]; path=source_path(raw,'.txt'); need(read(root,path,MAX_JSON)==raw); retained[path]=raw
        expected_licenses.append({'name':name,'license':identifier,'path':path,'bytes':len(raw),'sha256':sha(raw)})
    need(m['preferred']==expected_preferred and m['licenses']==expected_licenses)
    if npm is not None:
        observed, _, observed_map, observed_files = inspect_archives(npm,source,root)
        need(observed_map==raw_map and observed_files==files and observed==release)
    retained[MANIFEST]=manifest_raw
    need(manifest_raw == read(root,MANIFEST,MAX_JSON))
    return m,retained


def outputs(root=ROOT):
    m, retained = checked(root)
    notices = (b'Selected Pyodide314.0.7 JavaScript source/notice delivery\n'
        b'NOT full WASM corresponding source or global dependency/license clearance.\n'
        b'Ten sourcemap preferred files byte-match the pinned upstream source archive.\n'
        b'Vendored MIT ports and upstream MPL sources remain distinct.\n'
        b'Archive/source identity is observed; compiler output/signatures are not reproduced.\n'
        b'Bundle: PYODIDE-JS-SOURCES.zip; bindings and limits: index.json\n\n')
    for row in m['licenses']:
        label=('=== '+row['name']+' ('+row['license']+') ===\n').encode()
        need(len(label)+len(retained[row['path']])+1<=100000-len(notices))
        notices += label+retained[row['path']]+b'\n'
    need(len(notices)<=100000)
    members = {'NOTICES.txt':notices,'upstream/pyodide-'+COMMIT+'.tar.gz':retained[m['source_archive']['path']],
               'evidence/pyodide.mjs.map':retained[m['source_map']['path']]}
    members.update({row['name']:retained[row['path']] for row in m['preferred']})
    index = {'profile':PROFILE,'pyodide_version':VERSION,'source_commit':COMMIT,
        'runtime_members':m['runtime_members'],'cohort_manifest_sha256':sha(retained[MANIFEST]),
        'source_archive':m['source_archive'],'claims':CLAIMS,
        'members':[{'path':name,'bytes':len(raw),'sha256':sha(raw)} for name,raw in sorted(members.items())]}
    members['index.json']=canonical(index)+b'\n'
    need(sum(len(v) for v in members.values())<=MAX_OUTPUT)
    stream=io.BytesIO()
    with zipfile.ZipFile(stream,'w',compression=zipfile.ZIP_STORED,allowZip64=False) as archive:
        for name,raw in sorted(members.items()):
            safe_relative(name); info=zipfile.ZipInfo(name,(1980,1,1,0,0,0));info.create_system=3;info.external_attr=0o100644<<16
            archive.writestr(info,raw)
    bundle=stream.getvalue();need(len(bundle)<=MAX_OUTPUT)
    return {'PYODIDE-JS-SOURCES.zip':bundle,'NOTICES.txt':notices,'index.json':members['index.json']}


def export(destination, root=ROOT):
    expected=outputs(root); target=Path(destination).absolute(); parent=target.parent
    need(parent.resolve()==parent and parent.is_dir() and not parent.is_symlink())
    pi=parent.stat();need(pi.st_uid==os.getuid() and not pi.st_mode&0o022)
    existing=target.exists() or target.is_symlink()
    if existing:
        need(not target.is_symlink() and target.is_dir() and set(p.name for p in target.iterdir())==set(OUTPUT_NAMES))
        if all(read(target,n,MAX_OUTPUT)==v for n,v in expected.items()):return expected
    stage=parent/('.pyodide-js-stage-'+secrets.token_hex(12));backup=parent/('.pyodide-js-old-'+secrets.token_hex(12));stage.mkdir(mode=0o755);moved=False;committed=False
    try:
        for name,raw in expected.items():
            fd=os.open(stage/name,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o644)
            with os.fdopen(fd,'wb') as stream:stream.write(raw);stream.flush();os.fsync(stream.fileno())
        need(expected==outputs(root))
        if existing:os.rename(target,backup);moved=True
        os.rename(stage,target);committed=True
        if moved:shutil.rmtree(backup)
    except BaseException:
        if moved or committed:raise OutputUncertain() from None
        raise
    finally:
        if stage.exists():
            try:shutil.rmtree(stage)
            except BaseException:
                if moved or committed:raise OutputUncertain() from None
                raise SourceError('Runtime source staging cleanup unavailable') from None
    return expected


def check_built(directory, root=ROOT):
    expected=outputs(root)
    m,_=checked(root)
    for relative,names in [('runtime-js-sources',set(OUTPUT_NAMES)),('device/runtime-'+VERSION,set(m['runtime_members']))]:
        selected=Path(directory).absolute()/relative
        need(selected.resolve()==selected and selected.is_dir() and not selected.is_symlink()
             and {p.name for p in selected.iterdir()}==names)
    for name,row in m['runtime_members'].items():
        raw=read(directory,'device/runtime-'+VERSION+'/'+name,12_000_000)
        need(len(raw)==row['bytes'] and sha(raw)==row['sha256'])
    for name,raw in expected.items():need(read(directory,'runtime-js-sources/'+name,MAX_OUTPUT)==raw)
    return {'pass':True,'profile':PROFILE,'preferred_source_files':len(PREFERRED),'vendor_source_files':2,
            'verbatim_license_texts':2,'selected_runtime_members':5,'delivered_artifacts':3,
            'bundle_sha256':sha(expected['PYODIDE-JS-SOURCES.zip']),**CLAIMS}
