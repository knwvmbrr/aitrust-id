"""Actual-artifact SBOMs with closed source adapters; attestations are not approval."""
from datetime import datetime,timezone
from functools import wraps
import base64
import hashlib
import importlib
import io
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
 'source-snapshot':('scripts/source_snapshot.py','scripts/source_snapshot_v2.py','scripts/source_snapshot_v3.py','scripts/build-source-snapshot.py','scripts/verify-source-provenance.py',
  'tools/source_snapshot_binding.py','tools/source_release_policy.py','tools/source_release_policy_v2.py',
  'eval/dependencies/source-snapshot-release.json','eval/dependencies/source-snapshot-release-v2.json',
  'tools/source_release_policy_v3.py','eval/dependencies/source-snapshot-additions-v3.json',
  'tools/source_release_policy_v4.py','eval/dependencies/source-snapshot-additions-v4.json',
  'tools/source_release_policy_v5.py','eval/dependencies/source-snapshot-additions-v5.json',
  'tools/source_snapshot_admission.py','tools/source_snapshot_managed.py','scripts/verify-managed-source.py',
  'docs/source-snapshot-managed-consumer.md'),
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
 'mcp-stdio':('scripts/ai-tools-server.py','integrations/mcp/requirements.lock',
  'tools/mcp_distribution.py','scripts/mcp-distribution.py','tools/mcp_runtime_obligations.py',
  'scripts/collect-mcp-notices.py','sbom/mcp-runtime/targets.json','sbom/mcp-runtime/manifest.json',
  'sbom/mcp-runtime/source-inputs.json','sbom/mcp-runtime/obligations.json.gz',
  'sbom/mcp-runtime/THIRD-PARTY-NOTICES.txt','sbom/mcp-runtime/SCHEMA-ATTRIBUTION.txt',
  'tools/mcp_release_policy.py','eval/dependencies/mcp-runtime-release.json',
  'tools/mcp_managed_release.py','scripts/install-managed-mcp.py','docs/mcp-managed-release.md',
  'runs/2026-11-22-mcp-retained-grants-distinct-review.json',
  'runs/2026-11-22-mcp-cffi-rust-notice-facts-distinct-review.json'),
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
    def __init__(self,route,root,capture,artifact_target=None):
        need(route in ROUTES);self.route=route;self.root=Path(root);self.c=capture
        self.inputs={};self.raws={};self.nodes={};self.edges=set();self.gaps=[];self.commit=None
        self.artifact_target=artifact_target
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

    def mcp(self):
        from tools import mcp_distribution as m
        profile_raw,profile=m.load(self.c,self.root)
        self.read(m.PROFILE_FILE)
        need(sha(profile_raw)==self.inputs[m.PROFILE_FILE])
        for path in sorted(m.SOURCES):
            raw=self.read(path)
            declared='CC-BY-4.0'if path=='spec/assertion.schema.json'else 'Unicode-3.0'if path=='protocol/unicode15-data.json'else None
            self.node('mcp-source:'+path,path,None,'mcp-project-source-or-notice',path,[('SHA256',sha(raw))],declared)
        self.read('sbom/mcp-runtime/obligations.json.gz')
        data=m.read_obligations(self.c,self.root)
        evidence,_=m.supplement_evidence(self.root)
        for row in evidence:
            need(row['path']not in self.inputs or self.inputs[row['path']]==row['sha256'])
            self.inputs[row['path']]=row['sha256']
        source_keys={}
        for package in data['source_packages']:
            key='mcp-native-source:'+package['id'];source_keys[package['id']]=key
            self.node(key,package['id'],None,'exact-publisher-source-notice-observation',
                'sbom/mcp-runtime/obligations.json.gz',[('SHA256',package['archive_sha256'])],package['selected_grant'],
                {'official_source':package['url'],'source_archive_bytes':package['archive_bytes'],
                 'notice_sha256':package['notice_sha256'],'complete_compiled_closure':False})
        ffi=self.data('sbom/cffi-libffi/manifest.json')['packages'][0]
        ffi_key='mcp-native-source:libffi@3.4.6'
        self.node(ffi_key,'libffi','3.4.6','publisher-static-build-recipe-and-symbol-correspondence',
            'sbom/cffi-libffi/manifest.json',[('SHA256',ffi['source_identity']['archive_sha256'])],'MIT',
            {'source_identity':ffi['source_identity'],'notice_sha256':data['libffi_evidence']['notice_sha256'],
             'complete_compiled_closure':False,'publisher_attestation_verified':False})
        rust=self.data('sbom/mcp-rust-stdlib/manifest.json')
        rust_keys={}
        for commit in rust['source_commits']:
            key='mcp-rust-runtime-source:'+commit;rust_keys[commit]=key
            self.node(key,'Rust standard-library source',commit,'native-source-path-and-scoped-publisher-grant-observation',
                'sbom/mcp-rust-stdlib/manifest.json',declared='MIT OR Apache-2.0',
                details={'source_commit_observed':commit,'scoped_runtime_exceptions':rust['grant_scopes'],
                         'notice_sha256':data['rust_stdlib_evidence']['notice_sha256'],
                         'complete_compiled_closure':False})
        for scope in rust['grant_scopes']:
            if scope['id']in('rust-standard-library','std-lock-registry-candidates'):continue
            key='mcp-rust-runtime-grant:'+scope['id']
            declaration='MIT'if scope['id']=='compiler-builtins-libm-runtime-source'else scope['grant']
            self.node(key,scope['id'],scope.get('version'),'scoped-rust-runtime-source-grant',
                'sbom/mcp-rust-stdlib/manifest.json',declared=declaration,
                details={'source_scope':scope,'notice_sha256':data['rust_stdlib_evidence']['notice_sha256'],
                         'conservative_runtime_source_scope_not_a_linkage_assertion':True})
            for root_key in rust_keys.values():self.edge(root_key,key)
        registry_path='sbom/mcp-rust-stdlib/registry-candidate-grants.json'
        registry=self.data(registry_path)
        need(type(registry['packages'])is list and len(registry['packages'])==18)
        for package in registry['packages']:
            key='mcp-rust-stdlib-candidate:'+package['name']+'@'+package['version']
            self.node(key,package['name'],package['version'],'rust-stdlib-lock-source-notice-candidate',
                registry_path,[('SHA256',package['archive_sha256'])],package['license_declared'],
                {'official_source':package['url'],'source_locks':package['rust_commit_locks'],
                 'actual_linkage_not_asserted':True})
            for commit in package['rust_commit_locks']:self.edge(rust_keys[commit],key)
        targets=[self.artifact_target]if self.artifact_target is not None else sorted(m.TARGETS)
        need(all(target in m.TARGETS for target in targets))
        filenames={row['filename']for target in targets for row in profile['targets'][target]}
        records={w['filename']:w for w in profile['wheels']if w['filename']in filenames}
        component_keys={}
        for filename,w in sorted(records.items()):
            key='mcp-wheel:'+filename
            declaration='MIT'if w['name']=='rfc3339-validator'and w['license_declared']=='MIT license'else w['license_declared']
            self.node(key,w['name'],w['version'],'source-bound-publisher-wheel-observation',m.PROFILE_FILE,
                [('SHA256',w['sha256'])],declaration,
                {'filename':filename,'bytes':w['bytes'],'publisher_bytes_unmodified':True,
                 'native_members':w['native_members'],'notice_members':w['notice_members']})
            if w['sha256']in data['libffi_evidence']['applies_to_wheel_sha256']:
                self.edge(key,ffi_key)
            for observed in w['rust_runtime_observations']:
                for commit in observed['source_commits']:
                    self.edge(key,rust_keys[commit])
            for graph in w['publisher_graphs']:
                for component in graph['components']:
                    identity=component['id'];root=component['source_root_id']
                    if root in source_keys:
                        destination=source_keys[root]
                    else:
                        destination='mcp-native-declared:'+identity
                        if destination not in self.nodes:
                            self.node(destination,component['name'],component['version'],'wheel-publisher-native-declaration',
                                m.PROFILE_FILE,details={'source_root_id':root,'declaration_only':True})
                    component_keys[identity]=destination
                    self.edge(key,destination)
        for filename,w in sorted(records.items()):
            for graph in w['publisher_graphs']:
                for a,b in graph['dependency_edges']:
                    self.edge(component_keys[a],component_keys[b])
        for target in targets:
            names={x['name']:'mcp-wheel:'+x['filename']for x in profile['targets'][target]}
            for a,b in profile['dependencies'][target]['edges']:
                self.edge(names[a],names[b])
        self.gaps.extend(['mcp_target_runtime_and_distribution_review_pending',
            'publisher_source_and_native_declarations_are_not_exhaustive_compiled_coverage',
            'source_notice_asset_contains_a_conservative_cross_target_source_notice_set'])

    def committed_tree(self):
        from tools.source_snapshot_admission import _source_spawn_room
        _source_spawn_room()
        head=run_worker(['git','--no-replace-objects','-C',str(self.root),'rev-parse','--verify','HEAD^{commit}'],input=b'',timeout=20,output_limit=100)
        need(head.returncode==0);self.commit=head.stdout.decode('ascii').strip();need(COMMIT.fullmatch(self.commit))
        _source_spawn_room()
        result=run_worker(['git','--no-replace-objects','-C',str(self.root),'ls-tree','-r','-z','--full-tree',self.commit],input=b'',timeout=20,output_limit=2_000_000)
        need(result.returncode==0);rows=result.stdout.split(b'\0');need(rows[-1:]==[b''] and len(rows)-1<=MAX_NODES)
        evidence='scripts/source_snapshot_v3.py';self.read(evidence);self.read('scripts/source_snapshot.py');self.read('scripts/source_snapshot_v2.py')
        for row in rows:
            if not row:continue
            meta,name=row.split(b'\t',1);mode,kind,oid=meta.decode('ascii').split(' ');name=name.decode('ascii');path_name(name)
            need(mode in ('100644','100755')and kind=='blob'and COMMIT.fullmatch(oid))
            self.node('git:'+name,name,None,'committed-git-blob',evidence,details={'git_blob_oid':oid,'git_object_format':'sha1','mode':mode})
        self.gaps.append('whole_source_copy_requires_current_finite_profile_and_actual_archive_binding')
    def finish(self):
        # Source Git workers run before the heavy source-file Capture set.
        if self.route=='source-snapshot':self.committed_tree()
        for path in (*COMMON,*CONSUMERS[self.route]):self.read(path)
        for path in (*PRODUCERS,'tools/dependency_policy.py','scripts/worker_process.py'):
            need(self.read(path)==self.c.read(ROOT/path,16_000_000,private=False))
        if self.route=='ps-source':
            from tools.dependency_policy import require_route
            for row in require_route(self.route,self.root)['files']:
                need(sha(self.read(row['path']))==row['sha256'])
                self.node('source:'+row['path'],row['path'],None,'admitted-source-member',row['path'],[('SHA256',row['sha256'])])
        elif self.route=='source-snapshot':pass  # already bound before heavy reads
        elif self.route in ('web-checker','ios-app','android-app'):
            self.npm('site/package-lock.json');self.web_assets()
            if self.route!='web-checker':self.gaps.append('unbundled_platform_sdk_rights_are_separate_prerequisites')
        elif self.route.endswith('-linux-amd64'):self.image()
        elif self.route.startswith('nli-'):self.nli()
        elif self.route.startswith('c2pa-'):self.c2pa()
        elif self.route=='mcp-stdio':self.mcp()
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
        packages.append(p)
        relationship={'spdxElementId':'SPDXRef-Artifact','relationshipType':'OTHER','relatedSpdxElement':p['SPDXID']}
        relationship['comment']=('Source evidence'if route=='source-snapshot'else
                                 'Associated source evidence; not a containment claim.')
        relationships.append(relationship)
    for edge in graph['relationships']:relationships.append({'spdxElementId':ids[edge['from']],'relationshipType':'DEPENDS_ON','relatedSpdxElement':ids[edge['to']]})
    return {'spdxVersion':'SPDX-2.3','dataLicense':'CC0-1.0','SPDXID':'SPDXRef-DOCUMENT',
      'name':'AI Trust ID '+route+' artifact/source evidence','documentNamespace':'urn:uuid:'+str(uuid.uuid5(uuid.NAMESPACE_OID,seed)),
      'creationInfo':{'created':created,'creators':['Tool: AITrust-ID-artifact-sbom-1.0.0']},
      'comment':'Source graph SHA256 '+sha(encoded(graph))+'; source-input set SHA256 '+sha(encoded(graph['source_sha256']))+'; complete embedded coverage and license clearance are not asserted.'+(' All OTHER relationships identify associated source evidence, not a containment or permission claim.'if route=='source-snapshot'else''),
      'documentDescribes':['SPDXRef-Artifact'],'packages':packages,'relationships':relationships}


