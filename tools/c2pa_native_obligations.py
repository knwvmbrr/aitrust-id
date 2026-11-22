"""Source-only C2PA published Cargo graph; never grants native clearance."""
import gzip
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import tarfile
import time
import tomllib
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
PROFILE = 'c2pa-native-dependency-observations/v1'
STORE = 'sbom/c2pa-native/sources/'
MANIFEST = 'sbom/c2pa-native/manifest.json'
ROOT_NAME = 'c2pa-c-ffi'
VERSION = '0.91.0'
ROOT_SHA = '612bffa120fdb58b5b6767602b0c0c77a20e139a7102b3e13e85236308ee49f4'
COMMIT = 'e7cc666c3409bdaf4cea8e49046dfbf8290dff89'
LOCK_SHA = '0625bfce6060f01e9777fc88846fe85ba6a8b958c79d1d6da38b9857be236d59'
REGISTRY = 'registry+https://github.com/rust-lang/crates.io-index'
MAX_ARCHIVE = 16 * 1024**2
MAX_EXPANDED = 128 * 1024**2
MAX_MEMBER = 32 * 1024**2
MAX_RETAINED = 4 * 1024**2
MAX_FILES = 20000
MAX_PACKAGES = 1000
MAX_CACHE = 256 * 1024**2
INPUTS = ['sbom/c2pa/manifest.json', 'eval/dependencies/c2pa-inspection.json',
          'sbom/c2pa/sources/fbc34a38fe7a9047c157fbb4caf273d16c1448b23ead8e55573afa3b4494b4b3.txt',
          'sbom/c2pa-native/notice-supplements.json','sbom/c2pa-native/native-labels.json',
          'tools/c2pa_native_obligations.py','scripts/verify-c2pa-native-obligations.py',
          'tests/test_c2pa_native_obligations.py','sbom/c2pa-native/.gitattributes']
UNRESOLVED = ['Published package lock includes optional/dev/target alternatives; exact selected native feature/build closure is not established.', 'VCS declaration and matching selected manifests do not authenticate all archived source or compiler.', 'Embedded/system dependencies and distribution-specific source/notice obligations require explicit review.']
CLAIMS = {'permission_cleared': False, 'distribution_approved': False,
          'source_build_reproduced': False, 'independent_accuracy': False}


def need(value):
    if not value:raise ValueError('C2PA native evidence refused.')


def sha(raw):return hashlib.sha256(raw).hexdigest()


def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()


def strict(raw):
    def pairs(items):
        result={}
        for k,v in items:need(k not in result);result[k]=v
        return result
    return json.loads(raw,object_pairs_hook=pairs,
        parse_constant=lambda _:(_ for _ in ()).throw(ValueError('C2PA native evidence refused.')))


def read(path,limit=MAX_RETAINED):
    path=Path(path).absolute()
    need(not any(p.is_symlink() for p in [path,*path.parents]))
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    try:
        before=os.fstat(fd);need(stat.S_ISREG(before.st_mode) and 0<=before.st_size<=limit)
        raw=bytearray()
        while len(raw)<=limit:
            part=os.read(fd,min(65536,limit+1-len(raw)))
            if not part:break
            raw.extend(part)
        after=os.fstat(fd);current=os.stat(path,follow_symlinks=False)
        identity=lambda s:(s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns)
        need(identity(before)==identity(after)==identity(current) and len(raw)==before.st_size)
        return bytes(raw)
    finally:os.close(fd)


def safe(name):
    need(type(name) is str and 0<len(name)<=512 and not name.startswith('/') and '\\' not in name
         and ':' not in name and all(32<=ord(c)!=127 for c in name)
         and all(p not in ('','.','..') for p in name.rstrip('/').split('/')))


def token(name,version):
    need(type(name) is str and re.fullmatch(r'[A-Za-z0-9_-]{1,128}',name))
    need(type(version) is str and re.fullmatch(r'[0-9][A-Za-z0-9.+_-]{0,127}',version))
    return name+'@'+version


def url(name,version):
    token(name,version)
    return f'https://static.crates.io/crates/{name}/{name}-{version}.crate'


class Expanded:
    def __init__(self,handle):self.handle=handle;self.total=0
    def read(self,size=-1):
        left=MAX_EXPANDED-self.total
        data=self.handle.read(left+1 if size<0 else min(size,left+1))
        self.total+=len(data);need(self.total<=MAX_EXPANDED);return data


def notice(name):
    return PurePosixPath(name).name.lower() in ('authors','authors.txt','authors.md') or any(re.search(r'license|licence|copying|copyright|notice|patents',part.lower()) for part in PurePosixPath(name).parts)


