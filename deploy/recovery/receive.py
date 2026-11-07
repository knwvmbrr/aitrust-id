#!/usr/bin/env python3
"""Receive only an encrypted backup archive for a verified offline recovery guest."""
import argparse,hashlib,json,os,re,stat,subprocess,sys,tarfile
from pathlib import Path,PurePosixPath
PARENT=Path('/var/lib/aitrust-id/recovery-vm')
def require(ok):
    if not ok:raise ValueError('Recovery archive refused')
def selected(path):
    require(os.geteuid()==0 and path.parent==PARENT and re.fullmatch('[a-f0-9]{32}',path.name))
    for p in [PARENT,path]:
        s=p.lstat();require(stat.S_ISDIR(s.st_mode) and s.st_uid==0 and not s.st_mode&0o022)
    row=json.loads((path/'isolation.json').read_text());pid=int(row['pid']);require(pid>1)
    actual=os.stat('/proc/'+str(pid)+'/ns/net');require(actual.st_ino==row['network_inode'] and actual.st_ino!=os.stat('/proc/1/ns/net').st_ino)
    r=subprocess.run(['nsenter','-t',str(pid),'-n','--','ip','-j','link'],capture_output=True,check=True,timeout=10)
    require([x['ifname'] for x in json.loads(r.stdout)]==['lo'])
    return path

def receive(work):
    target=work/'encrypted-backup';target.mkdir(mode=0o700)
    total=0;files=0;manifest=hashlib.sha256()
    try:
        with tarfile.open(fileobj=sys.stdin.buffer,mode='r|') as archive:
            for member in archive:
                name=member.name
                while name.startswith('./'):name=name[2:]
                if name in ('','.'):continue
                parts=PurePosixPath(name).parts
                require(not name.startswith('/') and '\\' not in name and all(x not in ('..','.') for x in parts) and len(name)<=500)
                require(member.isdir() or member.isfile());require(0<=member.size<=256*1024**2)
                files+=1;total+=member.size;require(files<=100000 and total<=2*1024**3)
                dest=target/name;dest.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
                if member.isdir():dest.mkdir(mode=0o700,exist_ok=True);continue
                source=archive.extractfile(member);require(source is not None)
                fd=os.open(dest,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600);h=hashlib.sha256();seen=0
                with os.fdopen(fd,'wb') as out:
                    while chunk:=source.read(1024*1024):seen+=len(chunk);require(seen<=member.size);h.update(chunk);out.write(chunk)
                require(seen==member.size);manifest.update(name.encode()+b'\0'+h.digest())
        # Finish consuming tar padding before the SSH transport closes.
        while sys.stdin.buffer.read(1024*1024):pass
        require((target/'backup/aitrustid/backup.info').is_file())
        proof={'received_at':__import__('time').time(),'files':files,'encrypted_archive_bytes':total,'inventory_sha256':manifest.hexdigest(),'offline_guest_verified_before_receive':True,'decryption_material_received':False}
        (work/'collection.json').write_text(json.dumps(proof,indent=2)+'\n');(work/'collection.json').chmod(0o600);return proof
    except BaseException:
        import shutil
        shutil.rmtree(target);raise

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--work',type=Path,required=True);a=p.parse_args();print(json.dumps(receive(selected(a.work))))
if __name__=='__main__':main()
