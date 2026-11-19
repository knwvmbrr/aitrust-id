"""Finite offline NLI notice/source evidence, never imports model packages."""
import ast
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import re
import stat
import struct
import zipfile

ROOT = Path(__file__).resolve().parents[1]
PROFILE = 'nli-model-runtime-obligations/v1'
STORE = 'sbom/reviews/nli'
MANIFEST = STORE + '/manifest.json'
BUNDLE = STORE + '/THIRD-PARTY-NOTICES.txt'
REVISION = 'a150876415327c80daeff35ca6f68f5ed8cf5c24'
BASE_REVISION = '4b419818330868dff6a60ad3e6b1c730f8b8c0c6'
NATIVE = {'hf-xet', 'ml_dtypes', 'numpy', 'onnx', 'onnxruntime', 'protobuf', 'PyYAML', 'tokenizers'}
INPUTS = ('research/nli/assets.json', 'research/nli/backend.py', 'research/nli/notices.json',
          'research/nli/requirements-mac.lock', 'research/nli/requirements-linux.lock',
          'research/nli/wheel-provenance-mac.json', 'research/nli/wheel-provenance-linux.json')
OWN = ('tools/nli_license_cohort.py', 'scripts/verify-nli-license-cohort.py',
       'tests/test_nli_license_cohort.py', 'docs/nli-license-cohort.md', 'docs/nli-license-cohort-plan.md')
UPSTREAM = {
 'model-tree.json': ('https://huggingface.co/api/models/cross-encoder/nli-deberta-v3-xsmall/tree/'+REVISION+'?recursive=true&expand=false', 'c0286c0d0fbfae271bacf1c5f5fbe56a05aac466c761568750a119dc91dcbbc8', 4600),
 'base-tree.json': ('https://huggingface.co/api/models/microsoft/deberta-v3-xsmall/tree/'+BASE_REVISION+'?recursive=true&expand=false', '0bdc926f9d4724a2c5205cfb685aabd70733d2ee9889293251a79180c28dcc63', 1708),
 'base-README.md': ('https://huggingface.co/microsoft/deberta-v3-xsmall/raw/'+BASE_REVISION+'/README.md', '235a48b97b65c66b730c36444441ebfb8d5360c0e9100753b83825f90a622656', 3727),
 'deberta-LICENSE.txt': ('https://raw.githubusercontent.com/microsoft/DeBERTa/4d7fe0bd4fb3c7d4f4005a7cafabde9800372098/LICENSE', 'c2cfccb812fe482101a8f04597dfc5a9991a6b2748266c47ac91b6a5aae15383', 1141),
 'tokenizers-LICENSE.txt': ('https://raw.githubusercontent.com/huggingface/tokenizers/301277072263fb3830eb66eec7e47adadf76f1dc/LICENSE', 'c71d239df91726fc519c6eb72d318ec65820627232b2f796219e87dcf35d0ab4', 11357),
 'tokenizers-python-Cargo.toml': ('https://raw.githubusercontent.com/huggingface/tokenizers/301277072263fb3830eb66eec7e47adadf76f1dc/bindings/python/Cargo.toml', 'b22e1ccb03566a1d4d30ffa415dee41be1f3bd7f4188f53c393e27154f45126d', 1160),
 'tokenizers-python-Cargo.lock': ('https://raw.githubusercontent.com/huggingface/tokenizers/301277072263fb3830eb66eec7e47adadf76f1dc/bindings/python/Cargo.lock', 'afcedf7f2ebe008b068d7afd25e77f7d9d8e433c24153bc35a1eb5611083ee5b', 36178),
 'flatbuffers-LICENSE.txt': ('https://raw.githubusercontent.com/google/flatbuffers/7e163021e59cca4f8e1e35a7c828b5c6b7915953/LICENSE', 'cfc7749b96f63bd31c3c42b5c471bf756814053e847c10f3eb003417bc523d30', 11358),
}
TERMS = {
 'anyio': 'MIT', 'click': 'BSD-3-Clause', 'filelock': 'MIT', 'flatbuffers': 'Apache-2.0',
 'fsspec': 'BSD-3-Clause', 'h11': 'MIT', 'hf-xet': 'Apache-2.0', 'httpcore2': 'BSD-3-Clause',
 'httpx2': 'BSD-3-Clause', 'huggingface_hub': 'Apache-2.0', 'idna': 'BSD-3-Clause',
 'ml_dtypes': 'Apache-2.0 AND MPL-2.0', 'numpy': 'Multiple retained bundled terms',
 'onnx': 'Apache-2.0 and retained NOTICE', 'onnxruntime': 'MIT and retained third-party terms',
 'packaging': 'Apache-2.0 OR BSD-2-Clause', 'protobuf': 'BSD-3-Clause', 'PyYAML': 'MIT',
 'tokenizers': 'Apache-2.0 upstream source text; absent from wheel', 'tqdm': 'MPL-2.0 AND MIT',
 'truststore': 'MIT', 'typing_extensions': 'PSF-2.0',
}
BLOCKERS = {
 'hf-xet': 'Rust bundled dependency terms and exact native build/source correspondence not established',
 'ml_dtypes': 'Eigen MPL covered source availability and exact binary/header source correspondence not established',
 'numpy': 'Platform-specific bundled BLAS/Fortran terms and applicable corresponding source not established',
 'onnx': 'NOTICE names bundled abseil/protobuf/nanobind; exact linked-source/license correspondence not established',
 'onnxruntime': 'Full embedded-term applicability/source offers unresolved; pinned upstream tag and advertised short commit retrieval failed',
 'protobuf': 'Bundled native implementation and dependency source/license correspondence not established',
 'PyYAML': 'Bundled LibYAML implementation/source/notice correspondence not established',
 'tokenizers': 'Upstream Apache text retained; exact compiled Rust dependency/source correspondence not established',
}
SOURCE_FAILURES = [{'url':url,'http_status':404,'scope':'observed retrieval failure; no replacement with main'} for url in (
 'https://api.github.com/repos/microsoft/onnxruntime/releases/tags/v1.31.0',
 'https://raw.githubusercontent.com/microsoft/onnxruntime/v1.31.0/LICENSE',
 'https://api.github.com/repos/microsoft/onnxruntime/commits/402979a')]
