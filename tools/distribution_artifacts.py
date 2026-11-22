"""Actual-artifact SBOMs with closed source adapters; attestations are not approval."""
from datetime import datetime,timezone
from functools import wraps
import base64
import hashlib
import importlib
import json
import os
from pathlib import Path
from urllib.parse import urlsplit
import re
import shutil
import subprocess
import sys
import tempfile
import uuid

from tools.artifact_evidence_io import Capture,PrivateInputError,OutputCommitUncertain,need,sha,encoded
from tools.dependency_policy import ROUTES,evaluate
from tools.artifact_process import run_worker

ROOT=Path(__file__).absolute().parents[1]
PROFILE='artifact-source-sbom-binding/v1'
SPDX_TYPE='https://spdx.dev/Document/v2.3'
REPO='knwvmbrr/aitrust-id'
SIGNER=REPO+'/.github/workflows/artifact-sbom.yml'
IDENTITY='https://github.com/'+SIGNER+'@refs/heads/main'
PRODUCERS=('tools/distribution_artifacts.py','tools/artifact_evidence_io.py','scripts/distribution-artifact.py','tools/artifact_process.py')
SHA=re.compile('[a-f0-9]{64}')
COMMIT=re.compile('[a-f0-9]{40}')
MAX_PACKET=16_000_000
MAX_NODES=16384
MAX_EDGES=30000
COMMON=('LICENSE','NOTICE','eval/dependency-policy.json','tools/dependency_policy.py','scripts/worker_process.py',
 '.github/workflows/artifact-sbom.yml','docs/distribution-artifact-sbom.md',*PRODUCERS)
NPM_FILES=('package-lock.json','site/package-lock.json')
WEB_EVIDENCE=('sbom/assets/notices.json','sbom/nested-runtime/pyodide-wasm-release.json',
 'sbom/nested-runtime/manifest.json','sbom/reviews/pyodide-js/manifest.json','sbom/reviews/zlib-runtime/manifest.json')
CONSUMERS={
 'ps-source':('tools/ps_source_distribution.py','scripts/export-ps-source.py'),
 'source-snapshot':('scripts/source_snapshot.py','scripts/build-source-snapshot.py'),
 'web-checker':('site/package.json','site/scripts/prepare.mjs','tools/web_distribution.py'),
 'ios-app':('scripts/build-ios-project.py','scripts/verify-ios-archive.py','mobile/ios/Source/Assets.swift'),
 'android-app':('scripts/android-share-build.py','mobile/android/AndroidManifest.xml'),
 'gateway-linux-amd64':('services/gateway/Dockerfile','services/gateway/requirements.lock'),
 'evaluator-linux-amd64':('services/evaluator/Dockerfile','services/evaluator/requirements.lock'),
 'anonymizer-linux-amd64':('services/anonymizer/Dockerfile','services/anonymizer/requirements.lock'),
 'nli-linux-x86_64':('research/nli/backend.py','research/nli/requirements-linux.lock'),
 'nli-macos-arm64':('research/nli/backend.py','research/nli/requirements-mac.lock'),
 'c2pa-linux-x86_64':('scripts/inspect-manifest.py','tools/manifest_inspection.py'),
 'c2pa-macos-arm64':('scripts/inspect-manifest.py','tools/manifest_inspection.py'),
 'mcp-stdio':('scripts/ai-tools-server.py','integrations/mcp/requirements.lock'),
 'node-build-tools':('package.json','site/package.json'),
}
need(set(CONSUMERS)==set(ROUTES))



def boundary(function):
    @wraps(function)
    def safe(*args,**kwargs):
        try:return function(*args,**kwargs)
        except OutputCommitUncertain:raise
        except Exception:raise PrivateInputError('Artifact evidence unavailable.')from None
    return safe


def parse(raw):
    need(type(raw)is bytes and 0<len(raw)<=MAX_PACKET)
    def unique(pairs):
        d={}
        for k,v in pairs:need(k not in d);d[k]=v
        return d
    def bad(_):raise PrivateInputError('Artifact evidence unavailable.')
    return json.loads(raw.decode('utf-8','strict'),object_pairs_hook=unique,parse_constant=bad)


def path_name(name):
    need(type(name)is str and 0<len(name)<=500 and name.isascii() and not name.startswith('/')
         and re.fullmatch('[A-Za-z0-9_./@+~-]+',name)is not None
         and all(p not in ('','.','..')for p in name.split('/')))
    return name