class _SourceGraphCapture:
    """Source-only short captures, closed input denominator and one read ledger."""
    def __init__(self,root,artifact):
        self.root=Path(root);self.artifact_path=Path(artifact).absolute();self.snapshot=None;self.total_read=0
        self.allowed={self.root/p for p in(*COMMON,*CONSUMERS['source-snapshot'],*PRODUCERS,'tools/dependency_policy.py','scripts/worker_process.py')}
    def _adopt(self,phase,expected,artifact_paths=()):
        from tools.source_snapshot_admission import _SourceReadset,_phase_critical
        with _phase_critical():
            if self.snapshot is None:
                self.snapshot=_SourceReadset.from_capture(phase,expected,anchors=(self.root,self.artifact_path.parent),artifact_paths=artifact_paths)
            else:self.snapshot.absorb(phase,expected,artifact_paths=artifact_paths)
    def read(self,path,limit=16_000_000,*,private=False):
        path=Path(path).absolute();need(private is False and path in self.allowed and type(limit)is int and 0<limit<=16_000_000)
        with Capture()as phase:
            phase.total_read=self.total_read
            try:
                raw=phase.read(path,limit,private=False);self._adopt(phase,{path:sha(raw)});return raw
            finally:self.total_read=phase.total_read
    def artifact(self,path,limit,*,copy_to):
        path=Path(path).absolute();need(path==self.artifact_path and limit==64_000_000 and self.snapshot is not None)
        with Capture()as phase:
            phase.total_read=self.total_read
            try:
                value=phase.artifact(path,limit,copy_to=copy_to);self._adopt(phase,{path:value['sha256']},(path,));return value
            finally:self.total_read=phase.total_read
    def check(self):
        need(self.snapshot is not None);self.snapshot.total=self.total_read
        try:self.snapshot.check()
        finally:self.total_read=self.snapshot.total
    def close(self):
        if self.snapshot is not None:self.snapshot.close()
    def __enter__(self):return self
    def __exit__(self,*unused):self.close()


