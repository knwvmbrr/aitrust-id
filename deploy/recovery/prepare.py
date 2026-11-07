#!/usr/bin/env python3
"""Prepare a data-free bounded VM drill; never copies production secrets or data."""
import argparse,hashlib,json,os,re,shutil,subprocess,time,urllib.request,uuid
from pathlib import Path

def require(value):
    if not value:raise ValueError('Recovery preparation refused')
def run(args,timeout=300):return subprocess.run(args,check=True,stdin=subprocess.DEVNULL,capture_output=True,text=True,timeout=timeout).stdout

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--execute',action='store_true');a=p.parse_args()
    require(a.execute and os.geteuid()==0 and Path('/etc/debian_version').read_text().startswith('13.'))
    require(Path('/etc/postgresql/18/main/conf.d/aitrust-id.conf').is_file())
    require(all(shutil.which(name) for name in ('cloud-localds','qemu-img','ssh-keygen')))
    memory={r.split(':')[0]:int(r.split()[1])*1024 for r in Path('/proc/meminfo').read_text().splitlines() if r.startswith(('MemAvailable:','MemTotal:'))}
    require(memory['MemAvailable']>=4*1024**3 and shutil.disk_usage('/var/lib').free>=10*1024**3)
    require(run(['runuser','-u','postgres','--','psql','-XAt','-d','aitrustid','-c','SHOW listen_addresses']).strip()=='')
    plan=run(['apt-get','--simulate','--no-install-recommends','install','qemu-system-x86'])
    match=re.search(r'(\d+) upgraded, (\d+) newly installed, (\d+) to remove',plan)
    require(match and match[1]=='0' and match[3]=='0')
    subprocess.run(['apt-get','--yes','--no-install-recommends','install','qemu-system-x86'],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,env={**os.environ,'DEBIAN_FRONTEND':'noninteractive','NEEDRESTART_MODE':'l'},timeout=300)
    try:run(['id','ait-recovery'])
    except subprocess.CalledProcessError:run(['useradd','--system','--user-group','--no-create-home','--shell','/usr/sbin/nologin','ait-recovery'])
    parent=Path('/var/lib/aitrust-id/recovery-vm');parent.mkdir(mode=0o750,exist_ok=True);run(['chown','root:ait-recovery',str(parent)]);parent.chmod(0o750)
    work=parent/uuid.uuid4().hex;work.mkdir(mode=0o700)
    base='https://cloud.debian.org/images/cloud/trixie/latest/'
    manifest=urllib.request.urlopen(base+'SHA512SUMS',timeout=30).read(100000).decode('ascii')
    image='debian-13-generic-amd64.qcow2';selected=[line for line in manifest.splitlines() if line.endswith(' '+image) or line.endswith(' *'+image)]
    require(len(selected)==1);expected=selected[0].split()[0];require(re.fullmatch('[a-fA-F0-9]{128}',expected))
    target=work/'base.qcow2';digest=hashlib.sha512();total=0
    with urllib.request.urlopen(base+image,timeout=30) as src,target.open('xb') as out:
        while block:=src.read(1024*1024):
            total+=len(block);require(total<=1024**3);digest.update(block);out.write(block)
    require(digest.hexdigest()==expected.lower());target.chmod(0o444)
    metadata={'prepared_at':time.time(),'work':str(work),'source':base+image,'sha512':digest.hexdigest(),'bytes':total,'image_authentication':'official HTTPS source and vendor SHA512; no detached signature claimed','qemu_version':run(['qemu-system-x86_64','--version']).splitlines()[0],'production_data_copied':False,'guest_booted':False}
    (work/'preparation.json').write_text(json.dumps(metadata,indent=2)+'\n');(work/'preparation.json').chmod(0o600)
    run(['chown','root:ait-recovery',str(work)]);work.chmod(0o750)
    print(json.dumps(metadata))
if __name__=='__main__':main()
