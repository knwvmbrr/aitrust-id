#!/usr/bin/env python3
"""Deliver recovery inputs only to the verified loopback-only replacement VM."""
import argparse,hashlib,json,os,re,runpy,shlex,subprocess,sys
from pathlib import Path
BASE=Path('/var/lib/aitrust-id/recovery-vm');CACHE=Path('/var/lib/aitrust-id/recovery-source')
def check(ok):
    if not ok:raise ValueError('Offline guest recovery delivery refused')
def run(args,*,raw=None,timeout=60,check_status=True):return subprocess.run(list(map(str,args)),input=raw,stdin=subprocess.DEVNULL if raw is None else None,capture_output=True,timeout=timeout,check=check_status)
def load(path,prefix):
    check(path.parent==CACHE and re.fullmatch(prefix+'-[a-f0-9]{64}[.]py',path.name))
    info=path.lstat();check(info.st_uid==0 and not info.st_mode&0o077 and not path.is_symlink());check(hashlib.sha256(path.read_bytes()).hexdigest()==path.name[len(prefix)+1:-3]);return runpy.run_path(str(path))
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--work',required=True,type=Path);p.add_argument('--isolation-tool',required=True,type=Path);p.add_argument('--guest-program',required=True,type=Path);a=p.parse_args()
    check(os.geteuid()==0 and a.work.parent==BASE and re.fullmatch('[a-f0-9]{32}',a.work.name));work=a.work
    material=json.loads(sys.stdin.buffer.read(100001));check(set(material)=={'cipher','source_settings','owner_admin_public_key'})
    tools=load(a.isolation_tool,'isolate');check(tools['inspect'](work)['guest_ready'] is True)
    source=a.guest_program;check(source.parent==CACHE and re.fullmatch('restore-guest-[a-f0-9]{64}[.]py',source.name));info=source.lstat();check(info.st_uid==0 and not info.st_mode&0o077 and not source.is_symlink());check(hashlib.sha256(source.read_bytes()).hexdigest()==source.name[14:-3])
    received=json.loads((work/'collection.json').read_text());check(received['offline_guest_verified_before_receive'] is True)
    check(type(material['cipher']) is str and len(material['cipher'])>=48)
    controller=tools['ssh']
    def guest(cmd,raw=None,timeout=120):return controller(work,cmd,isolated=True,raw=raw,timeout=timeout)
    guest("sudo install -d -m 0700 /etc/aitrust-recovery; sudo install -d -o root -g postgres -m 0750 /var/lib/aitrust-recovery; sudo install -d -m 0700 /var/lib/aitrust-recovery/repository")
    # The source archive was already bounded and validated by receive.py; only
    # root can modify this directory. No arbitrary received tar is extracted.
    data=work/'encrypted-backup';check(data.is_dir() and not data.is_symlink())
    pid=str(json.loads((work/'isolation.json').read_text())['pid'])
    ssh=['nsenter','-t',pid,'-n','--','ssh','-F','/dev/null','-i',str(work/'control/identity'),'-p','22280','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','-o','UserKnownHostsFile='+str(work/'control/known_hosts'),'-o','ConnectTimeout=5','debian@127.0.0.1']
    sender=subprocess.Popen(['tar','--hard-dereference','-cf','-','-C',str(data),'.'],stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    receiver=subprocess.Popen([*ssh,'sudo tar -xf - --no-same-owner --no-same-permissions -C /var/lib/aitrust-recovery/repository'],stdin=sender.stdout,stdout=subprocess.PIPE,stderr=subprocess.PIPE);sender.stdout.close()
    out,err=receiver.communicate(timeout=180);sender.communicate(timeout=30);check(sender.returncode==0 and receiver.returncode==0)
    query=r"""SELECT format('SELECT json_build_object(''schema'',%L,''table'',%L,''rows'',count(*)) FROM %I.%I;',n.nspname,c.relname,n.nspname,c.relname) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE c.relkind='r' AND n.nspname NOT IN ('pg_catalog','information_schema') AND n.nspname NOT LIKE 'pg_toast%' ORDER BY n.nspname,c.relname
\gexec
"""
    rows=run(['runuser','-u','postgres','--','psql','-XAt','-v','ON_ERROR_STOP=1','-d','aitrustid'],raw=query.encode(),timeout=45).stdout.decode()
    material.update(nonce=work.name,source_system_sha256=json.loads((work/'control.json').read_text())['primary_before']['database_identity_sha256'],source_inventory=[json.loads(line) for line in rows.splitlines() if line.strip()])
    check(run(['runuser','-u','postgres','--','psql','-XAt','-d','aitrustid','-c',"SELECT count(*) FROM pg_tablespace WHERE spcname NOT IN ('pg_default','pg_global');"]).stdout.strip()==b'0')
    # No secret is put into a process argument or a public execution log.
    guest('sudo tee /etc/aitrust-recovery/material.json >/dev/null; sudo chmod 0600 /etc/aitrust-recovery/material.json',raw=json.dumps(material).encode())
    guest('sudo tee /etc/aitrust-recovery/restore-guest.py >/dev/null; sudo chmod 0700 /etc/aitrust-recovery/restore-guest.py',raw=source.read_bytes())
    rejected=run([*ssh,'sudo python3 /etc/aitrust-recovery/restore-guest.py --nonce '+work.name+' --data-directory /tmp/incorrect-destination'],check_status=False);check(rejected.returncode!=0)
    result=guest('sudo python3 /etc/aitrust-recovery/restore-guest.py --nonce '+work.name,timeout=360)
    proof=json.loads(result.stdout);check(proof['pass'] is True);proof['wrong_destination_refused']=True
    (work/'recovery-result.json').write_text(json.dumps(proof,indent=2)+'\n');(work/'recovery-result.json').chmod(0o600);print(json.dumps(proof))
if __name__=='__main__':main()
