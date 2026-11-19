"""Finite offline C2PA wheel/source/notice observations; no package execution."""
import base64
import csv
from datetime import datetime, timezone
import email
import gzip
import hashlib
import io
import json
from pathlib import Path
import re
import struct
import tarfile
from urllib.parse import urlsplit
import zipfile

from protocol.evidence import read_evidence

ROOT = Path(__file__).resolve().parents[1]
PROFILE = 'c2pa-selected-artifact-notice-observations/1.0.0'
MANIFEST = 'sbom/c2pa/manifest.json'
STORE = 'sbom/c2pa/sources/'
MAX_ARCHIVE = 64 * 1024**2
MAX_MEMBER = 40 * 1024**2
MAX_EXPANDED = 160 * 1024**2
MAX_FILES = 10000
MAX_TEXT = 4 * 1024**2
INPUTS = ('eval/c2pa-inspection.lock', 'eval/dependencies/c2pa-inspection.json', 'tools/manifest_inspection.py')
FILES = ('tools/c2pa_cohort.py', 'scripts/verify-c2pa-cohort.py', 'tests/test_c2pa_cohort.py',
         'docs/c2pa-cohort-plan.md', 'docs/c2pa-cohort-review.md', 'sbom/c2pa/.gitattributes', 'protocol/evidence.py')
PACKAGES = ('c2pa-python', 'certifi', 'cffi', 'charset-normalizer', 'cryptography', 'idna', 'pycparser', 'requests', 'toml', 'urllib3')
VERSIONS = ('0.38.0', '2026.7.22', '2.1.1', '3.5.2', '50.0.2', '3.20', '3.11', '2.32.5', '0.10.2', '2.8.0')
COMMON = ('certifi-2026.7.22-py3-none-any.whl', 'idna-3.20-py3-none-any.whl',
          'pycparser-3.11-py3-none-any.whl', 'requests-2.32.5-py3-none-any.whl',
          'toml-0.10.2-py2.py3-none-any.whl', 'urllib3-2.8.0-py3-none-any.whl')
SELECTION = {
 'darwin-arm64-cp312': sorted((*COMMON, 'c2pa_python-0.38.0-py3-none-macosx_11_0_arm64.whl',
   'cffi-2.1.1-cp312-cp312-macosx_11_0_arm64.whl',
   'charset_normalizer-3.5.2-cp312-cp312-macosx_10_13_universal2.whl',
   'cryptography-50.0.2-cp311-abi3-macosx_11_0_arm64.whl')),
 'linux-x86_64-cp313': sorted((*COMMON, 'c2pa_python-0.38.0-py3-none-manylinux_2_28_x86_64.whl',
   'cffi-2.1.1-cp313-cp313-manylinux2014_x86_64.manylinux_2_17_x86_64.whl',
   'charset_normalizer-3.5.2-cp313-cp313-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl',
   'cryptography-50.0.2-cp311-abi3-manylinux_2_34_x86_64.whl'))}
COMMIT = 'e7cc666c3409bdaf4cea8e49046dfbf8290dff89'
RAW_FILES = ('Cargo.toml', 'LICENSE-MIT', 'LICENSE-APACHE', 'c2pa_c_ffi/Cargo.toml', 'c2pa_c_ffi/README.md', 'sdk/Cargo.toml')
RELEASES = {'darwin-arm64': ('c2pa-v0.91.0-aarch64-apple-darwin.zip', 'lib/libc2pa_c.dylib'),
            'linux-x86_64': ('c2pa-v0.91.0-x86_64-unknown-linux-gnu.zip', 'lib/libc2pa_c.so')}
DISCLAIMERS = {'permission_cleared': False, 'release_approved': False,
               'source_build_reproduced': False, 'publisher_signature_verified': False,
               'complete_native_dependency_graph': False}


def need(condition):
    if not condition: raise ValueError('C2PA cohort evidence refused.')


def sha(raw): return hashlib.sha256(raw).hexdigest()


def read(path, limit=MAX_ARCHIVE):
    path = Path(path)
    need(not any(p.is_symlink() for p in [path, *path.parents]) and path.is_file())
    with path.open('rb') as handle: raw = handle.read(limit+1)
    need(len(raw) <= limit)
    return raw