def label(value,limit=500):
    need(type(value)is str and 0<len(value)<=limit and '\0'not in value and not any(ord(c)<32 for c in value))
    return value


class Graph:
    def __init__(self,route,root,capture):
        need(route in ROUTES);self.route=route;self.root=Path(root);self.c=capture
        self.inputs={};self.raws={};self.nodes={};self.edges=set();self.gaps=[];self.commit=None
    def read(self,path):
        path_name(path)
        need(not any(p=='.git'or p=='.env'or p.startswith('.env.')for p in path.split('/'))or path=='deploy/.env.example')
        if path not in self.raws:
            raw=self.c.read(self.root/path,16_000_000,private=False)
            if path in self.inputs:need(self.inputs[path]==sha(raw))
            self.raws[path]=raw;self.inputs[path]=sha(raw)
        return self.raws[path]
    def data(self,path):return parse(self.read(path))
    def node(self,key,name,version,origin,evidence,checksums=(),declared=None,details=None):
        label(key);label(name);need(version is None or type(version)is str and len(version)<=150)
        need(len(self.nodes)<MAX_NODES and key not in self.nodes)
        need(evidence in self.inputs and len(checksums)<=8)
        checked=[]
        for algorithm,digest in checksums:
            size={'SHA1':40,'SHA256':64,'SHA384':96,'SHA512':128}.get(algorithm)
            need(size is not None and type(digest)is str and re.fullmatch('[a-f0-9]{'+str(size)+'}',digest))
            checked.append({'algorithm':algorithm,'checksumValue':digest})
        need(declared is None or type(declared)is str and len(declared)<=4096 and not any(ord(c)<32 for c in declared))
        row={'key':key,'name':name,'version':version,'origin':origin,'evidence':evidence,
             'checksums':checked,'license_declaration':declared,'permission_decision':'unreviewed'}
        if details is not None:need(type(details)is dict);row['details']=details
        self.nodes[key]=row
    def edge(self,a,b):
        need(a in self.nodes and b in self.nodes and len(self.edges)<MAX_EDGES)
        self.edges.add((a,b))
    def npm(self,path):
        data=self.data(path);need(type(data)is dict and data.get('lockfileVersion')==3)
        packages=data.get('packages');need(type(packages)is dict and 0<len(packages)<=3000)
        keys={}
        for name,row in sorted(packages.items()):
            need(type(row)is dict)
            if not name:continue
            path_name(name);version=row.get('version');label(version,150)
            key='npm:'+path+':'+name;integrity=row.get('integrity');checks=[]
            need(type(integrity)is str and re.fullmatch('sha(256|384|512)-[A-Za-z0-9+/]+={0,2}',integrity))
            algorithm,value=integrity.split('-',1);digest=base64.b64decode(value,validate=True).hex()
            checks=[(algorithm.upper(),digest)]
            url=urlsplit(row.get('resolved',''))
            need(url.scheme=='https'and url.hostname=='registry.npmjs.org'and url.port is None and not url.username and not url.password and not url.query and not url.fragment)
            self.node(key,name.rsplit('node_modules/',1)[-1],version,'npm-lock',path,checks,row.get('license'),
                      {'optional':row.get('optional')is True,'dev':row.get('dev')is True,'resolved':row.get('resolved')})
            keys[name]=key
        for name,row in packages.items():
            if not name:continue
            for field in ('dependencies','optionalDependencies'):
                deps=row.get(field,{})
                need(type(deps)is dict and len(deps)<=500)
                for dep in deps:
                    label(dep,200);candidate=name+'/node_modules/'+dep
                    while candidate not in keys:
                        parent=candidate.rsplit('/node_modules/',1)[0]
                        candidate=('node_modules/'+dep)if '/node_modules/'not in parent else parent.rsplit('/node_modules/',1)[0]+'/node_modules/'+dep
                        if candidate=='node_modules/'+dep:break
                    if candidate in keys:self.edge(keys[name],keys[candidate])
                    else:self.gaps.append('npm_locked_dependency_target_unavailable')
    def python_lock(self,path):
        text=self.read(path).decode('utf-8','strict');text=re.sub(r'\\\n\s*',' ',text)
        count=0
        for line in text.splitlines():
            line=line.strip()
            if not line or line.startswith('#'):continue
            match=re.fullmatch(r'([A-Za-z0-9_.-]+)==([^\s;]+)(?:\s+--hash=sha256:[a-f0-9]{64})+(?:\s*#.*)?',line)
            need(match is not None);name,version=match.group(1,2)
            hashes=re.findall('--hash=sha256:([a-f0-9]{64})',line);need(0<len(hashes)<=512 and len(set(hashes))==len(hashes))
            # All alternatives are retained; they are not falsely called installed.
            self.node('python:'+path+':'+name.lower().replace('_','-'),name,version,'hashed-python-lock',path,
                      details={'accepted_artifact_sha256':hashes,'installed_artifact_selected':False})
            count+=1
        need(count>0);self.gaps.append('python_lock_does_not_identify_all_installed_vendored_code')
    def web_assets(self):
        for path in WEB_EVIDENCE:self.read(path)
        a=self.data('sbom/assets/notices.json')
        for row in a['assets']:
            name=path_name(row['path']);need(SHA.fullmatch(row['sha256'])and type(row['bytes'])is int and row['bytes']>0)
            self.node('asset:'+name,name,None,'retained-asset-observation','sbom/assets/notices.json',[('SHA256',row['sha256'])],
                      details={'bytes':row['bytes'],'notices':row['notices']})
        for row in a['runtime_members']:
            self.node('runtime:'+row['name'],row['name'],a['runtime_origin']['version'],'retained-runtime-observation','sbom/assets/notices.json',[('SHA256',row['sha256'])])
        self.gaps.extend(['compiled_runtime_embedded_coverage_unreviewed','distribution_notice_source_obligations_not_complete'])
    def image(self):
        path='eval/dependencies/runtime-sbom.json';registry=self.data(path);role=self.route.split('-linux-',1)[0]
        row=next(x for x in registry['images']if x['role']==role);docpath=path_name(row['artifact']);raw=self.read(docpath)
        need(sha(raw)==row['sha256']);doc=parse(raw);need(doc.get('spdxVersion')=='SPDX-2.3')
        packages=doc['packages'];need(type(packages)is list and 0<len(packages)<=2000)
        by_id={}
        for p in packages:
            k='image:'+p['SPDXID'];self.node(k,p['name'],p.get('versionInfo'),'observed-image-spdx',docpath,
                [(v['algorithm'],v['checksumValue'])for v in p.get('checksums',[])if v['algorithm']in ('SHA1','SHA256','SHA384','SHA512')],p.get('licenseDeclared'),
                {'image_id':row['image_id'],'manifest_digest':row['manifest_digest']})
            need(p['SPDXID']not in by_id);by_id[p['SPDXID']]=k
        for rel in doc.get('relationships',[]):
            if rel['relationshipType']=='DEPENDS_ON'and rel['spdxElementId']in by_id and rel['relatedSpdxElement']in by_id:self.edge(by_id[rel['spdxElementId']],by_id[rel['relatedSpdxElement']])
        self.gaps.extend(['installed_vendor_license_source_actions_unreviewed','existing_image_inventory_not_itself_an_artifact_attestation'])
    def nli(self):
        platform='linux'if self.route.startswith('nli-linux')else'mac'
        lock='research/nli/requirements-'+platform+'.lock';self.python_lock(lock)
        provenance='research/nli/wheel-provenance-'+platform+'.json'
        for row in self.data(provenance):
            self.node('wheel:'+row['wheel'],row['name'],row['version'],'selected-wheel-provenance',provenance,[('SHA256',row['sha256'])],row.get('declared_license'),{'notice_observations':row.get('license_members',row.get('license_files',[]))})
        assets='research/nli/assets.json'
        for row in self.data(assets)['files']:
            self.node('model:'+row['name'],row['name'],None,'pinned-model-asset',assets,[('SHA256',row['sha256'])])
        self.read('sbom/reviews/nli/manifest.json');self.gaps.extend(['model_license_scope_not_a_truth_claim','native_wheel_obligations_remain_unresolved']);self.obligations('nli')
    def c2pa(self):
        path='sbom/c2pa/manifest.json';doc=self.data(path);profile='linux-x86_64-cp313'if'linux'in self.route else'darwin-arm64-cp312'
        for row in doc['wheels']:
            if profile not in row['profiles']:continue
            p=row['declaration'];self.node('wheel:'+row['filename'],p['name'],p['version'],'selected-sdk-wheel',path,[('SHA256',row['sha256'])],p.get('license_declared'),{'notice_source_records':row['retained']})
        self.read('eval/dependencies/c2pa-inspection.json');self.gaps.append('native_rust_dependency_and_source_notice_graph_unresolved');self.obligations('c2pa')
    def obligations(self,kind):
        prefix='sbom/'+kind+'-native';path=prefix+'/manifest.json'
        try:os.lstat(self.root/path)
        except FileNotFoundError:return
        # The optional exact-source foundation is used only by this scope. Its
        # absence cannot poison PS or another distribution's graph.
        module=importlib.import_module('tools.'+kind+'_native_obligations')
        data=self.data(path);need(data.get('profile')==kind+'-native-dependency-observations/v1')
        report=module.verify(root=self.root);need(type(report)is dict and report.get('pass')is True)
        need(type(data['inputs'])is dict and len(data['inputs'])<=64)
        for name,digest in data['inputs'].items():need(SHA.fullmatch(digest)and sha(self.read(name))==digest)
        implementation='tools/'+kind+'_native_obligations.py'
        need(implementation in data['inputs']and self.read(implementation)==self.c.read(ROOT/implementation,16_000_000,private=False))
        need(type(data['sources'])is list and len(data['sources'])<=10000)
        total=0
        for source in data['sources']:
            need(type(source)is dict and set(source)=={'path','sha256','bytes'})
            name=path_name(source['path']);digest=source['sha256']
            need(name.startswith(prefix+'/')and SHA.fullmatch(digest)and type(source['bytes'])is int and 0<=source['bytes']<=16_000_000)
            need(source['bytes']>0 or digest==sha(b''))
            total+=source['bytes'];need(total<=64_000_000)
            # The foundation just verified these sequentially, so no thousands
            # of live descriptors are accumulated. Packet replay verifies again.
            need(name not in self.inputs or self.inputs[name]==digest);self.inputs[name]=digest
        need(type(data['claims'])is dict and all(type(v)is bool and v is False for v in data['claims'].values()))
        packages=data['packages'];need(type(packages)is list and 0<len(packages)<=3000)
        labels=set()
        if kind=='c2pa':
            platform='linux-x86_64'if'linux'in self.route else'darwin-arm64'
            selected=[v for v in data['native_source_label_observations']if v['profile']==platform]
            need(len(selected)==1 and selected[0]['exhaustive']is False and selected[0]['binary_executed']is False)
            labels=set(selected[0]['package_ids'])
        keys={}
        for row in packages:
            key=kind+'-native:'+row['id'];keys[row['id']]=key
            self.node(key,row['name'],row['version'],'published-native-source-graph',path,
                [('SHA256',row['archive_sha256'])]if'archive_sha256'in row else (),row.get('license_declared'),
                {'notice_paths':row['notice_paths'],'term_actions':row['term_actions'],
                 'source_identity':row.get('source_identity'),'platforms':row.get('platforms'),
                 'native_source_label_observed':row['id']in labels,'compiled_closure_established':False,'published_source_graph_only':True})
        for row in packages:
            for target in row['dependency_ids']:self.edge(keys[row['id']],keys[target])
        self.gaps.append(kind+'_published_source_graph_is_not_a_complete_compiled_dependency_claim')

    def committed_tree(self):
        head=run_worker(['git','--no-replace-objects','-C',str(self.root),'rev-parse','--verify','HEAD^{commit}'],input=b'',timeout=20,output_limit=100)
        need(head.returncode==0);self.commit=head.stdout.decode('ascii').strip();need(COMMIT.fullmatch(self.commit))
        result=run_worker(['git','--no-replace-objects','-C',str(self.root),'ls-tree','-r','-z','--full-tree',self.commit],input=b'',timeout=20,output_limit=2_000_000)
        need(result.returncode==0);rows=result.stdout.split(b'\0');need(rows[-1:]==[b''] and len(rows)-1<=MAX_NODES)
        evidence='scripts/source_snapshot.py';self.read(evidence)
        for row in rows:
            if not row:continue
            meta,name=row.split(b'\t',1);mode,kind,oid=meta.decode('ascii').split(' ');name=name.decode('ascii');path_name(name)
            need(mode in ('100644','100755')and kind=='blob'and COMMIT.fullmatch(oid))
            self.node('git:'+name,name,None,'committed-git-blob',evidence,details={'git_blob_oid':oid,'git_object_format':'sha1','mode':mode})
        self.gaps.append('whole_repository_source_terms_need_per_component_review')
    def finish(self):
        for path in (*COMMON,*CONSUMERS[self.route]):self.read(path)
        for path in (*PRODUCERS,'tools/dependency_policy.py','scripts/worker_process.py'):
            need(self.read(path)==self.c.read(ROOT/path,16_000_000,private=False))
        if self.route=='ps-source':
            from tools.dependency_policy import require_route
            for row in require_route(self.route,self.root)['files']:
                need(sha(self.read(row['path']))==row['sha256'])
                self.node('source:'+row['path'],row['path'],None,'admitted-source-member',row['path'],[('SHA256',row['sha256'])])
        elif self.route=='source-snapshot':self.committed_tree()
        elif self.route in ('web-checker','ios-app','android-app'):
            self.npm('site/package-lock.json');self.web_assets()
            if self.route!='web-checker':self.gaps.append('unbundled_platform_sdk_rights_are_separate_prerequisites')
        elif self.route.endswith('-linux-amd64'):self.image()
        elif self.route.startswith('nli-'):self.nli()
        elif self.route.startswith('c2pa-'):self.c2pa()
        elif self.route=='mcp-stdio':self.python_lock('integrations/mcp/requirements.lock')
        elif self.route=='node-build-tools':
            for path in NPM_FILES:self.npm(path)
            self.read('sbom/native/manifest.json');self.gaps.append('all_native_optional_platform_obligations_unreviewed')
        self.c.check()
        return {'profile':'declared-and-observed-distribution-graph/v1','route':self.route,
            'nodes':[self.nodes[k]for k in sorted(self.nodes)],
            'relationships':[{'from':a,'to':b,'type':'DEPENDS_ON'}for a,b in sorted(self.edges)],
            'source_sha256':dict(sorted(self.inputs.items())),'committed_tree':self.commit,'coverage_gaps':sorted(set(self.gaps)),
            'complete_embedded_dependency_coverage':False,'license_clearance':False}


