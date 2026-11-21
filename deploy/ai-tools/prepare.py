#!/usr/bin/env python3
"""Prepare an exclusive private release. NEVER install/start global services."""
import argparse
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import re
import subprocess
import tarfile
import tempfile

FILES=('LICENSE','NOTICE','tools/tag_api.py','tools/remote_tag_server.py','scripts/remote-tag-server.py','scripts/check-tags.py','scripts/check-ps.py','scripts/worker_process.py','scripts/build-device-detector.py','services/evaluator/app.py','protocol/normalization.py','protocol/unicode15-data.json','integrations/mcp/requirements.lock','integrations/mcp/requirements.in')
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('ai_tools_render',HERE/'render.py');render=importlib.util.module_from_spec(spec);spec.loader.exec_module(render)

def prepare(source,commit,destination,provision=False):
    if type(commit) is not str or not re.fullmatch('[0-9a-f]{40}',commit):raise ValueError('Preparation refused')
    source=Path(source).resolve(strict=True);destination=Path(destination)
    if not destination.is_absolute() or destination.name!=commit or destination.parent.resolve(strict=True)!=destination.parent:raise ValueError('Preparation refused')
    if destination.exists() or destination.is_symlink():raise ValueError('Preparation refused')
    # Trusted operator-selected Git tree, with a finite path/size cohort. No worktree files.
    with tempfile.TemporaryFile() as capture:
        subprocess.run(['git','-C',str(source),'archive','--format=tar',commit,*FILES],stdout=capture,stderr=subprocess.DEVNULL,timeout=20,check=True)
        if os.fstat(capture.fileno()).st_size>2_000_000:raise ValueError('Preparation refused')
        capture.seek(0);archive=capture.read(2_000_001)
    captured={}
    with tarfile.open(fileobj=io.BytesIO(archive)) as t:
        for m in t:
            if m.isdir():continue
            if not m.isfile() or m.name not in FILES or m.name in captured or m.size>1_000_000:raise ValueError('Preparation refused')
            b=t.extractfile(m).read(m.size+1)
            if len(b)!=m.size:raise ValueError('Preparation refused')
            captured[m.name]=b
    if set(captured)!=set(FILES):raise ValueError('Preparation refused')
    # All source acceptance precedes any candidate writes. Existing paths are never adopted.
    destination.mkdir(mode=0o700);src=destination/'source';src.mkdir(mode=0o700)
    for name,b in captured.items():
        p=src/name;p.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
        with p.open('xb') as f:f.write(b)
    for name,text in {'Caddyfile':render.caddyfile(),**render.units(commit)}.items():
        with (destination/name).open('x') as f:f.write(text)
    manifest={'schema':'aitrust-ai-tools-prepared-release-1','commit':commit,'source_sha256':{n:hashlib.sha256(b).hexdigest() for n,b in sorted(captured.items())},'archive_sha256':hashlib.sha256(archive).hexdigest(),'caddy_package_version':render.CADDY_VERSION,'caddy_package_sha256':render.CADDY_SHA256,'activated':False}
    if provision:
        for argv in [[os.sys.executable,'-m','venv',str(destination/'venv')],[str(destination/'venv/bin/python'),'-m','pip','install','--disable-pip-version-check','--no-cache-dir','--index-url','https://pypi.org/simple','--only-binary=:all:','--require-hashes','-r',str(src/'integrations/mcp/requirements.lock')]]:
            p=subprocess.run(argv,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=150)
            if p.returncode:raise ValueError('Preparation unavailable')
        manifest['venv_provisioned']=True
    else:manifest['venv_provisioned']=False
    with (destination/'release.json').open('x') as f:json.dump(manifest,f,indent=2);f.write('\n')
    return manifest

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--commit',required=True);p.add_argument('--destination',type=Path,required=True);p.add_argument('--provision-venv',action='store_true');a=p.parse_args()
    try:r=prepare(a.source,a.commit,a.destination,a.provision_venv)
    except Exception:print(json.dumps({'pass':False,'reason':'preparation_unavailable'}));return 1
    print(json.dumps({'pass':True,'commit':r['commit'],'activated':False,'venv_provisioned':r['venv_provisioned']}));return 0
if __name__=='__main__':raise SystemExit(main())