def strict(raw):
    def pairs(rows):
        result = {}
        for key,value in rows:
            need(key not in result); result[key] = value
        return result
    return json.loads(raw, object_pairs_hook=pairs,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError('Nonfinite evidence.')))


def safe(name):
    need(type(name) is str and 0 < len(name) <= 512 and not name.startswith('/')
         and '\\' not in name and ':' not in name and all(ord(c) >= 32 and ord(c) != 127 for c in name)
         and all(x not in ('', '.', '..') for x in name.rstrip('/').split('/')))


class ExpandedReader:
    """Cap bytes consumed before tarfile processes extended/PAX headers."""
    def __init__(self, handle): self.handle = handle; self.consumed = 0
    def read(self, size=-1):
        remaining = MAX_EXPANDED-self.consumed
        requested = remaining+1 if size < 0 else min(size,remaining+1)
        data = self.handle.read(requested); self.consumed += len(data)
        need(self.consumed <= MAX_EXPANDED)
        return data


def zip_directory_preflight(raw):
    """Bound classic single-disk ZIP metadata before ZipFile allocates ZipInfo."""
    need(len(raw) >= 22 and raw[-22:-18] == b'PK\x05\x06')
    end = len(raw) - 22
    signature, disk, directory_disk, disk_count, count, size, start, comment = struct.unpack_from('<4s4H2IH', raw, end)
    need(signature == b'PK\x05\x06' and disk == directory_disk == comment == 0)
    need(0 < count == disk_count <= MAX_FILES and count != 0xffff)
    need(size != 0xffffffff and start != 0xffffffff and 0 < size <= 8 * 1024**2 and start + size == end)
    # ZIP64 end records/locators, split archives, archive/entry comments, trailing
    # data and self-extracting prefixes are outside this finite classic profile.
    pos = start; seen = set(); offsets = set(); ranges = []; expanded = 0

    def extra_fields(data):
        offset = 0; tags = set()
        while offset < len(data):
            need(offset + 4 <= len(data))
            tag, length = struct.unpack_from('<HH', data, offset)
            need(tag != 1 and tag not in tags and offset + 4 + length <= len(data))
            tags.add(tag); offset += 4 + length
        need(offset == len(data))

    for _ in range(count):
        need(pos + 46 <= end)
        fields = struct.unpack_from('<4s6H3I5H2I', raw, pos)
        sig, _, _, flags, method, _, _, _, compressed, unpacked, namesize, extrasize, commentsize, member_disk, _, _, local = fields
        need(sig == b'PK\x01\x02' and not flags & 1 and member_disk == 0)
        need(commentsize == 0 and 0 < namesize <= 2048 and extrasize <= 4096)
        finish = pos + 46 + namesize + extrasize
        need(finish <= end and compressed != 0xffffffff and unpacked != 0xffffffff and local != 0xffffffff)
        need(compressed <= MAX_ARCHIVE and unpacked <= MAX_MEMBER)
        expanded += unpacked; need(expanded <= MAX_EXPANDED)
        name_raw = raw[pos + 46:pos + 46 + namesize]
        name = name_raw.decode('utf-8' if flags & 0x800 else 'cp437', 'strict'); safe(name)
        need(name not in seen and local not in offsets); seen.add(name); offsets.add(local)
        extra_fields(raw[pos + 46 + namesize:finish])
        need(0 <= local and local + 30 <= start)
        header = struct.unpack_from('<4s5H3I2H', raw, local)
        need(header[0] == b'PK\x03\x04' and header[2] == flags and header[3] == method)
        need(header[7] != 0xffffffff and header[8] != 0xffffffff)
        local_name, local_extra = header[-2:]
        need(local_name == namesize and local_extra <= 4096)
        payload = local + 30 + local_name + local_extra
        need(payload + compressed <= start and raw[local + 30:local + 30 + local_name] == name_raw)
        extra_fields(raw[local + 30 + local_name:payload])
        ranges.append((local, payload + compressed)); pos = finish
    need(pos == end and min(offsets) == 0)
    ranges.sort(); need(all(a[1] <= b[0] for a, b in zip(ranges, ranges[1:])))