def _prepare_source(artifact,source_commit,root,created):
    from tools import source_snapshot_admission as admission
    root=Path(root);need(root.resolve()==ROOT.resolve());artifact=Path(artifact).absolute()
    with _SourceGraphCapture(root,artifact)as captured:
        g=Graph('source-snapshot',root,captured).finish();need(g['committed_tree']==source_commit)
        with io.BytesIO()as received:
            value=captured.artifact(artifact,64_000_000,copy_to=received);raw=received.getvalue()
        expected={root/path:digest for path,digest in g['source_sha256'].items()}
        need(artifact not in expected or expected[artifact]==value['sha256']);expected[artifact]=value['sha256']
        need(captured.snapshot.expected==expected)
        # Every heavy owned file capture is CLOSED. No borrowed caller is closed.
        bound=admission.review_archive(raw,source_commit=source_commit,root=root)
        need(bound.get('pass')is True and bound.get('source_copy_profile_satisfied')is True and bound.get('trusted_git_bytes_matched')is True
          and bound.get('source_commit')==source_commit and bound.get('archive_sha256')==value['sha256']and bound.get('archive_bytes')==value['bytes']
          and bound.get('source_files')==len(g['nodes'])and bound.get('signature_verified')is False
          and all(bound.get(k)is False for k in('legal_clearance','compiled_runtime_permission','source_archive_admitted','release_authorized','accuracy','complete_F057_X02')))
        policy=evaluate('source-snapshot',root);document=spdx('source-snapshot',value,g,created)
        record={'profile':PROFILE,'route':'source-snapshot','source_commit':source_commit,'artifact':value,'created':created,'graph':g,'spdx':document,
          'spdx_sha256':sha(encoded(document)+b'\n'),'graph_sha256':sha(encoded(g)),'policy':policy,'artifact_format_verified':True,
          'attestation_verified':False,'release_authorized':False,'license_clearance':False,'complete_project_obligations':False}
        need(len(encoded(record))<=MAX_PACKET);admission._source_spawn_room()
        current=run_worker(['git','--no-replace-objects','-C',str(root),'rev-parse','--verify','HEAD^{commit}'],input=b'',timeout=20,output_limit=100)
        need(current.returncode==0 and current.stdout.decode('ascii').strip()==source_commit)
        captured.check();return record


