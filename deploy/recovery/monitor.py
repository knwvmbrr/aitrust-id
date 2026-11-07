#!/usr/bin/env python3
"""Deliver versioned operational source to the verified offline replacement."""
import argparse, json, runpy, sys
from pathlib import Path

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--work',required=True,type=Path);p.add_argument('--apply-tool',required=True,type=Path);p.add_argument('--isolation-tool',required=True,type=Path);a=p.parse_args()
    # Reuse the root-owned content-hash loader and nonce-bound work checks.
    expected=Path('/var/lib/aitrust-id/recovery-source')
    assert a.apply_tool.parent==expected
    import hashlib,re,os
    assert re.fullmatch('apply-[a-f0-9]{64}[.]py',a.apply_tool.name)
    s=a.apply_tool.lstat();assert s.st_uid==0 and not s.st_mode&0o077 and not a.apply_tool.is_symlink()
    assert hashlib.sha256(a.apply_tool.read_bytes()).hexdigest()==a.apply_tool.name[6:-3]
    loader=runpy.run_path(str(a.apply_tool))['load'];tools=loader(a.isolation_tool,'isolate');tools['workdir'](a.work)
    payload=json.loads(sys.stdin.buffer.read(300001));assert set(payload)=={'alerts.py','source-health.py','monitor-guest.py'} and all(type(v) is str and len(v)<100000 for v in payload.values())
    assert tools['inspect'](a.work)['guest_ready'] is True
    for name in ['aitrust-source-backup-health.service','aitrust-source-backup-health.timer','aitrust-source-backup-failure.service']:
        path=Path('/etc/systemd/system')/name;s=path.lstat();assert s.st_uid==0 and not s.st_mode&0o022 and not path.is_symlink();payload[name]=path.read_text()
    code="import json,sys; from pathlib import Path; d=json.load(sys.stdin);p=Path('/opt/aitrust-recovery-operations');p.mkdir(mode=0o700,exist_ok=True);[(p.joinpath(k).write_text(v),p.joinpath(k).chmod(0o600)) for k,v in d.items()]"
    import shlex
    tools['ssh'](a.work,'sudo python3 -c '+shlex.quote(code),isolated=True,raw=json.dumps(payload).encode())
    result=tools['ssh'](a.work,'sudo python3 /opt/aitrust-recovery-operations/monitor-guest.py --nonce '+a.work.name,isolated=True,timeout=180)
    proof=json.loads(result.stdout);assert proof['pass'] is True
    out=a.work/'monitoring-result.json';out.write_text(json.dumps(proof,indent=2)+'\n');out.chmod(0o600);print(json.dumps(proof))
if __name__=='__main__':main()