@boundary
def graph(route,root=ROOT):
    try:
        with Capture()as c:return Graph(route,root,c).finish()
    except (ValueError,OSError,KeyError,TypeError,RecursionError,UnicodeError):
        raise PrivateInputError('Artifact evidence unavailable.')from None


def spdx(route,artifact,graph,created):
    need(re.fullmatch(r'\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ',created))
    stamp=datetime.fromisoformat(created.replace('Z','+00:00'));need(stamp<=datetime.now(timezone.utc))
    seed=sha(encoded({'route':route,'artifact':artifact,'graph':graph,'created':created}))
    packages=[{'SPDXID':'SPDXRef-Artifact','name':'aitrust-'+route,'downloadLocation':'NOASSERTION',
       'filesAnalyzed':False,'checksums':[{'algorithm':'SHA256','checksumValue':artifact['sha256']}],
       'licenseConcluded':'NOASSERTION','licenseDeclared':'NOASSERTION','copyrightText':'NOASSERTION',
       'comment':'Exact supplied artifact bytes. Source-derived dependencies below are declared/observed evidence, not a complete embedded-content or permission claim.'}]
    ordered=sorted(graph['nodes'],key=lambda n:n['key'])
    need(len({n['key']for n in ordered})==len(ordered))
    ids={n['key']:'SPDXRef-Component-'+str(i).zfill(5)for i,n in enumerate(ordered,1)}
    relationships=[{'spdxElementId':'SPDXRef-DOCUMENT','relationshipType':'DESCRIBES','relatedSpdxElement':'SPDXRef-Artifact'}]
    for n in graph['nodes']:
        p={'SPDXID':ids[n['key']],'name':n['name'],'downloadLocation':'NOASSERTION','filesAnalyzed':False,
           'licenseConcluded':'NOASSERTION','licenseDeclared':'NOASSERTION','copyrightText':'NOASSERTION',
           'comment':'Evidence origin: '+n['origin']+'; evidence file: '+n['evidence']+'. Metadata is not permission.'}
        if n['version']is not None:p['versionInfo']=n['version']
        if n['checksums']:p['checksums']=n['checksums']
        if n['origin']=='committed-git-blob':
            p['sourceInfo']='Git blob object identity (includes Git object header; not a plain file checksum): '+n['details']['git_blob_oid']+'; mode '+n['details']['mode']
        packages.append(p);relationships.append({'spdxElementId':'SPDXRef-Artifact','relationshipType':'OTHER','relatedSpdxElement':p['SPDXID'],'comment':'Associated source evidence; not a containment claim.'})
    for edge in graph['relationships']:relationships.append({'spdxElementId':ids[edge['from']],'relationshipType':'DEPENDS_ON','relatedSpdxElement':ids[edge['to']]})
    return {'spdxVersion':'SPDX-2.3','dataLicense':'CC0-1.0','SPDXID':'SPDXRef-DOCUMENT',
      'name':'AI Trust ID '+route+' artifact/source evidence','documentNamespace':'urn:uuid:'+str(uuid.uuid5(uuid.NAMESPACE_OID,seed)),
      'creationInfo':{'created':created,'creators':['Tool: AITrust-ID-artifact-sbom-1.0.0']},
      'comment':'Source graph SHA256 '+sha(encoded(graph))+'; source-input set SHA256 '+sha(encoded(graph['source_sha256']))+'; complete embedded coverage and license clearance are not asserted.',
      'documentDescribes':['SPDXRef-Artifact'],'packages':packages,'relationships':relationships}