@boundary
def prepare(route,artifact,source_commit,root=ROOT,created=None):
    need(type(source_commit)is str and COMMIT.fullmatch(source_commit));need(route in ROUTES)
    if route=='source-snapshot':need(Path(root).resolve()==ROOT.resolve())
    created=created or datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z')
    if route=='source-snapshot':return _prepare_source(artifact,source_commit,root,created)
    try:
        with Capture()as c:
            mcp=None
            if route=='mcp-stdio':
                from tools.mcp_distribution import verify_file
                mcp=verify_file(artifact,root)
            g=Graph(route,root,c,artifact_target=mcp['target']if mcp else None).finish();value=c.artifact(artifact)
            # The actually admitted source route is also checked against canonical contents.
            if route=='ps-source':
                from tools.ps_source_distribution import verify_file
                verify_file(artifact,root)
            if mcp is not None:
                need(mcp['sha256']==value['sha256']and mcp['bytes']==value['bytes']and
                     mcp['profile_sha256']==g['source_sha256']['sbom/mcp-runtime/manifest.json'])
            sbom=spdx(route,value,g,created);policy=evaluate(route,root)
            record={'profile':PROFILE,'route':route,'source_commit':source_commit,'artifact':value,'created':created,
                'graph':g,'spdx':sbom,'spdx_sha256':sha(encoded(sbom)+b'\n'),'graph_sha256':sha(encoded(g)),
                'policy':policy,'artifact_format_verified':route in('ps-source','mcp-stdio','source-snapshot'),'attestation_verified':False,'release_authorized':False,
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