MAX_WHEEL = 128_000_000
MAX_EXPANDED = 512_000_000
MAX_NOTICE = 1_000_000
MAX_FILES = 20_000
MAX_CENTRAL = 8_000_000


def need(ok):
    if not ok:raise ValueError('NLI license cohort refused')


def encoded(value):return json.dumps(value, sort_keys=True, ensure_ascii=True, allow_nan=False, separators=(',', ':')).encode()
def sha(raw):return hashlib.sha256(raw).hexdigest()


def read(path, limit=8_000_000):
    path = Path(path).absolute()
    need(not any(p.is_symlink() for p in (path, *path.parents)))
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, 'rb') as stream:
        before = os.fstat(stream.fileno())
        need(stat.S_ISREG(before.st_mode) and before.st_nlink == 1 and 0 < before.st_size <= limit)
        raw = stream.read(limit + 1);after = os.fstat(stream.fileno())
        need(len(raw) == before.st_size and (before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns) ==
             (after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns))
        return raw


def safe(name):
    need(type(name) is str and 0 < len(name) <= 512 and name.isascii() and
         re.fullmatch(r'[A-Za-z0-9_./+@-]+', name) and not name.startswith('/') and
         all(part not in ('', '.', '..') for part in name.rstrip('/').split('/')))


def unique(pairs):
    result = {}
    for key, value in pairs:
        need(key not in result);result[key] = value
    return result


def document(raw):
    return json.loads(raw.decode('utf-8'), object_pairs_hook=unique,
                      parse_constant=lambda _: need(False))


