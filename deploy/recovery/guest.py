#!/usr/bin/env python3
"""Start/inspect only the explicit data-free recovery guest. No live host bootstrap."""
import argparse,base64,hashlib,json,os,pwd,re,subprocess,time
from pathlib import Path
PARENT=Path('/var/lib/aitrust-id/recovery-vm')
FILES={'bootstrap.sh','verify.py','roles.sql','postgresql.conf','pg_hba.conf','pg_ident.conf','sshd.conf','nftables.conf'}
def require(ok):
    if not ok:raise ValueError('Recovery guest boundary refused')
def run(args,*,timeout=30,raw=None,check=True):return subprocess.run(list(map(str,args)),input=raw,stdin=subprocess.DEVNULL if raw is None else None,capture_output=True,text=raw is None,timeout=timeout,check=check)
def selected(path):
    require(os.geteuid()==0 and path.is_absolute() and path.parent==PARENT and re.fullmatch('[a-f0-9]{32}',path.name))
    for p in [PARENT,path]:
        s=p.lstat();require(p.is_dir() and not p.is_symlink() and s.st_uid==0 and not s.st_mode&0o022)
    return path

def snapshot():
    def h(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
    q=run(['runuser','-u','postgres','--','psql','-XAt','-d','aitrustid','-c','SELECT system_identifier FROM pg_control_system()']).stdout.strip()
    return {'database_identity_sha256':hashlib.sha256(q.encode()).hexdigest(),'postgres_active':run(['systemctl','is-active','postgresql@18-main']).stdout.strip(),'ssh_active':run(['systemctl','is-active','ssh']).stdout.strip(),'firewall_config_sha256':h('/etc/nftables.conf'),'ssh_policy_sha256':h('/etc/ssh/sshd_config.d/00-aitrust-id.conf'),'postgres_policy_sha256':h('/etc/postgresql/18/main/conf.d/aitrust-id.conf')}

def launch_args(work,unit,isolated=False):
    vm=work/'vm';disk=vm/'guest.qcow2';seed=vm/'seed.iso'
    args=['systemd-run','--quiet','--unit='+unit,'--service-type=exec','--property=User=ait-recovery','--property=Group=ait-recovery','--property=SupplementaryGroups=kvm','--property=NoNewPrivileges=yes','--property=MemoryMax=2G','--property=CPUQuota=100%','--property=TasksMax=256','--property=ProtectSystem=strict','--property=ProtectHome=yes','--property=PrivateTmp=yes','--property=ProtectKernelTunables=yes','--property=ProtectKernelModules=yes','--property=ProtectControlGroups=yes','--property=RestrictSUIDSGID=yes','--property=DevicePolicy=closed','--property=DeviceAllow=/dev/kvm rw','--property=ReadWritePaths='+str(vm),'--property=InaccessiblePaths=-/etc/pgbackrest -/etc/aitrust-id -/var/lib/postgresql -/var/lib/pgbackrest','/usr/bin/qemu-system-x86_64','-accel','kvm','-cpu','host','-m','1536','-smp','1','-display','none','-monitor','none','-serial','file:'+str(vm/'serial.log'),'-drive','file='+str(disk)+',if=virtio,format=qcow2','-drive','file='+str(seed)+',media=cdrom,readonly=on','-netdev','user,id=net0,hostfwd=tcp:127.0.0.1:22280-:22','-device','virtio-net-pci,netdev=net0','-device','virtio-rng-pci']
    if isolated:args.insert(args.index('/usr/bin/qemu-system-x86_64'),'--property=PrivateNetwork=yes')
    return args

def start(work,source):
    require(not (work/'control.json').exists());record=json.loads((work/'preparation.json').read_text());require(record['production_data_copied'] is False)
    require(hashlib.sha512((work/'base.qcow2').read_bytes()).hexdigest()==record['sha512'])
    files=json.loads(source.read_text());require(set(files)==FILES and all(type(v) is str and len(v)<100000 for v in files.values()))
    control=work/'control';vm=work/'vm';control.mkdir(mode=0o700);vm.mkdir(mode=0o700)
    identity=pwd.getpwnam('ait-recovery');os.chown(vm,identity.pw_uid,identity.pw_gid)
    run(['ssh-keygen','-q','-t','ed25519','-N','','-C','aitrust-disposable-guest','-f',control/'identity'])
    public=(control/'identity.pub').read_text().strip()
    userdata={'hostname':'aitrust-recovery-'+work.name[:8],'manage_etc_hosts':True,'ssh_pwauth':False,'disable_root':True,'users':['default',{'name':'debian','lock_passwd':True,'sudo':'ALL=(ALL) NOPASSWD:ALL','shell':'/bin/bash','ssh_authorized_keys':[public]}],'package_update':True,'packages':['systemd-resolved','systemd-timesyncd','ca-certificates','curl','gnupg'],'write_files':[],'runcmd':[]}
    for name,contents in files.items():userdata['write_files'].append({'path':'/opt/aitrust-recovery-source/host/'+name,'owner':'root:root','permissions':'0755' if name.endswith(('.py','.sh')) else '0600','encoding':'b64','content':base64.b64encode(contents.encode()).decode()})
    userdata['runcmd'].append(['bash','-c',"printf '\\nAITRUST_GUEST_SSH_KEY=' > /dev/ttyS0; cat /etc/ssh/ssh_host_ed25519_key.pub > /dev/ttyS0"])
    userdata['runcmd'].append(['bash','-c',"set -e; install -d /etc/systemd/resolved.conf.d; printf '[Resolve]\\nDNS=10.0.2.3\\n' > /etc/systemd/resolved.conf.d/recovery-drill.conf; systemctl restart systemd-resolved; if bash /opt/aitrust-recovery-source/host/bootstrap.sh > /var/log/aitrust-preparation.log 2>&1; then touch /var/lib/aitrust-recovery-prepared; printf '\\nAITRUST_GUEST_PREPARED\\n' > /dev/ttyS0; else printf '\\nAITRUST_GUEST_PREPARATION_FAILED\\n' > /dev/ttyS0; tail -60 /var/log/aitrust-preparation.log > /dev/ttyS0; exit 1; fi"])
    user=work/'user-data';user.write_text('#cloud-config\n'+json.dumps(userdata,indent=2)+'\n');user.chmod(0o640)
    meta=work/'meta-data';meta.write_text('instance-id: aitrust-recovery-'+work.name+'\nlocal-hostname: aitrust-recovery-'+work.name[:8]+'\n');meta.chmod(0o640)
    seed=vm/'seed.iso';run(['cloud-localds',seed,user,meta]);seed.chmod(0o400);os.chown(seed,identity.pw_uid,identity.pw_gid)
    disk=vm/'guest.qcow2';run(['qemu-img','create','-f','qcow2','-F','qcow2','-b',work/'base.qcow2',disk,'12G']);disk.chmod(0o600);os.chown(disk,identity.pw_uid,identity.pw_gid)
    unit='aitrust-recovery-'+work.name[:16]
    args=launch_args(work,unit)
    before=snapshot();run(args)
    row={'unit':unit,'work':str(work),'started_at':time.time(),'primary_before':before,'production_data_copied':False,'phase':'data_free_preparation','source_hashes':{k:hashlib.sha256(v.encode()).hexdigest() for k,v in files.items()}}
    (work/'control.json').write_text(json.dumps(row,indent=2)+'\n');(work/'control.json').chmod(0o600);return row

def inspect(work):
    data=json.loads((work/'control.json').read_text());serial=work/'vm/serial.log';text=serial.read_text(errors='replace')[-100000:] if serial.exists() else ''
    match=re.search(r'AITRUST_GUEST_SSH_KEY=(ssh-ed25519 [A-Za-z0-9+/=]+)',text)
    hostpin=bool(match)
    if match:
        known=work/'control/known_hosts';known.write_text('[127.0.0.1]:22280 '+match[1]+'\n');known.chmod(0o600)
    active=run(['systemctl','is-active',data['unit']],check=False).stdout.strip()
    return {'unit_active':active,'guest_host_key_pinned':hostpin,'prepared':'AITRUST_GUEST_PREPARED' in text,'preparation_failed':'AITRUST_GUEST_PREPARATION_FAILED' in text,'serial_tail_if_failed':text[-2500:] if 'AITRUST_GUEST_PREPARATION_FAILED' in text else None,'primary_unchanged':snapshot()==data['primary_before'],'production_data_copied':False}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--work',type=Path,required=True);p.add_argument('--source',type=Path);p.add_argument('command',choices=['start','inspect']);a=p.parse_args();work=selected(a.work)
    print(json.dumps(start(work,a.source) if a.command=='start' else inspect(work)))
if __name__=='__main__':main()
