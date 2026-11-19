#!/usr/bin/env python3
"""Build deterministic exact-source MT browser input; no package installation."""
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tools.mt_device import SOURCE_FILES, METHODS

LICENSE_FILES=('LICENSE','NOTICE','eval/vectors/unicode/LICENSE.txt')
ALL_FILES=(*SOURCE_FILES,*LICENSE_FILES)


def write(path,raw):
    if any(p.is_symlink() for p in [path,*path.parents]):raise ValueError('Build symlink refused.')
    if path.exists() and path.read_bytes()==raw:return
    path.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent,delete=False) as f:
        temporary=Path(f.name);f.write(raw);f.flush();os.fsync(f.fileno())
    try:temporary.chmod(0o644);os.replace(temporary,path)
    finally:temporary.unlink(missing_ok=True)


def build(root=ROOT):
    root=Path(root);files={p:(root/p).read_bytes() for p in ALL_FILES}
    if any(len(raw)>200000 for raw in files.values()):raise ValueError('Unexpected MT source size.')
    sources={p:hashlib.sha256(raw).hexdigest() for p,raw in files.items()}
    value={'format':'mt-device-source-bundle/v1','files':{p:raw.decode('utf-8','strict') for p,raw in files.items()}}
    raw=(json.dumps(value,ensure_ascii=True,sort_keys=True,separators=(',',':'))+'\n').encode()
    if len(raw)>1000000:raise ValueError('MT source bundle exceeds limit.')
    digest=hashlib.sha256(raw).hexdigest();path='/mt-device/method-'+digest+'.json'
    manifest={'format':'mt-device-source-manifest/v1','runtime':'314.0.7',
       'runtime_path':'/device/runtime-314.0.7/','path':path,'bundle_sha256':digest,
       'bundle_bytes':len(raw),'sources':sources,'methods':METHODS,
       'normalization_id':'NFC-Unicode-15.0.0/v1','max_codepoints':8000,'max_bytes':32000}
    notices=b'AI Trust ID MT phrase explorer - original source notices\n\n'
    for name in LICENSE_FILES:notices+=('----- '+name+' -----\n').encode()+files[name]+b'\n'
    write(root/('site/public'+path),raw)
    write(root/'site/public/mt-device/notices.txt',notices)
    write(root/'site/src/mt-device-manifest.json',(json.dumps(manifest,indent=2)+'\n').encode())
    return manifest


if __name__=='__main__':print(json.dumps(build(),sort_keys=True))