def selected(root):
    assets = document(read(root/'research/nli/assets.json'))
    need(assets['revision'] == REVISION and [r['name'] for r in assets['files']] ==
         ['model.onnx', 'tokenizer.json', 'config.json', 'README.md'])
    tree = ast.parse(read(root/'research/nli/backend.py'))
    versions = next(ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign) and
                    any(isinstance(t, ast.Name) and t.id == 'VERSIONS' for t in n.targets))
    need(set(versions) == set(TERMS))
    rows = []
    for platform in ('mac', 'linux'):
        current = document(read(root/('research/nli/wheel-provenance-'+platform+'.json')))
        need(len(current) == 22 and {r['name']: r['version'] for r in current} == versions)
        expected = ''.join(f"{r['name']}=={r['version']} --hash=sha256:{r['sha256']}\n" for r in current)
        need(read(root/('research/nli/requirements-'+platform+'.lock')).decode() == expected)
        for row in current:
            safe(row['wheel']);need('/' not in row['wheel'] and re.fullmatch('[a-f0-9]{64}', row['sha256']))
            rows.append({'platform': platform, **row})
    return assets, sorted(rows, key=lambda row: (row['platform'], row['name']))


def central_directory(raw):
    """Bound filelist allocation before ZipFile, including a lying EOCD count."""
    need(type(raw) is bytes and 22 <= len(raw) <= MAX_WHEEL)
    end = raw.rfind(b'PK\x05\x06',max(0,len(raw)-65557))
    need(end >= 0 and end+22==len(raw))
    _,disk,central_disk,disk_entries,entries,size,offset,comment = struct.unpack_from('<4s4H2IH',raw,end)
    need(disk==central_disk==comment==0 and 0 < entries==disk_entries <= MAX_FILES and
         size<=MAX_CENTRAL and offset+size==end)
    def extras(data,local_sizes=None):
        cursor=0;zip64=None
        while cursor<len(data):
            need(cursor+4<=len(data))
            kind,length=struct.unpack_from('<HH',data,cursor)
            need(cursor+4+length<=len(data))
            if kind==1:
                need(local_sizes is not None and zip64 is None and length==16)
                zip64=struct.unpack_from('<QQ',data,cursor+4)
                need(zip64==local_sizes)
            cursor+=4+length
        return zip64
    cursor=offset;count=0;names=set()
    while cursor<end:
        need(cursor+46<=end and raw[cursor:cursor+4]==b'PK\x01\x02')
        name,extra,description,disk_number=struct.unpack_from('<4H',raw,cursor+28)
        need(0<name<=512 and extra<=4096 and description<=4096 and disk_number==0)
        need(cursor+46+name+extra+description<=end)
        raw_name=raw[cursor+46:cursor+46+name]
        decoded=raw_name.decode('ascii','strict');safe(decoded)
        need(decoded not in names);names.add(decoded)
        version,flags,method=struct.unpack_from('<HHH',raw,cursor+6)
        compressed,expanded=struct.unpack_from('<II',raw,cursor+20)
        local=struct.unpack_from('<I',raw,cursor+42)[0]
        need((version<=20 or version==45) and not flags&1 and method in (zipfile.ZIP_STORED,zipfile.ZIP_DEFLATED) and
             compressed!=0xffffffff and expanded!=0xffffffff and local+30<=offset)
        extras(raw[cursor+46+name:cursor+46+name+extra])
        need(raw[local:local+4]==b'PK\x03\x04')
        local_version,local_flags,local_method=struct.unpack_from('<HHH',raw,local+4)
        local_compressed,local_expanded=struct.unpack_from('<II',raw,local+18)
        local_name,local_extra=struct.unpack_from('<HH',raw,local+26)
        need((local_version<=20 or local_version==45) and local_flags==flags and local_method==method and
             local_name==name and local_extra<=4096 and local+30+local_name+local_extra<=offset)
        need(raw[local+30:local+30+local_name]==raw_name)
        zip64=extras(raw[local+30+local_name:local+30+local_name+local_extra],(expanded,compressed))
        if zip64 is None:
            need(version<=20 and local_version<=20 and local_compressed!=0xffffffff and local_expanded!=0xffffffff)
            need(flags&8 or (local_compressed,local_expanded)==(compressed,expanded))
        else:
            # Some pinned wheels carry redundant local ZIP64 sizes despite a
            # classic central directory. They must equal its bounded sizes.
            need(local_compressed in (compressed,0xffffffff) and local_expanded in (expanded,0xffffffff))
        cursor += 46+name+extra+description;count+=1
        need(cursor<=end and count<=MAX_FILES)
    need(cursor==end and count==entries)