def archive(raw,name,version):
    need(type(raw) is bytes and 0<len(raw)<=MAX_ARCHIVE)
    prefix=name+'-'+version+'/'
    rows={};seen=set();expanded=0;retained=0
    with gzip.GzipFile(fileobj=io.BytesIO(raw)) as gz:
        bounded=Expanded(gz)
        with tarfile.open(fileobj=bounded,mode='r|') as t:
            for member in t:
                safe(member.name);need(member.name not in seen and len(seen)<MAX_FILES);seen.add(member.name)
                need(member.name.startswith(prefix) and (member.isfile() or member.isdir()))
                need(0<=member.size<=MAX_MEMBER);expanded+=member.size;need(expanded<=MAX_EXPANDED)
                if member.isdir():need(member.size==0);continue
                relative=member.name[len(prefix):]
                selected=relative in ('Cargo.toml','Cargo.toml.orig','Cargo.lock','.cargo_vcs_info.json') or notice(relative) or PurePosixPath(relative).name.lower().startswith('readme')
                if selected:
                    need(member.size<=MAX_RETAINED and retained+member.size<=MAX_RETAINED)
                    with t.extractfile(member) as f:data=f.read(member.size+1)
                    need(len(data)==member.size);retained+=len(data);rows[relative]=data
        # Consume the bounded gzip trailer/remaining tar padding to detect errors.
        while bounded.read(65536):pass
    need('Cargo.toml' in rows)
    return rows


def lock_graph(raw):
    need(len(raw)<=MAX_RETAINED)
    data=tomllib.loads(raw.decode('utf-8'));need(data.get('version') in (3,4))
    nodes=data.get('package');need(type(nodes) is list and 1<=len(nodes)<=MAX_PACKAGES)
    indexed={};names={}
    for row in nodes:
        need(type(row) is dict and {'name','version'}<=set(row)<= {'name','version','source','checksum','dependencies','replace'})
        ident=token(row['name'],row['version']);need(ident not in indexed and 'replace' not in row)
        if row.get('source') is None:need(ident==ROOT_NAME+'@'+VERSION and 'checksum' not in row)
        else:need(row['source']==REGISTRY and re.fullmatch('[a-f0-9]{64}',row.get('checksum','')))
        indexed[ident]=row;names.setdefault(row['name'],[]).append(ident)
    result=[]
    for ident,row in indexed.items():
        deps=[]
        for dependency in row.get('dependencies',[]):
            need(type(dependency) is str and len(dependency)<=512)
            parts=dependency.split(' ');need(1<=len(parts)<=2)
            matches=names.get(parts[0],[]) if len(parts)==1 else [token(*parts)]
            need(len(matches)==1 and matches[0] in indexed and matches[0] not in deps)
            deps.append(matches[0])
        result.append({'id':ident,'name':row['name'],'version':row['version'],
                       'archive_sha256':row.get('checksum',ROOT_SHA),'dependency_ids':sorted(deps)})
    need(ROOT_NAME+'@'+VERSION in indexed)
    return sorted(result,key=lambda r:r['id'])


def declarations(manifest):
    rows=[]
    for key in ('dependencies','build-dependencies','dev-dependencies'):
        for name,value in manifest.get(key,{}).items():
            rows.append({'kind':key,'target':None,'name':name,'declaration':value})
    for target, groups in manifest.get('target',{}).items():
        for key in ('dependencies','build-dependencies','dev-dependencies'):
            for name,value in groups.get(key,{}).items():
                rows.append({'kind':key,'target':target,'name':name,'declaration':value})
    need(len(rows)<=1000)
    return sorted(rows,key=lambda r:(r['kind'],r['target'] or '',r['name']))


