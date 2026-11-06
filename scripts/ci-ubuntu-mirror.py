#!/usr/bin/env python3
"""Prepare a signed canonical archive configuration for disposable Ubuntu CI only."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
from urllib.parse import urlsplit

KEY='/usr/share/keyrings/ubuntu-archive-keyring.gpg'
FIELDS={'types','uris','suites','components','signed-by','architectures','languages'}
SUITES={'noble','noble-updates','noble-backports','noble-security'}

def require(value):
    if not value:raise ValueError('CI archive preparation refused')

def transform(raw):
    require(type(raw) is bytes and 0<len(raw)<=65536)
    text=raw.decode('ascii');require('\r' not in text and '\x00' not in text)
    lines=text.splitlines(keepends=True);blocks=[];fields={};uri_lines=[]
    for index,line in enumerate(lines+['\n']):
        value=line.strip()
        if not value:
            if fields:blocks.append((fields,uri_lines));fields={};uri_lines=[]
            continue
        if value.startswith('#'):continue
        require(not line[0].isspace() and ':' in line)
        key,content=line.split(':',1);key=key.lower();content=content.strip()
        require(key in FIELDS and key not in fields and content)
        fields[key]=content
        if key=='uris':uri_lines.append(index)
    require(1<=len(blocks)<=4)
    changed=False
    for fields,indices in blocks:
        require({'types','uris','suites','components','signed-by'}<=fields.keys())
        require(fields['signed-by']==KEY and set(fields['types'].split())<= {'deb','deb-src'} and 'deb' in fields['types'].split())
        require(set(fields['suites'].split())<=SUITES and set(fields['components'].split())<= {'main','restricted','universe','multiverse'} and 'main' in fields['components'].split())
        values=[]
        for value in fields['uris'].split():
            if value=='mirror+file:/etc/apt/apt-mirrors.txt':
                changed=True;values.append('https://archive.ubuntu.com/ubuntu');continue
            url=urlsplit(value)
            require(url.scheme in ('http','https') and url.netloc in ('azure.archive.ubuntu.com','archive.ubuntu.com','security.ubuntu.com')
                    and url.path.rstrip('/')=='/ubuntu' and not url.query and not url.fragment)
            replacement='https://archive.ubuntu.com/ubuntu' if url.netloc in ('azure.archive.ubuntu.com','archive.ubuntu.com') else value
            changed=changed or replacement!=value;values.append(replacement)
        index=indices[0];prefix=lines[index].split(':',1)[0]
        lines[index]=prefix+': '+' '.join(values)+ ('\n' if lines[index].endswith('\n') else '')
    output=''.join(lines).encode('ascii');require(len(output)<=65536)
    return output,changed

def context(env,release):
    require(env.get('GITHUB_ACTIONS')=='true' and env.get('AITRUST_CI_RUNNER_ENV')=='github-hosted'
            and env.get('AITRUST_CI_RUNNER_OS')=='Linux')
    fields={}
    for line in release.splitlines():
        if '=' in line:
            key,value=line.split('=',1);require(key not in fields);fields[key]=value.strip('"')
    require(fields.get('ID')=='ubuntu' and fields.get('VERSION_ID')=='24.04')

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',required=True,type=Path);a=p.parse_args(argv)
    try:
        # Environment markers prevent accidental host use, not a forged-root threat.
        context(os.environ,Path('/etc/os-release').read_text() if sys.platform=='linux' else '')
        temp=Path(os.environ['AITRUST_CI_SOURCE_DIR']);require(temp.is_absolute() and not temp.is_symlink())
        info=temp.stat();require(stat.S_ISDIR(info.st_mode) and info.st_uid==os.getuid() and not info.st_mode&0o022)
        require(a.output.is_absolute() and a.output.name=='aitrust-ubuntu.sources' and not a.output.parent.is_symlink() and a.output.parent.resolve()==temp.resolve())
        source=Path('/etc/apt/sources.list.d/ubuntu.sources')
        fd=os.open(source,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
        with os.fdopen(fd,'rb') as handle:
            before=os.fstat(handle.fileno());require(stat.S_ISREG(before.st_mode) and before.st_uid==0 and not before.st_mode&0o022 and before.st_size<=65536)
            raw=handle.read(65537);after=os.fstat(handle.fileno());require((before.st_size,before.st_mtime_ns,before.st_ctime_ns)==(after.st_size,after.st_mtime_ns,after.st_ctime_ns))
        output,changed=transform(raw)
        fd=os.open(a.output,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
        with os.fdopen(fd,'wb') as handle:handle.write(output);handle.flush();os.fsync(handle.fileno())
        print(json.dumps({'pass':True,'mirror_changed':changed,'input_sha256':hashlib.sha256(raw).hexdigest(),'output_sha256':hashlib.sha256(output).hexdigest(),'signing_key_retained':True,'system_files_modified_by_helper':False}));return 0
    except (OSError,ValueError,KeyError,UnicodeError):
        print('CI archive preparation refused; no system source was modified by this helper.',file=sys.stderr);return 2
if __name__=='__main__':raise SystemExit(main())