@boundary
def prepare(route,artifact,source_commit,root=ROOT,created=None):
    need(type(source_commit)is str and COMMIT.fullmatch(source_commit));need(route in ROUTES)
    created=created or datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z')
    try:
        with Capture()as c:
            g=Graph(route,root,c).finish();value=c.artifact(artifact)
            # The actually admitted source route is also checked against canonical contents.
            if route=='ps-source':
                from tools.ps_source_distribution import verify_file
                verify_file(artifact,root)
            if route=='source-snapshot':need(g['committed_tree']==source_commit)
            sbom=spdx(route,value,g,created);policy=evaluate(route,root)
            record={'profile':PROFILE,'route':route,'source_commit':source_commit,'artifact':value,'created':created,
                'graph':g,'spdx':sbom,'spdx_sha256':sha(encoded(sbom)+b'\n'),'graph_sha256':sha(encoded(g)),
                'policy':policy,'artifact_format_verified':route=='ps-source','attestation_verified':False,'release_authorized':False,
                'license_clearance':False,'complete_project_obligations':False}
            need(len(encoded(record))<=MAX_PACKET);c.check();return record
    except (ValueError,OSError,KeyError,TypeError,RecursionError,UnicodeError):raise PrivateInputError('Artifact evidence unavailable.')from None