def package_record(node,members,blobs,supplement=None):
    parsed=tomllib.loads(members['Cargo.toml'].decode('utf-8'));p=parsed['package']
    need(p['name']==node['name'] and p['version']==node['version'])
    license_value=p.get('license');license_file=p.get('license-file')
    need(license_value is None or type(license_value) is str and len(license_value)<=512)
    if license_file is not None:
        safe(license_file);need(license_file in members)
    retained=[]
    for member,raw in sorted(members.items()):
        path=STORE+sha(raw)+'.txt'
        if path in blobs:need(blobs[path]==raw)
        else:blobs[path]=raw
        retained.append({'member':member,'path':path,'sha256':sha(raw),'bytes':len(raw)})
    notices=[r['path'] for r in retained if notice(r['member'])]
    vcs=None
    if '.cargo_vcs_info.json' in members:
        vcs=strict(members['.cargo_vcs_info.json'])
    supplement=supplement or {'notices':[], 'evidence_paths':[]}
    return {**node,'source_identity':{'kind':'official_checksummed_registry_archive','url':url(node['name'],node['version']),
                                     'sha256':node['archive_sha256'],'vcs_declaration':vcs},
            'license_declared':license_value,'license_file_declared':license_file,'notice_paths':sorted(set(notices)),
            'supplemental_source_notices':supplement['notices'],
            'source_readme_paths':[r['path'] for r in retained if PurePosixPath(r['member']).name.lower().startswith('readme')],
            'supplement_evidence_paths':supplement['evidence_paths'],
            'retained_members':retained,'dependency_declarations':declarations(parsed),
            'features_declared':parsed.get('features',{}),
            'term_actions':['retain_applicable_copyright_license_and_notice_texts','review_declared_terms_for_this_distribution'],
            'unresolved':[] if license_value and notices else ['license_declaration_or_shipped_notice_absent'],
            'evidence_paths':[r['path'] for r in retained]}


def load_cache(cache,node):
    name=node['name']+'-'+node['version']+'.crate'
    raw=read(Path(cache)/name,MAX_ARCHIVE);need(sha(raw)==node['archive_sha256'])
    return raw