def archive(raw, kind):
    need(type(raw) is bytes and 0 < len(raw) <= MAX_ARCHIVE)
    rows = {}; seen = set(); total = 0
    if kind == 'zip':
        zip_directory_preflight(raw)
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            for item in z.infolist():
                name = item.filename; safe(item.orig_filename); need(item.orig_filename == name); safe(name); need(name not in seen and len(seen) < MAX_FILES); seen.add(name)
                need(not item.flag_bits & 1 and (item.external_attr >> 16) & 0o170000 in (0, 0o040000, 0o100000))
                total += item.file_size
                need(0 <= item.file_size <= MAX_MEMBER and total <= MAX_EXPANDED)
                if item.is_dir(): need(item.file_size == 0); continue
                with z.open(item) as f: data = f.read(MAX_MEMBER+1)
                need(len(data) == item.file_size and len(data) <= MAX_MEMBER); rows[name] = data
    else:
        need(kind == 'tar-gzip')
        with gzip.GzipFile(fileobj=io.BytesIO(raw)) as expanded, \
                tarfile.open(fileobj=ExpandedReader(expanded), mode='r|') as t:
            for item in t:
                safe(item.name); need(item.name not in seen and len(seen) < MAX_FILES); seen.add(item.name)
                need(item.isdir() or item.isfile())
                total += item.size; need(0 <= item.size <= MAX_MEMBER and total <= MAX_EXPANDED)
                if item.isdir(): need(item.size == 0); continue
                with t.extractfile(item) as f: data = f.read(MAX_MEMBER+1)
                need(len(data) == item.size and len(data) <= MAX_MEMBER); rows[item.name] = data
    return rows


def canonical(name): return re.sub('[-_.]+', '-', name).lower()


def locked(root):
    raw = read(root/INPUTS[0], 100000).decode('ascii')
    result = {}; name = None; binary_policy = False
    for line in raw.splitlines():
        if not line.strip() or line.startswith('#'): continue
        if line == '--only-binary=:all:':
            need(not binary_policy and name is None); binary_policy = True; continue
        match = re.fullmatch(r'([a-z0-9-]+)==([0-9.]+) \\', line)
        if match:
            name, version = match.groups(); need(name not in result)
            result[name] = {'version':version, 'hashes':[]}; continue
        match = re.fullmatch(r'    --hash=sha256:([a-f0-9]{64})(?: \\)?', line)
        need(match is not None and name is not None)
        result[name]['hashes'].append(match.group(1))
    need(binary_policy and set(result) == set(PACKAGES) and all(result[n]['version'] == v and result[n]['hashes'] for n,v in zip(PACKAGES,VERSIONS)))
    return result


def notice(name):
    parts = name.lower().split('/')
    return bool(re.match(r'^(?:licen[cs]e|copying|notice|copyright)(?:[._-]|$)', parts[-1]) or 'licenses' in parts[:-1])


def entry(raw): return {'sha256':sha(raw), 'bytes':len(raw)}


def blob(raw, blobs):
    raw.decode('utf-8', 'strict'); need(0 < len(raw) <= MAX_TEXT)
    name = STORE+sha(raw)+'.txt'; blobs[name] = raw
    return {'path':name, **entry(raw)}


def retained(members, names, blobs):
    return [{'member':n, **blob(members[n], blobs)} for n in sorted(names)]


def records(members, record):
    expected = {}
    for row in csv.reader(io.StringIO(members[record].decode('utf-8', 'strict'), newline='')):
        need(len(row) == 3); name,h,size = row; safe(name); need(name not in expected)
        if name == record: need(h == size == ''); expected[name] = None; continue
        need(h.startswith('sha256=') and re.fullmatch('[A-Za-z0-9_-]{43}', h[7:]) is not None)
        need(re.fullmatch('0|[1-9][0-9]{0,8}', size) is not None)
        expected[name] = {'sha256':base64.urlsafe_b64decode(h[7:]+'=').hex(), 'bytes':int(size)}
    need(set(expected) == set(members))
    need(all(info is None or info == entry(members[n]) for n,info in expected.items()))
    return expected