@boundary
def verify_packet(record,artifact,route,source_commit,root=ROOT):
    need(type(record)is dict and set(record)=={'profile','route','source_commit','artifact','created','graph','spdx','spdx_sha256','graph_sha256','policy','artifact_format_verified','attestation_verified','release_authorized','license_clearance','complete_project_obligations'})
    need(record['route']==route and record['source_commit']==source_commit)
    expected=prepare(route,artifact,source_commit,root,record['created'])
    need(encoded(expected)==encoded(record));return expected


@boundary
def save_packet(record,output):
    with Capture()as c:c.save(output,record,MAX_PACKET)


GH_CAPTURE = """import os,resource,sys
resource.setrlimit(resource.RLIMIT_CORE,(0,0))
resource.setrlimit(resource.RLIMIT_FSIZE,(16000000,16000000))
fd=os.open(sys.argv[1],os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
os.dup2(fd,1)
if fd!=1:os.close(fd)
os.execvp('gh',['gh',*sys.argv[2:]])
"""


@boundary
def run_attestation(argv,timeout=60,output_limit=16_000_000):
    need(type(argv)is list and argv[:3]==['gh','attestation','verify']and len(argv)>3 and timeout==60 and output_limit==16_000_000)
    destination=Path(argv[3]).parent/'verification-result.json'
    outcome=run_worker([sys.executable,'-I','-S','-B','-c',GH_CAPTURE,str(destination),*argv[1:]],input=b'',timeout=60,output_limit=4096)
    if outcome.returncode:return subprocess.CompletedProcess(argv,outcome.returncode,b'',b'')
    with Capture()as captured:
        raw=captured.read(destination,16_000_000);captured.check()
    return subprocess.CompletedProcess(argv,0,raw,b'')



