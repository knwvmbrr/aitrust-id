#!/usr/bin/env python3
"""Checkpoint a prepared guest and restart it with loopback-only host networking."""
import argparse,hashlib,json,os,re,runpy,subprocess,sys,time
from pathlib import Path
PARENT=Path('/var/lib/aitrust-id/recovery-vm')
def check(ok):
    if not ok:raise ValueError('Recovery isolation refused')
def run(args,*,timeout=40,raw=None,check_status=True):return subprocess.run(list(map(str,args)),input=raw,stdin=subprocess.DEVNULL if raw is None else None,capture_output=True,timeout=timeout,check=check_status)
def workdir(path):
    check(os.geteuid()==0 and path.parent==PARENT and re.fullmatch('[a-f0-9]{32}',path.name))
    for f in [PARENT,path]:
        s=f.lstat();check(f.is_dir() and not f.is_symlink() and s.st_uid==0 and not s.st_mode&0o022)
    return path

def ssh(work,command,*,isolated=False,raw=None,timeout=60):
    args=['ssh','-F','/dev/null','-i',str(work/'control/identity'),'-p','22280','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','-o','UserKnownHostsFile='+str(work/'control/known_hosts'),'-o','ConnectTimeout=5','debian@127.0.0.1',command]
    if isolated:
        row=json.loads((work/'isolation.json').read_text());pid=int(row['pid']);check(os.stat('/proc/'+str(pid)+'/ns/net').st_ino==row['network_inode'])
        args=['nsenter','-t',str(pid),'-n','--',*args]
    return run(args,raw=raw,timeout=timeout)

def isolate(work,launcher):
    row=json.loads((work/'control.json').read_text());check(row['phase']=='data_free_preparation' and row['production_data_copied'] is False and not (work/'isolation.json').exists())
    check((work/'control/known_hosts').is_file())
    command="sudo python3 - <<'PY'\nimport json,os,socket,subprocess\nfrom pathlib import Path\nassert Path('/var/lib/aitrust-recovery-prepared').is_file()\nr=subprocess.run(['python3','/opt/aitrust-id/host/verify.py'],capture_output=True,text=True,check=True)\nd=json.loads(r.stdout);assert d['passed'] is True\nprint(json.dumps({'hostname':socket.gethostname(),'kernel':os.uname().release,'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'foundation':d}))\nPY"
    checkpoint=work/'prepared-guest.json'
    if checkpoint.exists():
        info=checkpoint.lstat();check(info.st_uid==0 and not info.st_mode&0o077 and not checkpoint.is_symlink());guest=json.loads(checkpoint.read_text())
    else:
        guest=json.loads(ssh(work,command,timeout=120).stdout)
        checkpoint.write_text(json.dumps(guest,indent=2)+'\n');checkpoint.chmod(0o600)
    check(guest['hostname']=='aitrust-recovery-'+work.name[:8] and guest['foundation']['passed'] is True)
    check(guest['boot_id']!=Path('/proc/sys/kernel/random/boot_id').read_text().strip())
    if run(['systemctl','is-active',row['unit']],check_status=False).stdout.strip()==b'active':
        try:ssh(work,'sudo systemctl poweroff',timeout=30)
        except subprocess.CalledProcessError:pass
        deadline=time.monotonic()+45
        while run(['systemctl','is-active',row['unit']],check_status=False).stdout.strip()==b'active':
            check(time.monotonic()<deadline);time.sleep(1)
    run(['systemctl','stop',row['unit']],check_status=False)
    check(launcher.parent==Path('/var/lib/aitrust-id/recovery-source') and re.fullmatch(r'guest-[a-f0-9]{64}[.]py',launcher.name))
    info=launcher.lstat();check(info.st_uid==0 and not info.st_mode&0o077 and not launcher.is_symlink())
    check(hashlib.sha256(launcher.read_bytes()).hexdigest()==launcher.name[6:-3])
    build=runpy.run_path(str(launcher))['launch_args'];unit=row['unit']+'-isolated'
    check(run(['systemctl','is-active',unit],check_status=False).stdout.strip()!=b'active')
    run(build(work,unit,True));row['unit']=unit
    pid=int(run(['systemctl','show','--property=MainPID','--value',row['unit']]).stdout.strip())
    check(pid>1);network=os.stat('/proc/'+str(pid)+'/ns/net');check(network.st_ino!=os.stat('/proc/1/ns/net').st_ino)
    interfaces=json.loads(run(['nsenter','-t',str(pid),'-n','--','ip','-j','link']).stdout);check([x['ifname'] for x in interfaces]==['lo'])
    probe="import socket; s=socket.socket(); s.settimeout(2)\ntry:s.connect(('1.1.1.1',443)); raise SystemExit(9)\nexcept OSError as e:assert e.errno in (99,101,113)\n"
    run(['nsenter','-t',str(pid),'-n','--','python3','-c',probe])
    proof={'unit':row['unit'],'isolated_at':time.time(),'pid':pid,'network_inode':network.st_ino,'only_loopback':True,'external_connection_refused':True,'fresh_os_foundation_checks':len(guest['foundation']['checks']),'fresh_guest_boot_id_sha256':hashlib.sha256(guest['boot_id'].encode()).hexdigest(),'production_data_copied':False}
    (work/'isolation.json').write_text(json.dumps(proof,indent=2)+'\n');(work/'isolation.json').chmod(0o600);return proof

def inspect(work):
    row=json.loads((work/'isolation.json').read_text());pid=int(row['pid']);check(os.stat('/proc/'+str(pid)+'/ns/net').st_ino==row['network_inode'])
    try:
        raw=ssh(work,"sudo python3 -c \"import json,os; from pathlib import Path; assert Path('/var/lib/aitrust-recovery-prepared').is_file(); print(json.dumps({'ready':True,'kernel':os.uname().release,'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip()}))\"",isolated=True,timeout=15).stdout
        guest=json.loads(raw);check(hashlib.sha256(guest['boot_id'].encode()).hexdigest()!=row['fresh_guest_boot_id_sha256'])
        return {'isolated_guest_rebooted':True,'guest_ready':True,'only_loopback':True,'guest_data_state':'not_attested_by_readiness'}
    except Exception:return {'isolated_guest_rebooted':False,'guest_ready':False,'only_loopback':True,'guest_data_state':'not_attested_by_readiness'}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--work',required=True,type=Path);p.add_argument('--launcher',type=Path);p.add_argument('command',choices=['isolate','inspect']);a=p.parse_args();work=workdir(a.work);print(json.dumps(isolate(work,a.launcher) if a.command=='isolate' else inspect(work)))
if __name__=='__main__':main()