def distribution(members, package, version):
    names = [n for n in members if n.endswith('.dist-info/METADATA')]; need(len(names) == 1)
    prefix = names[0][:-len('METADATA')]
    need(all(n in members for n in (prefix+'METADATA', prefix+'WHEEL', prefix+'RECORD')))
    meta = email.message_from_bytes(members[names[0]])
    need(len(meta.get_all('Name', [])) == len(meta.get_all('Version', [])) == 1)
    need(canonical(meta['Name']) == package and meta['Version'] == version)
    w = email.message_from_bytes(members[prefix+'WHEEL'])
    need(w['Wheel-Version'] == '1.0')
    records(members, prefix+'RECORD')
    return {'name':canonical(meta['Name']), 'version':meta['Version'],
            'license_declared':meta.get('License-Expression') or meta.get('License'),
            'license_file_declarations':meta.get_all('License-File', []),
            'requires_dist':meta.get_all('Requires-Dist', []), 'wheel_tags':w.get_all('Tag', [])}, prefix


def file_record(metadata, filename, version, package):
    need(canonical(metadata['info']['name']) == package and metadata['info']['version'] == version)
    rows = [r for r in metadata['urls'] if r['filename'] == filename]; need(len(rows) == 1)
    row = rows[0]; u = urlsplit(row['url'])
    need(u.scheme == 'https' and u.netloc == 'files.pythonhosted.org' and u.path.endswith('/'+filename) and not u.query and not u.fragment)
    need(row['yanked'] is False and row['packagetype'] in ('bdist_wheel', 'sdist'))
    need(re.fullmatch('[a-f0-9]{64}', row['digests']['sha256']) and type(row['size']) is int and 0 < row['size'] <= MAX_ARCHIVE)
    return {'filename':filename, 'url':row['url'], 'sha256':row['digests']['sha256'], 'bytes':row['size'], 'kind':row['packagetype']}