def wheel(raw, expected_sha):
    """Hash/CRC-check bounded data, with no archive extraction or imports."""
    need(type(raw) is bytes and 0 < len(raw) <= MAX_WHEEL and sha(raw) == expected_sha)
    central_directory(raw)
    notices = {};native = [];inventory = [];count = 0;total = 0;seen = set()
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        need(not archive.comment and 0 < len(archive.infolist()) <= MAX_FILES)
        for info in archive.infolist():
            need(info.orig_filename==info.filename);safe(info.orig_filename);safe(info.filename)
            need(info.filename not in seen);seen.add(info.filename)
            mode = info.external_attr >> 16
            need(not stat.S_ISLNK(mode) and (not stat.S_IFMT(mode) or stat.S_ISREG(mode) or stat.S_ISDIR(mode)))
            need(not info.flag_bits & 1 and info.compress_type in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED))
            need(0 <= info.file_size <= MAX_WHEEL);total += info.file_size;need(total <= MAX_EXPANDED)
            if info.is_dir():continue
            is_notice = any(word in info.filename.rsplit('/', 1)[-1].lower() for word in
                            ('license', 'licence', 'notice', 'copying', 'copyright'))
            if is_notice:need(0 < info.file_size <= MAX_NOTICE)
            digest = hashlib.sha256();prefix = b'';parts = [];length = 0
            with archive.open(info) as stream:
                while True:
                    chunk = stream.read(65536)
                    if not chunk:break
                    length += len(chunk);need(length <= info.file_size)
                    digest.update(chunk)
                    if len(prefix) < 4:prefix += chunk[:4-len(prefix)]
                    if is_notice:parts.append(chunk)
            need(length == info.file_size)
            item = {'member': info.filename, 'sha256': digest.hexdigest(), 'bytes': length}
            inventory.append(item)
            if info.filename.endswith('.py'):count += 1
            if prefix in (b'\x7fELF', b'\xcf\xfa\xed\xfe', b'\xfe\xed\xfa\xcf', b'\xca\xfe\xba\xbe',
                          b'\xca\xfe\xba\xbf',b'\xbe\xba\xfe\xca',b'\xbf\xba\xfe\xca',
                          b'\xfe\xed\xfa\xce',b'\xce\xfa\xed\xfe') or prefix[:2] == b'MZ':native.append(item)
            if is_notice:
                body = b''.join(parts);body.decode('utf-8', 'strict');notices[info.filename] = body
    return {'member_count': len(inventory), 'contents_sha256': sha(encoded(sorted(inventory, key=lambda r:r['member']))),
            'python_source_count': count, 'native_members': sorted(native, key=lambda r:r['member']),
            'notices': [{'member': name, 'sha256': sha(body), 'bytes': len(body)} for name, body in sorted(notices.items())]}, notices


