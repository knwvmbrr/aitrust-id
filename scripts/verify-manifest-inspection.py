#!/usr/bin/env python3
"""Execute optional real-SDK CLI controls against frozen synthetic images."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tools import manifest_inspection as m
from protocol.reports import write_report


def main():
    import argparse
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output');args=parser.parse_args()
    paths=['tools/manifest_inspection.py','scripts/inspect-manifest.py','scripts/verify-manifest-inspection.py',
        'tests/test_manifest_inspection.py','eval/c2pa-inspection.lock','eval/dependencies/c2pa-inspection.json',
        'protocol/corpus.py','protocol/normalization.py','protocol/unicode15-data.json','protocol/reports.py']
    paths += [p.relative_to(ROOT).as_posix() for p in (ROOT/'tests/fixtures/c2pa-inspection-2026').iterdir() if p.is_file()]
    def inventory():return {p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in sorted(paths)}
    before=inventory();native,pins=m.checked_sdk();cases=[]
    fixture=ROOT/'tests/fixtures/c2pa-inspection-2026'
    def invoke(arguments,exit_code,state,environment=None):
        result=subprocess.run([sys.executable,str(ROOT/'scripts/inspect-manifest.py'),*arguments],
            cwd=ROOT,capture_output=True,timeout=20,env=environment)
        assert result.returncode==exit_code,(arguments,result.stderr[:300])
        assert not result.stderr and b'FIXTURE_PRIVATE_METADATA_CANARY' not in result.stdout
        assert str(ROOT).encode() not in result.stdout
        value=json.loads(result.stdout);assert value['state']==state and value['tags']==[]
        assert value['content_truth_established'] is False and value['author_identity_established'] is False
        if state!='UNAVAILABLE':assert value['method_sha256']==before['tools/manifest_inspection.py']
        return value
    for name,state in [('signed','OBSERVED'),('altered','OBSERVED'),('unsigned','NOT_FOUND')]:
        value=invoke(['--image',str(fixture/(name+'.png'))],0,state)
        if name!='unsigned':
            assert value['claim_signature']=='matched' and value['signer_trust']=='untrusted'
            assert value['asset_binding']==('matched' if name=='signed' else 'mismatched')
            assert value['revocation']=='unknown_skipped'
        cases.append({'case':name,'state':state,'minimal_output_no_private_metadata':True})
    value=invoke(['--image',str(fixture/'signed.png')],0,'OBSERVED',
        {**os.environ,'C2PA_LIBRARY_NAME':'/nonexistent/LOADER_PRIVATE_CANARY','LD_LIBRARY_PATH':'/nonexistent/LOADER_PRIVATE_CANARY'})
    assert value['asset_binding']=='matched' and value['active_assertion_count']==2
    cases.append({'case':'ambient_native_loader_override','state':'OBSERVED','reviewed_library_used':True})
    with tempfile.TemporaryDirectory(prefix='aitrust-manifest-control-') as directory:
        private=Path(directory).resolve();private.chmod(0o700)
        malformed=private/'malformed.png';malformed.write_bytes((fixture/'unsigned.png').read_bytes()[:-1])
        unsupported=private/'unsupported.jpg';unsupported.write_bytes(b'JPEG_NOT_PNG')
        oversized=private/'oversized.png';oversized.write_bytes(b'\x89PNG\r\n\x1a\n'+b'X'*m.MAX_ASSET_BYTES)
        linked=private/'link.png';linked.symlink_to(fixture/'signed.png')
        for name,path in [('malformed',malformed),('unsupported',unsupported),('oversized',oversized),('symlink',linked),('directory',private),('missing',private/'absent.png')]:
            invoke(['--image',str(path)],2,'UNAVAILABLE');cases.append({'case':name,'state':'UNAVAILABLE','no_path_or_metadata_echo':True})
        report=private/'full.json';invoke(['--image',str(fixture/'signed.png'),'--private-report',str(report)],0,'OBSERVED')
        assert report.stat().st_mode&0o777==0o600 and 'FIXTURE_PRIVATE_METADATA_CANARY' in report.read_text()
        saved=report.read_bytes();invoke(['--image',str(fixture/'signed.png'),'--private-report',str(report)],2,'UNAVAILABLE');assert report.read_bytes()==saved
        cases.append({'case':'explicit_private_export_and_replacement_refusal','state':'OBSERVED','owner_private':True})
        public=private/'public';public.mkdir(mode=0o755)
        for name,path in [('public_directory',public/'out.json'),('source_checkout',ROOT/'private-do-not-create.json')]:
            invoke(['--image',str(fixture/'signed.png'),'--private-report',str(path)],2,'UNAVAILABLE');assert not path.exists()
            cases.append({'case':name,'state':'UNAVAILABLE','private_export_refused':True})
    stable=before==inventory();assert stable
    isolated=None
    if sys.platform=='linux':
        try:isolated=os.readlink('/proc/self/ns/net')!=os.readlink('/proc/1/ns/net')
        except OSError:pass
    report={'captured_at':datetime.now(timezone.utc).isoformat(),'pass':True,'cases':cases,
        'case_count':len(cases),'sources':before,'source_unchanged_during_execution':stable,
        'package_version':pins['package_version'],'sdk_version':pins['sdk_version'],
        'native_sha256':hashlib.sha256(Path(native).read_bytes()).hexdigest(),
        'effective_user_is_root':os.geteuid()==0,
        'network_namespace_differs_from_init':isolated,'settings':m.SETTINGS,
        'native_is_a_complete_security_sandbox':False,'new_tag_releases':0,'independent_accuracy_evidence':False}
    if args.output:write_report(args.output,report,root=ROOT)
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