def observe(cache, root=ROOT):
    """Inspect explicit private cached upstream bytes; no downloads or imports."""
    cache, root = Path(cache), Path(root)
    pins = strict(read(root/INPUTS[1], 20000)); lock = locked(root); blobs = {}
    need(set(pins['profiles']) == set(RELEASES))
    wheel_names = sorted(set(sum(SELECTION.values(), [])))
    packages = []; wheels = []; source_members = {}
    for name in PACKAGES:
        version = lock[name]['version']; metadata_name = f'{name}-{version}.metadata.json'
        raw_meta = read(cache/metadata_name, MAX_TEXT); meta = strict(raw_meta)
        source_rows = [r for r in meta['urls'] if r['packagetype'] == 'sdist']; need(len(source_rows) == 1)
        source = file_record(meta, source_rows[0]['filename'], version, name)
        raw_source = read(cache/source['filename']); need(entry(raw_source) == {k:source[k] for k in ('sha256','bytes')})
        members = archive(raw_source, 'tar-gzip'); roots = {n.split('/')[0] for n in members}; need(len(roots) == 1)
        prefix = next(iter(roots))+'/'
        source_members[name] = (members, prefix)
        source_meta = [n for n in members if n == prefix+'PKG-INFO']; need(len(source_meta) == 1)
        source_decl = email.message_from_bytes(members[source_meta[0]])
        need(canonical(source_decl['Name']) == name and source_decl['Version'] == version)
        source.update(notices=retained(members, [n for n in members if notice(n)], blobs),
                      metadata=retained(members,source_meta,blobs)[0],
                      members={n:entry(data) for n,data in sorted(members.items())})
        need(source['notices'])
        packages.append({'name':name, 'version':version, 'pypi_metadata':{'filename':metadata_name,
                         'url':f'https://pypi.org/pypi/{name}/{version}/json', **blob(raw_meta, blobs)}, 'source':source})
        for filename in wheel_names:
            if canonical(filename.split('-')[0]) != name: continue
            artifact = file_record(meta, filename, version, name)
            need(artifact['kind'] == 'bdist_wheel' and artifact['sha256'] in lock[name]['hashes'])
            raw = read(cache/filename); need(entry(raw) == {k:artifact[k] for k in ('sha256','bytes')})
            contents = archive(raw, 'zip'); declaration, info_prefix = distribution(contents, name, version)
            py_sources = []
            for member,data in sorted(contents.items()):
                if not member.endswith('.py') or '.dist-info/' in member: continue
                choices = [prefix+member, prefix+'src/'+member, prefix+'lib/'+member]
                matches = [n for n in choices if n in members and members[n] == data]
                py_sources.append({'member':member, **entry(data), 'source_members':matches,
                                   'relationship':'exact_bytes_at_selected_paths' if matches else 'not_matched_at_selected_paths'})
            native = [{'member':n, **entry(data)} for n,data in sorted(contents.items())
                      if re.search(r'\.(?:so|dylib|dll|pyd)$', n) or data.startswith((b'\x7fELF',b'MZ',b'\xcf\xfa\xed\xfe',b'\xfe\xed\xfa\xcf'))]
            selected = [n for n in contents if notice(n) or n in [info_prefix+x for x in ('METADATA','WHEEL','RECORD')]]
            artifact.update(package=name, profiles=sorted(p for p,ns in SELECTION.items() if filename in ns),
                            declaration=declaration, retained=retained(contents, selected, blobs),
                            members={n:entry(data) for n,data in sorted(contents.items())},
                            native_members=native, python_source_relationships=py_sources)
            wheels.append(artifact)
    wheels.sort(key=lambda x:x['filename']); need(len(wheels) == 14)
    upstream_raw = read(cache/'c2pa-rs-0.91.0-release.json', MAX_TEXT); release = strict(upstream_raw)
    need(release['tag_name'] == 'c2pa-v0.91.0' and release['target_commitish'] == COMMIT)
    upstream = {'source_commit':COMMIT, 'release_metadata':{'filename':'c2pa-rs-0.91.0-release.json',
                'url':'https://api.github.com/repos/contentauth/c2pa-rs/releases/tags/c2pa-v0.91.0', **blob(upstream_raw, blobs)},
                'documents':[], 'native_matches':[]}
    for name in RAW_FILES:
        filename = 'c2pa-rs-'+name.replace('/','--'); raw = read(cache/filename, MAX_TEXT)
        upstream['documents'].append({'filename':filename, 'upstream_path':name,
            'url':f'https://raw.githubusercontent.com/contentauth/c2pa-rs/{COMMIT}/{name}', **blob(raw, blobs)})
    for profile,(filename,member) in RELEASES.items():
        assets = [a for a in release['assets'] if a['name'] == filename]; need(len(assets) == 1)
        asset = assets[0]; raw = read(cache/filename); need(len(raw) == asset['size'])
        if asset.get('digest'): need(asset['digest'] == 'sha256:'+sha(raw))
        members = archive(raw, 'zip'); native = members[member]
        pin = pins['profiles'][profile]; wheel = next(w for w in wheels if w['filename'] == pin['wheel'])
        need(wheel['sha256'] == pin['wheel_sha256'])
        need(wheel['members'][pin['native']] == entry(native) and sha(native) == pin['sources'][pin['native']])
        for n,h in pin['sources'].items(): need(wheel['members'][n]['sha256'] == h)
        source, prefix = source_members['c2pa-python']
        wrapper_matches = []
        for n,h in pin['sources'].items():
            if n == pin['native']: continue
            source_name = prefix+'src/'+n
            need(source_name in source and sha(source[source_name]) == h)
            wrapper_matches.append({'wheel_member':n, 'source_member':source_name, 'sha256':h})
        upstream['native_matches'].append({'profile':profile, 'filename':filename,
            'url':asset['browser_download_url'], **entry(raw), 'release_member':member,
            'wheel':pin['wheel'], 'wheel_member':pin['native'], 'native':entry(native),
            'wrapper_matches':wrapper_matches, 'relationship':'exact_wheel_and_release_member_bytes',
            'binary_executed':False})
    return {'profile':PROFILE, 'status':'bounded_notice_and_artifact_observations',
            'captured_at':datetime.now(timezone.utc).isoformat(), 'sources':{p:sha(read(root/p,MAX_TEXT)) for p in FILES},
            'inputs':{p:sha(read(root/p,MAX_TEXT)) for p in INPUTS},
            'selected_profiles':SELECTION, 'packages':packages, 'wheels':wheels,
            'sdk_upstream':upstream, **DISCLAIMERS}, blobs