def obligation(row):
    name = row['name'];native = name in NATIVE
    need(bool(row['native_members']) == native and row['python_source_count'] > 0)
    actions = ['preserve exact copyright, grant, attribution and disclaimer texts',
               'do not imply upstream endorsement; preserve applicable patent/trademark limits',
               'identify modifications if distributing modified covered files']
    offer = 'No source offer identified in reviewed primary permissive terms; source Python files are included'
    if name == 'tqdm':
        actions += ['retain MPL notice and provide covered Source Code Form under MPL-2.0; retain MIT portions']
        offer = 'Covered Python Source Code Form is present in this wheel; no native member observed'
    if native:
        actions += ['resolve exact bundled native terms and applicable source/relinking obligations before redistribution approval']
        offer = BLOCKERS[name]
    return {'name': name, 'version': row['version'], 'platform': row['platform'], 'wheel_sha256': row['sha256'],
            'terms_reviewed': TERMS[name], 'retention_actions': actions, 'source_offer': offer,
            'native_obligations_resolved': False if native else None,
            'status': 'blocked_native_obligations' if native else 'source_notice_retention_bound',
            'upstream_license_text_required': name in {'flatbuffers', 'tokenizers'},
            'permission_cleared': False}


def fingerprints(root):return {name:sha(read(root/name)) for name in INPUTS+OWN}


def blob(root, raw, pending):
    digest = sha(raw);existing = 'research/nli/notices/'+digest+'.txt'
    if (root/existing).exists():need(read(root/existing, MAX_NOTICE) == raw);return existing
    name = STORE+'/notices/'+digest+'.txt';pending[name] = raw;return name


def bundle(notices, sources):
    result = [b'NLI cohort notice/source reference bundle. Identity and retention evidence only; distribution remains blocked.\n',
              b'Pinned publisher declares Apache-2.0 for the model repository through card metadata.\n',
              b'Related base/source references do not establish the exact training-base revision or complete native source correspondence.\n']
    for item in sources:result.append(('\nSOURCE '+item['name']+'\n'+item['url']+'\nSHA256 '+item['sha256']+'\n').encode())
    for name, raw in sorted(notices.items()):result.extend([('\n===== '+name+' =====\n').encode(), raw, b'\n'])
    return b''.join(result)


def model_review(assets, upstream, card):
    trees = {name:document(upstream[name]) for name in ('model-tree.json', 'base-tree.json')}
    need(not any(row['path'].rsplit('/',1)[-1].lower() in ('license','license.txt','licence') for rows in trees.values() for row in rows))
    model = {row['path']:row for row in trees['model-tree.json']}
    for item in assets['files']:
        member = 'onnx/model.onnx' if item['name']=='model.onnx' else item['name']
        need(model[member]['size'] == item['bytes'])
        if item['name']=='model.onnx':need(model[member]['lfs']['oid'] == item['sha256'])
    need(b'license: apache-2.0' in card and b'microsoft/deberta-v3-xsmall' in card)
    need(b'license: mit' in upstream['base-README.md'])
    return {'repository': 'cross-encoder/nli-deberta-v3-xsmall', 'revision': REVISION,
            'assets': assets['files'], 'card_license_declaration': 'Apache-2.0',
            'base_repository_declared': 'microsoft/deberta-v3-xsmall', 'base_observation_revision': BASE_REVISION,
            'base_license_declaration': 'MIT', 'license_file_present_in_model_or_base_tree': False,
            'publisher_license_metadata_semantics':'https://huggingface.co/docs/hub/repositories-licenses',
            'publisher_declared_repository_license_evidence':True,
            'exact_pretraining_base_revision_established': False,
            'related_microsoft_code_license_is_model_grant': False,
            'training_datasets_bundled': False, 'independent_rights_or_accuracy_verified': False,
            'status': 'publisher_declared_terms_bound_base_correspondence_unestablished'}