@boundary
def publish_bound(record,artifact,route,source_commit,output,root=ROOT,spdx_only=False):
    def stable():return verify_packet(record,artifact,route,source_commit,root)
    with Capture()as c:
        stable()
        c.save(output,record['spdx']if spdx_only else record,MAX_PACKET,prepublish=stable)
        stable()  # Any later failure is explicitly uncertain because publication occurred.


@boundary
def verify_attestation(record,artifact,sbom,bundle,trusted_root,route,source_commit,root=ROOT,runner=run_attestation):
    record=verify_packet(record,artifact,route,source_commit,root)
    with Capture()as c:
        expected=encoded(record['spdx'])+b'\n'
        need(c.read(sbom,MAX_PACKET,private=False)==expected)
        bundle_raw=c.read(bundle,MAX_PACKET,private=False);trust_raw=c.read(trusted_root,5_000_000,private=False)
        # Roots are separately selected. No carried artifact/packet can choose verifier identity.
        with tempfile.TemporaryDirectory(prefix='aitrust-artifact-verify-')as temp:
            stage=Path(temp).resolve();stage.chmod(0o700)
            need(shutil.disk_usage(stage).free-record['artifact']['bytes']>=2*1024**3)
            with(stage/'artifact.bin').open('xb')as stream:
                os.chmod(stage/'artifact.bin',0o600);need(c.artifact(artifact,copy_to=stream)==record['artifact'])
            for name,raw in [('bundle.json',bundle_raw),('trusted-root.jsonl',trust_raw)]:
                with(stage/name).open('xb')as stream:os.chmod(stage/name,0o600);stream.write(raw)
            argv=['gh','attestation','verify',str(stage/'artifact.bin'),'--bundle',str(stage/'bundle.json'),
              '--custom-trusted-root',str(stage/'trusted-root.jsonl'),'--repo',REPO,'--cert-identity',IDENTITY,
              '--cert-oidc-issuer','https://token.actions.githubusercontent.com','--source-digest',record['source_commit'],
              '--source-ref','refs/heads/main','--deny-self-hosted-runners','--predicate-type',SPDX_TYPE,'--format','json',
              '--jq','map({verificationResult: .verificationResult})']
            result=runner(argv,timeout=60,output_limit=16_000_000)
            need(result.returncode==0);verified=parse(result.stdout);need(type(verified)is list and 0<len(verified)<=10)
            for result in verified:
                v=result['verificationResult'];statement=v['statement']
                need(v.get('verifiedTimestamps')and statement['predicateType']==SPDX_TYPE and
                     encoded(statement['predicate'])==encoded(record['spdx'])and any(s.get('digest')=={'sha256':record['artifact']['sha256']}for s in statement['subject']))
            with Capture()as staged:
                need(staged.artifact(stage/'artifact.bin')==record['artifact'])
                need(staged.read(stage/'bundle.json',MAX_PACKET)==bundle_raw and staged.read(stage/'trusted-root.jsonl',5_000_000)==trust_raw)
                staged.check()
        c.check()
    verify_packet(record,artifact,route,source_commit,root)
    return {'state':'VERIFIED','attestation_verified':True,'route':record['route'],
      'artifact_sha256':record['artifact']['sha256'],'spdx_sha256':record['spdx_sha256'],
      'bundle_sha256':sha(bundle_raw),'trusted_root_sha256':sha(trust_raw),'source_commit':record['source_commit'],
      'release_authorized':False,'license_clearance':False}


@boundary
def authorize_release(record,artifact,sbom,bundle,trusted_root,route,source_commit,root=ROOT,runner=run_attestation):
    """Actual managed-release consumer: authenticity alone cannot override policy."""
    current=verify_packet(record,artifact,route,source_commit,root)
    need(current['policy'].get('release_allowed')is True)
    verified=verify_attestation(current,artifact,sbom,bundle,trusted_root,route,source_commit,root,runner)
    # Repeat current graph/policy and input identity after the verifier returns.
    verify_packet(current,artifact,route,source_commit,root)
    return {**verified,'state':'AUTHORIZED','release_authorized':True,'policy_admitted':True}