def verify(root=ROOT, cache_dir=None, require_clearance=False):
    root = Path(root); value = read_evidence(root/MANIFEST, limit=8*1024**2)
    need(set(value) == {'profile','status','captured_at','sources','inputs','selected_profiles','packages','wheels','sdk_upstream',*DISCLAIMERS})
    need(value['profile'] == PROFILE and value['status'] == 'bounded_notice_and_artifact_observations')
    stamp = datetime.fromisoformat(value['captured_at']); need(stamp.tzinfo is not None and stamp <= datetime.now(timezone.utc))
    need(all(value[k] is False for k in DISCLAIMERS))
    need(value['sources'] == {p:sha(read(root/p,MAX_TEXT)) for p in FILES})
    need(value['inputs'] == {p:sha(read(root/p,MAX_TEXT)) for p in INPUTS})
    need(value['selected_profiles'] == SELECTION)
    lock = locked(root); pins = strict(read(root/INPUTS[1],20000)); texts = {}
    def text(row):
        need(set(row) >= {'path','sha256','bytes'} and row['path'] == STORE+row['sha256']+'.txt')
        need(re.fullmatch('[a-f0-9]{64}',row['sha256']) and type(row['bytes']) is int and 0 < row['bytes'] <= MAX_TEXT)
        raw = read(root/row['path'],MAX_TEXT); raw.decode('utf-8','strict')
        need(entry(raw) == {k:row[k] for k in ('sha256','bytes')}); texts[row['path']] = raw
        return raw
    need(type(value['packages']) is list and [r['name'] for r in value['packages']] == list(PACKAGES))
    metas = {}; package_map = {}
    for package in value['packages']:
        need(set(package) == {'name','version','pypi_metadata','source'})
        name = package['name']; version = lock[name]['version']; need(package['version'] == version)
        meta_row = package['pypi_metadata']; need(set(meta_row)=={'filename','url','path','sha256','bytes'}); need(meta_row['filename'] == f'{name}-{version}.metadata.json')
        need(meta_row['url'] == f'https://pypi.org/pypi/{name}/{version}/json')
        meta = strict(text(meta_row)); metas[name] = meta; package_map[name] = package
        source = package['source']; need(source['kind'] == 'sdist')
        need({k:source[k] for k in ('filename','url','sha256','bytes','kind')} == file_record(meta,source['filename'],version,name))
        need(set(source) == {'filename','url','sha256','bytes','kind','notices','metadata','members'})
        source_inventory = source['members']; need(type(source_inventory) is dict and 1 <= len(source_inventory) <= MAX_FILES)
        for n,info in source_inventory.items():
            safe(n); need(set(info) == {'sha256','bytes'} and re.fullmatch('[a-f0-9]{64}',info['sha256']))
            need(type(info['bytes']) is int and 0 <= info['bytes'] <= MAX_MEMBER)
        need(sum(info['bytes'] for info in source_inventory.values()) <= MAX_EXPANDED)
        source_roots = {n.split('/')[0] for n in source_inventory}; need(len(source_roots) == 1)
        prefix = next(iter(source_roots))+'/'
        sm = source['metadata']; need(set(sm)=={'member','path','sha256','bytes'}); need(sm['member'] == prefix+'PKG-INFO' and source_inventory[sm['member']] == {k:sm[k] for k in ('sha256','bytes')})
        sd = email.message_from_bytes(text(sm)); need(canonical(sd['Name']) == name and sd['Version'] == version)
        need(type(source['notices']) is list and 1 <= len(source['notices']) <= 128)
        need([r['member'] for r in source['notices']] == sorted(n for n in source_inventory if notice(n)))
        seen = set()
        for row in source['notices']:
            need(set(row)=={'member','path','sha256','bytes'}); safe(row['member']); need(row['member'] not in seen and notice(row['member'])); seen.add(row['member']); text(row)
            need(source_inventory[row['member']] == {k:row[k] for k in ('sha256','bytes')})
    wheel_names = sorted(set(sum(SELECTION.values(), [])))
    need(type(value['wheels']) is list and [r['filename'] for r in value['wheels']] == wheel_names)
    for wheel in value['wheels']:
        name = wheel['package']; need(name in lock)
        need(set(wheel) == {'filename','url','sha256','bytes','kind','package','profiles','declaration','retained','members','native_members','python_source_relationships'})
        need(wheel['profiles'] == sorted(p for p,ns in SELECTION.items() if wheel['filename'] in ns))
        need({k:wheel[k] for k in ('filename','url','sha256','bytes','kind')} == file_record(metas[name],wheel['filename'],lock[name]['version'],name))
        need(wheel['sha256'] in lock[name]['hashes'])
        members = wheel['members']; need(type(members) is dict and 1 <= len(members) <= MAX_FILES)
        for n,row in members.items():
            safe(n); need(set(row) == {'sha256','bytes'} and re.fullmatch('[a-f0-9]{64}',row['sha256']))
            need(type(row['bytes']) is int and 0 <= row['bytes'] <= MAX_MEMBER)
        need(sum(row['bytes'] for row in members.values()) <= MAX_EXPANDED)
        retained_bytes = {}; names = set()
        for row in wheel['retained']:
            need(set(row)=={'member','path','sha256','bytes'}); n = row['member']; need(n in members and n not in names); names.add(n)
            raw = text(row); need(entry(raw) == members[n]); retained_bytes[n] = raw
        metadata_names = [n for n in members if n.endswith('.dist-info/METADATA')]; need(len(metadata_names) == 1)
        prefix = metadata_names[0][:-len('METADATA')]
        expected_names = {n for n in members if notice(n) or n in [prefix+x for x in ('METADATA','WHEEL','RECORD')]}
        need(names == expected_names)
        # Reconstruct exact RECORD expectations without pretending archived bytes
        # were replayed. Retained metadata/notice bytes are checked above.
        expected = {}
        for row in csv.reader(io.StringIO(retained_bytes[prefix+'RECORD'].decode(),newline='')):
            need(len(row)==3); n,h,size=row; safe(n); need(n not in expected)
            if n == prefix+'RECORD': need(h == size == ''); expected[n] = members[n]; continue
            need(h.startswith('sha256=') and re.fullmatch('[A-Za-z0-9_-]{43}',h[7:]) and re.fullmatch('0|[1-9][0-9]{0,8}',size))
            expected[n] = {'sha256':base64.urlsafe_b64decode(h[7:]+'=').hex(),'bytes':int(size)}
        need(expected == members)
        meta = email.message_from_bytes(retained_bytes[metadata_names[0]])
        wh = email.message_from_bytes(retained_bytes[prefix+'WHEEL'])
        need(canonical(meta['Name']) == name and meta['Version'] == lock[name]['version'] and wh['Wheel-Version']=='1.0')
        declaration = {'name':canonical(meta['Name']),'version':meta['Version'], 'license_declared':meta.get('License-Expression') or meta.get('License'),
                       'license_file_declarations':meta.get_all('License-File',[]),'requires_dist':meta.get_all('Requires-Dist',[]),'wheel_tags':wh.get_all('Tag',[])}
        need(wheel['declaration'] == declaration)
        native_names = [r['member'] for r in wheel['native_members']]
        need(native_names == sorted(n for n in members if re.search(r'\.(?:so|dylib|dll|pyd)$',n)))
        for row in wheel['native_members']:
            need(set(row)=={'member','sha256','bytes'}); need(row['member'] in members and {k:row[k] for k in ('sha256','bytes')} == members[row['member']])
        py_names = {n for n in members if n.endswith('.py') and '.dist-info/' not in n}
        need([r['member'] for r in wheel['python_source_relationships']] == sorted(py_names))
        for row in wheel['python_source_relationships']:
            need(set(row) == {'member','sha256','bytes','source_members','relationship'})
            need({k:row[k] for k in ('sha256','bytes')} == members[row['member']])
            need(type(row['source_members']) is list and len(row['source_members']) <= 3)
            source_inventory = package_map[name]['source']['members']
            source_prefix = next(iter(source_inventory)).split('/')[0]+'/'
            choices = [source_prefix+row['member'], source_prefix+'src/'+row['member'], source_prefix+'lib/'+row['member']]
            need(row['source_members'] == [n for n in choices if source_inventory.get(n) == members[row['member']]])
            for n in row['source_members']: safe(n)
            need(row['relationship'] == ('exact_bytes_at_selected_paths' if row['source_members'] else 'not_matched_at_selected_paths'))
    up = value['sdk_upstream']; need(set(up)=={'source_commit','release_metadata','documents','native_matches'} and up['source_commit']==COMMIT)
    rm=up['release_metadata']; need(set(rm)=={'filename','url','path','sha256','bytes'})
    need(rm['filename']=='c2pa-rs-0.91.0-release.json' and rm['url']=='https://api.github.com/repos/contentauth/c2pa-rs/releases/tags/c2pa-v0.91.0')
    release = strict(text(rm)); need(release['target_commitish']==COMMIT and release['tag_name']=='c2pa-v0.91.0')
    need([r['upstream_path'] for r in up['documents']] == list(RAW_FILES))
    for row in up['documents']:
        need(set(row)=={'filename','upstream_path','url','path','sha256','bytes'})
        need(row['filename']=='c2pa-rs-'+row['upstream_path'].replace('/','--'))
        need(row['url']==f'https://raw.githubusercontent.com/contentauth/c2pa-rs/{COMMIT}/'+row['upstream_path']); text(row)
    need([r['profile'] for r in up['native_matches']] == list(RELEASES))
    for row in up['native_matches']:
        need(set(row)=={'profile','filename','url','sha256','bytes','release_member','wheel','wheel_member','native','wrapper_matches','relationship','binary_executed'})
        profile = row['profile']; filename,member = RELEASES[profile]; pin = pins['profiles'][profile]
        need(row['filename']==filename and row['release_member']==member and row['wheel']==pin['wheel'] and row['wheel_member']==pin['native'])
        need(row['binary_executed'] is False and row['relationship']=='exact_wheel_and_release_member_bytes')
        assets=[a for a in release['assets'] if a['name']==filename]; need(len(assets)==1)
        need(row['url']==assets[0]['browser_download_url']=='https://github.com/contentauth/c2pa-rs/releases/download/c2pa-v0.91.0/'+filename and row['bytes']==assets[0]['size'])
        need(not assets[0].get('digest') or assets[0]['digest']=='sha256:'+row['sha256'])
        wheel = next(w for w in value['wheels'] if w['filename']==pin['wheel'])
        need(wheel['sha256']==pin['wheel_sha256'] and row['native']==wheel['members'][pin['native']])
        need(set(m['wheel_member'] for m in row['wrapper_matches'])==set(pin['sources'])-{pin['native']})
        for n,h in pin['sources'].items(): need(wheel['members'][n]['sha256']==h)
        for match in row['wrapper_matches']:
            need(set(match)=={'wheel_member','source_member','sha256'})
            need(match['sha256']==pin['sources'][match['wheel_member']]); safe(match['source_member'])
            py = next(p for p in wheel['python_source_relationships'] if p['member']==match['wheel_member'])
            need(match['source_member'] in py['source_members'])
    actual = {str(p.relative_to(root)) for p in (root/STORE).iterdir()}; need(actual==set(texts))
    if cache_dir is not None:
        replay, replay_blobs = observe(cache_dir,root)
        replay['captured_at'] = value['captured_at']
        need(replay==value and replay_blobs==texts)
    need(not require_clearance)
    return {'profile':PROFILE,'pass':True,'packages':len(PACKAGES),'distinct_wheels':len(wheel_names),
            'selected_profile_slots':sum(len(v) for v in SELECTION.values()),'retained_texts':len(texts),
            'native_release_matches':len(RELEASES),'artifact_bytes_replayed':cache_dir is not None,
            'source_bytes_replayed':cache_dir is not None,'packages_executed':False, **DISCLAIMERS}
