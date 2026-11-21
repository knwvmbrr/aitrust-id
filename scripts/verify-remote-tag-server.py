#!/usr/bin/env python3
"""Run only the remote connector's bounded official-client and HTTP controls."""
import argparse
import ast
from datetime import datetime,timezone
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1]
FILES=['tools/remote_tag_server.py','scripts/remote-tag-server.py','tests/test_remote_tag_server.py','scripts/verify-remote-tag-server.py','docs/remote-tag-connectors-plan.md','docs/remote-tag-connectors.md','tools/tag_api.py','scripts/check-tags.py','scripts/check-ps.py','scripts/worker_process.py','services/evaluator/app.py','protocol/normalization.py','protocol/unicode15-data.json','integrations/mcp/requirements.lock']
def snapshot():return {n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in FILES}
class Parser(argparse.ArgumentParser):
    def error(self,message):raise ValueError('Refused')
def main():
    p=Parser(description=__doc__);p.add_argument('--output',type=Path);args=p.parse_args()
    if importlib.metadata.version('mcp')!='2.3.0':raise ValueError('Refused')
    before=snapshot();start=datetime.now(timezone.utc).isoformat()
    process=subprocess.run([sys.executable,'-B','-m','unittest','discover','-s','tests','-p','test_remote_tag_server.py','-v'],cwd=ROOT,capture_output=True,timeout=45)
    if len(process.stdout)+len(process.stderr)>256_000:raise ValueError('Refused')
    test_count=sum(isinstance(n,ast.AsyncFunctionDef) or isinstance(n,ast.FunctionDef) for n in ast.walk(ast.parse((ROOT/'tests/test_remote_tag_server.py').read_text())) if isinstance(n,(ast.AsyncFunctionDef,ast.FunctionDef)) and n.name.startswith('test_'))
    after=snapshot();ran=re.search(rb'Ran (\d+) tests? in',process.stderr)
    report={'profile':'remote-PS-MCP-HTTP-engineering/v1','captured_at':start,'finished_at':datetime.now(timezone.utc).isoformat(),'pass':process.returncode==0 and before==after and ran is not None and int(ran[1])==test_count,'source_sha256':before,'source_stable':before==after,'mcp_sdk':'2.3.0','python_version':sys.version.split()[0],'focused_test_groups':int(ran[1]) if ran else 0,'expected_groups':test_count,'exit':process.returncode,'stdout_sha256':hashlib.sha256(process.stdout).hexdigest(),'stderr_sha256':hashlib.sha256(process.stderr).hexdigest(),'actual':['owned loopback ordinaryHTTP and official MCP modern2026-07-28+legacy clients','canonical briefrecords positive/no-finding parity; remotePII nevergateway','Host/Origin/path/query/headers/duplicateJSON/UTF8/body/output/framing/deadline refusals','two actualownedworkers busyadmission; one cancellation preserves other; health/listing saturation independence','actualsocketdisconnect ordinary/MCP and workerdeadline/shutdown/spawnrace reap','actualCLI NoAuth loopback/privacy-error/logging/shutdown; URLtext notfetched'],'public_service_deployed':False,'AI_host_account_connected':False,'real_user_data_collected':False,'tag_release_approved':False,'independent_accuracy_evidence':False,'new_original_closures':0,'limits':['Synthetic explicitlyselected examples on owned loopback; no externalChatGPT/Anthropic account connection.','No hostedTLS/proxy/operator-log verification, livepublicroute, distributedabuse/SLA guarantee or wholedependency clearance.','PII unavailable remotely; existinglocalstdio/ondevice remains separate.']}
    raw=(json.dumps(report,indent=2)+'\n').encode()
    if args.output:
        target=args.output.absolute();parent=target.parent;info=parent.stat()
        if parent.resolve()!=parent or not stat.S_ISDIR(info.st_mode) or info.st_uid!=os.getuid() or info.st_mode&0o022:raise ValueError('Refused')
        fd=os.open(target,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
        try:
            with os.fdopen(fd,'wb',closefd=False) as output:output.write(raw);output.flush();os.fsync(output.fileno())
        finally:owned=fd;fd=None;os.close(owned)
    print(json.dumps({'pass':report['pass'],'focused_test_groups':report['focused_test_groups'],'source_stable':report['source_stable'],'receipt_sha256':hashlib.sha256(raw).hexdigest()}))
    return 0 if report['pass'] else 1
if __name__=='__main__':
    try:raise SystemExit(main())
    except Exception:
        print('{"pass":false,"reason":"remote_connector_verification_unavailable"}');raise SystemExit(1)