def fetch(cache,node):
    cache=Path(cache);target=cache/(node['name']+'-'+node['version']+'.crate')
    if target.exists():return load_cache(cache,node)
    need(shutil.disk_usage(cache).free>=2*1024**3+MAX_ARCHIVE)
    request=urllib.request.Request(url(node['name'],node['version']),headers={'User-Agent':'AITrust-ID-source-evidence/1'})
    start=time.monotonic()
    with urllib.request.urlopen(request,timeout=15) as response:
        need(response.url==url(node['name'],node['version']))
        raw=bytearray()
        while len(raw)<=MAX_ARCHIVE:
            need(time.monotonic()-start<30)
            part=response.read(min(65536,MAX_ARCHIVE+1-len(raw)))
            if not part:break
            raw.extend(part)
    need(len(raw)<=MAX_ARCHIVE and sha(raw)==node['archive_sha256'])
    need(sum(p.stat().st_size for p in cache.glob('*.crate'))+len(raw)<=MAX_CACHE)
    fd=os.open(target,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    try:
        with os.fdopen(fd,'wb',closefd=False) as f:f.write(raw);f.flush();os.fsync(f.fileno())
    finally:
        owned=fd;fd=None;os.close(owned)
    return bytes(raw)


def root_source(cache,download=False):
    node={'name':ROOT_NAME,'version':VERSION,'archive_sha256':ROOT_SHA}
    raw=fetch(cache,node) if download else load_cache(cache,node)
    members=archive(raw,ROOT_NAME,VERSION)
    need('Cargo.lock' in members and 'Cargo.toml.orig' in members and sha(members['Cargo.lock'])==LOCK_SHA)
    vcs=strict(members['.cargo_vcs_info.json']);need(vcs=={'git':{'sha1':COMMIT},'path_in_vcs':'c2pa_c_ffi'})
    need(sha(members['Cargo.toml.orig'])=='fbc34a38fe7a9047c157fbb4caf273d16c1448b23ead8e55573afa3b4494b4b3')
    return members,lock_graph(members['Cargo.lock'])



def supplements(root,blobs,cache=None):
    index=strict(read(root/'sbom/c2pa-native/notice-supplements.json'))
    need(set(index)=={'format','captured_at','packages','role','permission_cleared'}
         and index['format']=='c2pa-native-pinned-source-notice-supplements/v1'
         and index['role']=='exact_upstream_commit_notices_not_claimed_as_crate_members'
         and index['permission_cleared'] is False)
    result={}
    for item in index['packages']:
        need(set(item)=={'package_id','repository','upstream_commit','vcs_path','tree_evidence','notices'})
        need(item['package_id'] not in result and re.fullmatch('[a-f0-9]{40}',item['upstream_commit']))
        match=re.fullmatch(r'https://github.com/([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)',item['repository']);need(match is not None)
        tree_info=item['tree_evidence']
        need(set(tree_info)=={'path','sha256','bytes','official_url'})
        need(tree_info['official_url']==f'https://api.github.com/repos/{match[1]}/git/trees/{item["upstream_commit"]}')
        evidence=[]
        for row in [tree_info,*item['notices']]:
            need(re.fullmatch(STORE+r'[a-f0-9]{64}\.txt',row['path']))
            raw=read(root/row['path']);need(sha(raw)==row['sha256'] and len(raw)==row['bytes'])
            if cache is not None:need(read(Path(cache)/(sha(raw)+'.source'))==raw)
            blobs[row['path']]=raw;evidence.append(row['path'])
        tree=strict(blobs[tree_info['path']]);need(tree['truncated'] is False)
        tree_members={r['path']:r for r in tree['tree']}
        for row in item['notices']:
            need(set(row)=={'upstream_path','official_url','git_blob_sha1','path','sha256','bytes','role'})
            safe(row['upstream_path'])
            need(row['role']=='upstream_source_notice_not_present_in_selected_crate')
            need(row['official_url']==f'https://raw.githubusercontent.com/{match[1]}/{item["upstream_commit"]}/{row["upstream_path"]}')
            raw=blobs[row['path']]
            need(tree_members[row['upstream_path']]['type']=='blob'
                 and tree_members[row['upstream_path']]['sha']==row['git_blob_sha1']
                 and hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==row['git_blob_sha1'])
        result[item['package_id']]={'notices':item['notices'],'evidence_paths':sorted(set(evidence)),
                                   'commit':item['upstream_commit'],'vcs_path':item['vcs_path'],'repository':item['repository']}
    return result


def bind_supplement(package,selected,blobs):
    if selected:
        vcs=package['source_identity']['vcs_declaration']
        need(vcs is not None and vcs['git']['sha1']==selected['commit'] and vcs['path_in_vcs']==selected['vcs_path'])
        manifest=next(r for r in package['retained_members'] if r['member']=='Cargo.toml')
        repository=tomllib.loads(blobs[manifest['path']].decode('utf-8'))['package'].get('repository','').removesuffix('.git')
        need(repository==selected['repository'])
    return package


def native_labels(cache,root=ROOT):
    from tools.c2pa_cohort import zip_directory_preflight
    old=strict(read(Path(root)/'sbom/c2pa/manifest.json'))
    result=[]
    pattern=re.compile(rb'registry/src/[A-Za-z0-9._-]+/([A-Za-z0-9_-]+)-(\d+\.\d+\.\d+(?:[-+][A-Za-z0-9._-]+)?)/')
    for row in old['sdk_upstream']['native_matches']:
        wheel=next(w for w in old['wheels'] if w['filename']==row['wheel'])
        raw=read(Path(cache)/row['wheel'],64*1024**2);need(sha(raw)==wheel['sha256'])
        zip_directory_preflight(raw)
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            info=z.getinfo(row['wheel_member']);need(info.file_size<=MAX_MEMBER)
            with z.open(info) as handle:binary=handle.read(MAX_MEMBER+1)
        need(len(binary)==row['native']['bytes'] and sha(binary)==row['native']['sha256'])
        labels=sorted({token(m[1].decode(),m[2].decode()) for m in pattern.finditer(binary)})
        need(len(labels)<=MAX_PACKAGES)
        result.append({'profile':row['profile'],'native_sha256':row['native']['sha256'],
                       'package_ids':labels,'observation':'embedded_registry_source_version_labels_only',
                       'exhaustive':False,'binary_executed':False})
    return result

def assemble(cache,root=ROOT,download=False):
    root=Path(root);cache=Path(cache);blobs={}
    original={p:sha(read(root/p)) for p in INPUTS}
    members,nodes=root_source(cache,download)
    selected=supplements(root,blobs,cache)
    packages=[]
    for node in nodes:
        raw=fetch(cache,node) if download else load_cache(cache,node)
        record=package_record(node,archive(raw,node['name'],node['version']),blobs,selected.get(node['id']))
        packages.append(bind_supplement(record,selected.get(node['id']),blobs))
    old=strict(read(root/'sbom/c2pa/manifest.json'))
    native=[{'profile':r['profile'],'sha256':r['native']['sha256'],
             'native_path':r['wheel_member'],'wheel':r['wheel'],'wheel_sha256':next(w['sha256'] for w in old['wheels'] if w['filename']==r['wheel'])}
            for r in old['sdk_upstream']['native_matches']]
    need({p:sha(read(root/p)) for p in INPUTS}==original)
    labels=strict(read(root/'sbom/c2pa-native/native-labels.json'))
    need(set(labels)=={'format','captured_at','observations'} and labels['format']=='c2pa-native-embedded-registry-labels/v1')
    result={'profile':PROFILE,'upstream_commit_declared':COMMIT,'inputs':original,
            'native_artifacts':native,'native_source_label_observations':labels['observations'],'packages':packages,
            'sources':sorted([{'path':p,'sha256':sha(raw),'bytes':len(raw)} for p,raw in blobs.items()],key=lambda r:r['path']),
            'coverage':{'published_package_lock_available':True,'complete_published_lock_graph':True,
                        'exact_build_lock_available':False,'complete_native_dependency_graph':False},
            'unresolved':UNRESOLVED.copy(),
            'claims':CLAIMS.copy()}
    return result,blobs


def verify(root=ROOT,cache=None,native_cache=None):
    root=Path(root);data=strict(read(root/MANIFEST,32*1024**2))
    need(type(data) is dict and set(data)=={'profile','upstream_commit_declared','inputs','native_artifacts','native_source_label_observations','packages','sources','coverage','unresolved','claims'})
    need(data['unresolved']==UNRESOLVED)
    need(data['profile']==PROFILE and data['upstream_commit_declared']==COMMIT and data['claims']==CLAIMS)
    need(canonical(data['claims'])==canonical(CLAIMS))
    need(data['inputs']=={p:sha(read(root/p)) for p in INPUTS})
    need(canonical(data['coverage'])==canonical({'published_package_lock_available':True,'complete_published_lock_graph':True,'exact_build_lock_available':False,'complete_native_dependency_graph':False}))
    blobs={}
    for row in data['sources']:
        need(type(row) is dict and set(row)=={'path','sha256','bytes'} and re.fullmatch(STORE+r'[a-f0-9]{64}\.txt',row['path']))
        need(row['path'] not in blobs and row['sha256']==Path(row['path']).stem)
        raw=read(root/row['path']);need(sha(raw)==row['sha256'] and len(raw)==row['bytes']);blobs[row['path']]=raw
    root_pkg=next(p for p in data['packages'] if p['id']==ROOT_NAME+'@'+VERSION)
    lock=next(m for m in root_pkg['retained_members'] if m['member']=='Cargo.lock')
    need(sha(blobs[lock['path']])==LOCK_SHA)
    nodes=lock_graph(blobs[lock['path']]);need(len(nodes)==len(data['packages']))
    expected=[]
    rebuilt_blobs={}
    selected=supplements(root,rebuilt_blobs)
    for node,package in zip(nodes,data['packages']):
        need(node['id']==package['id'])
        contents={}
        for member in package['retained_members']:
            need(set(member)=={'member','path','sha256','bytes'});safe(member['member']);need(member['member'] not in contents)
            raw=blobs[member['path']];need(sha(raw)==member['sha256'] and len(raw)==member['bytes']);contents[member['member']]=raw
        record=package_record(node,contents,rebuilt_blobs,selected.get(node['id']))
        expected.append(bind_supplement(record,selected.get(node['id']),rebuilt_blobs))
    need(canonical(expected)==canonical(data['packages']) and rebuilt_blobs==blobs)
    need(set(p.relative_to(root).as_posix() for p in (root/'sbom/c2pa-native/sources').iterdir())==set(blobs))
    old=strict(read(root/'sbom/c2pa/manifest.json'))
    native=[{'profile':r['profile'],'sha256':r['native']['sha256'],'native_path':r['wheel_member'],'wheel':r['wheel'],
             'wheel_sha256':next(w['sha256'] for w in old['wheels'] if w['filename']==r['wheel'])} for r in old['sdk_upstream']['native_matches']]
    need(data['native_artifacts']==native)
    labels=strict(read(root/'sbom/c2pa-native/native-labels.json'))
    need(data['native_source_label_observations']==labels['observations'])
    identities={n['id'] for n in nodes}
    for row in labels['observations']:
        need(set(row)=={'profile','native_sha256','package_ids','observation','exhaustive','binary_executed'})
        need(row['exhaustive'] is False and row['binary_executed'] is False
             and row['observation']=='embedded_registry_source_version_labels_only'
             and sorted(set(row['package_ids']))==row['package_ids'] and set(row['package_ids'])<=identities
             and any(n['profile']==row['profile'] and n['sha256']==row['native_sha256'] for n in native))
    if cache is not None:
        rebuilt,replayed=assemble(cache,root)
        need(canonical(rebuilt)==canonical(data) and replayed==blobs)
    if native_cache is not None:need(native_labels(native_cache,root)==labels['observations'])
    return {'pass':True,'profile':PROFILE,'packages':len(nodes),'dependency_edges':sum(len(n['dependency_ids']) for n in nodes),
            'retained_sources':len(blobs),'actual_archive_replay':cache is not None,
            'native_labels_replayed':native_cache is not None,'native_build_graph_proven':False,'permission_cleared':False,'claims':CLAIMS}
