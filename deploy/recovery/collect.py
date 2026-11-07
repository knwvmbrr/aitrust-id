#!/usr/bin/env python3
"""Owner-run SSH transfer; private keys stay on the owner's machine."""
import argparse,configparser,hashlib,json,os,re,shlex,stat,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def require(ok):
    if not ok:raise ValueError('Recovery transfer refused')
def private(path):
    path=path.resolve(strict=True);s=path.stat();require(stat.S_ISREG(s.st_mode) and s.st_uid==os.getuid() and s.st_nlink==1 and not s.st_mode&0o077)
    require(not any((p/'.git').exists() for p in path.parents));return path

RECEIVER_INSTALL = """import os,sys,hashlib,stat,re
from pathlib import Path
assert os.geteuid()==0
raw=sys.stdin.buffer.read(100001);digest=sys.argv[1];p=Path(sys.argv[2]);parent=Path('/var/lib/aitrust-id/recovery-source')
assert len(raw)<100001 and re.fullmatch('[a-f0-9]{64}',digest) and hashlib.sha256(raw).hexdigest()==digest
assert p.parent==parent and p.name=='receive-'+digest+'.py'
s=parent.lstat();assert stat.S_ISDIR(s.st_mode) and s.st_uid==0 and not s.st_mode&0o077
if p.exists() or p.is_symlink():
 s=p.lstat();assert stat.S_ISREG(s.st_mode) and s.st_uid==0 and s.st_nlink==1 and stat.S_IMODE(s.st_mode)==0o700
 assert p.read_bytes()==raw
else:
 fd=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o700)
 with os.fdopen(fd,'wb') as out:
  out.write(raw);out.flush();os.fsync(out.fileno());os.fchmod(out.fileno(),0o700)
assert hashlib.sha256(p.read_bytes()).hexdigest()==digest
"""

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--primary',required=True);p.add_argument('--primary-key',type=Path,required=True);p.add_argument('--recovery-directory',type=Path,required=True);p.add_argument('--work',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    require(re.fullmatch('[A-Za-z0-9][A-Za-z0-9.:-]{0,252}',a.primary) and re.fullmatch('/var/lib/aitrust-id/recovery-vm/[a-f0-9]{32}',a.work))
    key=private(a.primary_key);bundle=a.recovery_directory.resolve(strict=True);require(bundle.is_dir() and not bundle.stat().st_mode&0o077)
    cfg=configparser.ConfigParser(interpolation=None);cfg.read_string(private(bundle/'primary.conf').read_text());backup=cfg['global']['repo1-host'];require(re.fullmatch('[A-Za-z0-9][A-Za-z0-9.:-]{0,252}',backup))
    backup_key=private(bundle/'backup-admin-key')
    def ssh(host,user,key,command):return ['ssh','-i',str(key),'-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','-o','ConnectTimeout=8',user+'@'+host,command]
    # Inspect root-only protected copies through the existing owner-approved admin key.
    guard=(ROOT/'deploy/backup/restore.py').read_text();namespace={};exec(compile(guard,'reviewed-restore-guard','exec'),namespace)
    import inspect
    # This source file contains no recovery key; send the reviewed guard as code,
    # then call only its path/ownership check. Never invoke its restore main.
    code="import os,re,stat,time,json; from pathlib import Path\n"+guard[guard.index('def protected_generation('):guard.index('\n\ndef main():')]+"\nroot=Path('/var/lib/aitrust-id/protected'); names=sorted(p.name for p in root.iterdir() if re.fullmatch(r'\\d{8}T\\d{6}Z-[a-f0-9]{8}',p.name)); assert names; chosen=protected_generation(names[-1]); print(json.dumps({'generation':chosen.name,'path':str(chosen)}))"
    remote='sudo python3 -c '+shlex.quote(code)
    selected=json.loads(subprocess.check_output(ssh(backup,'ait-backup-admin',backup_key,remote),stdin=subprocess.DEVNULL,timeout=60));generation=selected['generation'];require(re.fullmatch(r'\d{8}T\d{6}Z-[a-f0-9]{8}',generation))
    receiver=(ROOT/'deploy/recovery/receive.py').read_bytes();digest=hashlib.sha256(receiver).hexdigest();target='/var/lib/aitrust-id/recovery-source/receive-'+digest+'.py'
    upload=RECEIVER_INSTALL
    subprocess.run(ssh(a.primary,'debian',key,'sudo python3 -c '+shlex.quote(upload)+' '+digest+' '+shlex.quote(target)),input=receiver,check=True,capture_output=True,timeout=30)
    # Verify owner recovery material against the current primary without printing it.
    cipher=private(bundle/'repository-cipher.txt').read_bytes().strip();require(len(cipher)>=48)
    compare="import configparser,sys,hmac; c=configparser.ConfigParser(interpolation=None); c.read('/etc/pgbackrest/pgbackrest.conf'); assert hmac.compare_digest(c['global']['repo1-cipher-pass'].encode(),sys.stdin.buffer.read(1024).strip()); print('owner_material_matches')"
    result=subprocess.run(ssh(a.primary,'debian',key,'sudo python3 -c '+shlex.quote(compare)),input=cipher,capture_output=True,timeout=30);require(result.returncode==0 and result.stdout.strip()==b'owner_material_matches')
    sender='sudo tar --hard-dereference -cf - -C '+shlex.quote(selected['path'])+' .'
    command='sudo python3 '+shlex.quote(target)+' --work '+shlex.quote(a.work)
    source=subprocess.Popen(ssh(backup,'ait-backup-admin',backup_key,sender),stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    try:
        dest=subprocess.Popen(ssh(a.primary,'debian',key,command),stdin=source.stdout,stdout=subprocess.PIPE,stderr=subprocess.PIPE);source.stdout.close()
        out,err=dest.communicate(timeout=300);sender_error=source.communicate(timeout=30)[1]
        require(dest.returncode==0 and source.returncode==0)
    except BaseException:
        source.kill();source.wait();raise
    proof=json.loads(out);proof.update(generation=generation,owner_recovery_material_matches=True,administrative_private_keys_transferred=False,production_changed=False)
    require(not a.output.exists());a.output.write_text(json.dumps(proof,indent=2)+'\n');a.output.chmod(0o600);print(json.dumps({'encrypted_backup_collected':True,'files':proof['files'],'bytes':proof['encrypted_archive_bytes'],'owner_material_matches':True}))
if __name__=='__main__':main()