def collect(root, wheel_dirs, source_cache):
    root = Path(root);need(not (root/STORE).exists());before = fingerprints(root)
    assets, chosen = selected(root);pending = {};sources = [];upstream = {}
    for name, (url, digest, size) in UPSTREAM.items():
        raw = read(Path(source_cache)/name, 1_000_000);need(len(raw)==size and sha(raw)==digest)
        upstream[name] = raw;path = STORE+'/sources/'+name;pending[path] = raw
        sources.append({'name':name,'url':url,'sha256':digest,'bytes':size,'path':path})
    observations = [];all_notices = {}
    for selected_row in chosen:
        raw = read(Path(wheel_dirs[selected_row['platform']])/selected_row['wheel'], MAX_WHEEL)
        observed, notices = wheel(raw, selected_row['sha256'])
        for item in observed['notices']:
            body = notices[item['member']];item['path'] = blob(root, body, pending);all_notices[item['path']] = body
        observations.append({**selected_row, 'artifact_bytes':len(raw), **observed})
    retained = document(read(root/'research/nli/notices.json'))['notices']
    model_card = next(row for row in retained if row.get('component')=='cross-encoder/nli-deberta-v3-xsmall')
    card = read(root/model_card['notice_file']);need(sha(card)==model_card['sha256'])
    all_notices[model_card['notice_file']] = card
    for name in ('tokenizers-LICENSE.txt','flatbuffers-LICENSE.txt','deberta-LICENSE.txt','base-README.md'):
        all_notices[next(r['path'] for r in sources if r['name']==name)] = upstream[name]
    value = {'profile':PROFILE,'captured_at':datetime.now(timezone.utc).isoformat(),'observed_by':'Codex',
             'sources':before,'upstream':sources,'model':model_review(assets,upstream,card),'wheels':observations,
             'obligations':[obligation(row) for row in observations],
             'source_retrieval_failures':SOURCE_FAILURES,
             'permission_cleared':False,'complete_native_source_coverage':False,
             'distribution_ready':False,'independent_accuracy_evidence':False}
    payload = bundle(all_notices, sources);pending[BUNDLE] = payload
    value['bundle'] = {'path':BUNDLE,'sha256':sha(payload),'bytes':len(payload)}
    value['observation_sha256'] = sha(encoded(value))
    need(fingerprints(root)==before)
    # Refuse all existing output; original observations are never rewritten.
    (root/STORE).mkdir()
    for name, raw in sorted(pending.items()):
        path = root/name;path.parent.mkdir(parents=True,exist_ok=True)
        with path.open('xb') as stream:stream.write(raw)
    with (root/MANIFEST).open('xb') as stream:stream.write(json.dumps(value,indent=2).encode()+b'\n')
    return verify(root, wheel_dirs=wheel_dirs)


def verify(root=ROOT, *, wheel_dirs=None):
    root = Path(root);value = document(read(root/MANIFEST))
    need(set(value)=={'profile','captured_at','observed_by','sources','upstream','model','wheels','obligations',
                     'source_retrieval_failures','permission_cleared','complete_native_source_coverage',
                     'distribution_ready','independent_accuracy_evidence','bundle','observation_sha256'})
    projection = {k:v for k,v in value.items() if k!='observation_sha256'}
    need(sha(encoded(projection))==value['observation_sha256'] and value['profile']==PROFILE and
         value['observed_by']=='Codex' and value['sources']==fingerprints(root))
    need(all(value[k] is False for k in ('permission_cleared','complete_native_source_coverage','distribution_ready','independent_accuracy_evidence')))
    need(value['source_retrieval_failures']==SOURCE_FAILURES)
    assets, chosen = selected(root);need(len(value['wheels'])==44)
    need([{k:row[k] for k in selected_row} for row,selected_row in zip(value['wheels'],chosen)]==chosen)
    need(value['obligations']==[obligation(row) for row in value['wheels']])
    upstream = {};all_notices = {};legacy = document(read(root/'research/nli/notices.json'))['notices']
    need(len(value['upstream'])==len(UPSTREAM) and len({r['name'] for r in value['upstream']})==len(UPSTREAM))
    for row in value['upstream']:
        need(set(row)=={'name','url','sha256','bytes','path'} and row['name'] in UPSTREAM)
        need((row['url'],row['sha256'],row['bytes'])==UPSTREAM[row['name']] and row['path']==STORE+'/sources/'+row['name'])
        raw = read(root/row['path'], MAX_NOTICE);need(len(raw)==row['bytes'] and sha(raw)==row['sha256']);upstream[row['name']] = raw
    need(set(upstream)==set(UPSTREAM))
    for row in value['wheels']:
        selected_row = next(r for r in chosen if (r['name'],r['platform'])==(row['name'],row['platform']))
        need(set(row)==set(selected_row)|{'artifact_bytes','member_count','contents_sha256','python_source_count','native_members','notices'})
        need(type(row['native_members']) is list and len(row['native_members'])<=1000 and type(row['notices']) is list and len(row['notices'])<=128)
        need(row['member_count']>0 and row['artifact_bytes']<=MAX_WHEEL and re.fullmatch('[a-f0-9]{64}',row['contents_sha256']))
        for item in row['native_members']+row['notices']:
            need(set(item)==({'member','sha256','bytes','path'} if 'path' in item else {'member','sha256','bytes'}))
            safe(item['member']);need(type(item['bytes']) is int and item['bytes']>=0 and re.fullmatch('[a-f0-9]{64}',item['sha256']))
        for item in row['notices']:
            need(item['path'] in ('research/nli/notices/'+item['sha256']+'.txt',STORE+'/notices/'+item['sha256']+'.txt'))
            raw = read(root/item['path'],MAX_NOTICE);need(len(raw)==item['bytes'] and sha(raw)==item['sha256']);all_notices[item['path']] = raw
        if wheel_dirs is not None:
            raw = read(Path(wheel_dirs[row['platform']])/row['wheel'],MAX_WHEEL)
            observed, _ = wheel(raw,row['sha256'])
            expected = {k:row[k] for k in observed};expected['notices']=[{k:v for k,v in item.items() if k!='path'} for item in row['notices']]
            need(observed==expected and len(raw)==row['artifact_bytes'])
    card_row = next(row for row in legacy if row.get('component')=='cross-encoder/nli-deberta-v3-xsmall')
    card = read(root/card_row['notice_file']);need(sha(card)==card_row['sha256']);all_notices[card_row['notice_file']] = card
    need(value['model']==model_review(assets,upstream,card))
    for name in ('tokenizers-LICENSE.txt','flatbuffers-LICENSE.txt','deberta-LICENSE.txt','base-README.md'):
        all_notices[STORE+'/sources/'+name] = upstream[name]
    payload = bundle(all_notices,value['upstream'])
    need(value['bundle']=={'path':BUNDLE,'sha256':sha(payload),'bytes':len(payload)} and read(root/BUNDLE,4_000_000)==payload)
    new_notice_paths = {item['path'] for row in value['wheels'] for item in row['notices'] if item['path'].startswith(STORE+'/')}
    expected_paths = {MANIFEST,BUNDLE}|new_notice_paths|{row['path'] for row in value['upstream']}
    need({str(path.relative_to(root)) for path in (root/STORE).rglob('*') if path.is_file() or path.is_symlink()}==expected_paths)
    need(value['sources']==fingerprints(root))
    return {'profile':PROFILE,'pass':True,'wheel_occurrences':44,'packages_per_platform':22,
            'notice_occurrences':sum(len(row['notices']) for row in value['wheels']),
            'unique_notice_texts':len({item['sha256'] for row in value['wheels'] for item in row['notices']}),
            'source_form_package_occurrences':sum(row['name'] not in NATIVE for row in value['wheels']),
            'blocked_native_package_occurrences':sum(row['name'] in NATIVE for row in value['wheels']),
            'model_license_evidence':'pinned_publisher_declared_apache2',
            'exact_training_base_revision_established':False,'archive_bytes_replayed':wheel_dirs is not None,
            'observation_sha256':value['observation_sha256'],'notice_bundle_sha256':sha(payload),
            'distribution_ready':False,'permission_cleared':False,'independent_accuracy_evidence':False,
            'complete_project_obligations':False}
