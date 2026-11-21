#!/usr/bin/env python3
"""Extract one hash-pinned official Debian package into a NEW private directory."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
HERE=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('render',HERE/'render.py');r=importlib.util.module_from_spec(s);s.loader.exec_module(r)

def fetch(destination):
    if os.getuid()==0:raise ValueError('Nonroot temporary extraction required')
    destination=Path(destination)
    if not destination.is_absolute() or destination.parent.resolve(strict=True)!=destination.parent or destination.exists() or destination.is_symlink():raise ValueError('Refused')
    # apt metadata is supplied by the host's already configured signed Debian indexes.
    p=subprocess.run(['apt-cache','show','caddy='+r.CADDY_VERSION],capture_output=True,timeout=15,check=True)
    if len(p.stdout)>32768:raise ValueError('Refused')
    fields=dict(line.split(': ',1) for line in p.stdout.decode().splitlines() if ': ' in line and not line.startswith(' '))
    if fields.get('SHA256')!=r.CADDY_SHA256 or fields.get('Architecture')!='amd64' or fields.get('Version')!=r.CADDY_VERSION or fields.get('Filename')!='pool/main/c/caddy/caddy_2.11.2-1~bpo13+1_amd64.deb' or fields.get('Size')!='11642740':raise ValueError('Refused')
    destination.mkdir(mode=0o700)
    # --print-uris asserts the configured download resolves to official Debian origin;
    # downloaded bytes must independently equal the pinned signed-index SHA.
    uri=subprocess.run(['apt-get','--print-uris','download','caddy='+r.CADDY_VERSION],cwd=destination,capture_output=True,timeout=15,check=True).stdout.decode()
    import shlex,urllib.parse
    rows=[shlex.split(x) for x in uri.splitlines() if x.startswith("'")]
    if len(rows)!=1 or urllib.parse.urlsplit(rows[0][0]).hostname not in ('deb.debian.org','security.debian.org') or urllib.parse.urlsplit(rows[0][0]).scheme not in ('http','https'):raise ValueError('Refused')
    p=subprocess.run(['apt-get','download','caddy='+r.CADDY_VERSION],cwd=destination,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=90)
    if p.returncode:raise ValueError('Download unavailable')
    packages=list(destination.glob('*.deb'))
    if len(packages)!=1 or packages[0].is_symlink() or packages[0].stat().st_size!=11642740:raise ValueError('Refused')
    digest=hashlib.sha256(packages[0].read_bytes()).hexdigest()
    if digest!=r.CADDY_SHA256:raise ValueError('Refused')
    control=subprocess.run(['dpkg-deb','-f',str(packages[0]),'Package','Version','Architecture'],capture_output=True,timeout=10,check=True).stdout.decode()
    if control!='Package: caddy\nVersion: '+r.CADDY_VERSION+'\nArchitecture: amd64\n':raise ValueError('Refused')
    out=destination/'extracted';subprocess.run(['dpkg-deb','-x',str(packages[0]),str(out)],capture_output=True,timeout=15,check=True)
    binary=out/'usr/bin/caddy'
    version=subprocess.run([str(binary),'version'],capture_output=True,timeout=5,check=True).stdout.decode().strip()
    if not version.startswith('2.11.2'):raise ValueError('Refused')
    report={'pass':True,'package':'caddy','version':r.CADDY_VERSION,'architecture':'amd64','package_sha256':digest,'binary_sha256':hashlib.sha256(binary.read_bytes()).hexdigest(),'official_debian_origin':True,'signed_host_apt_metadata_matched':True,'maintainer_scripts_executed':False,'global_package_installed':False}
    (destination/'package-proof.json').write_text(json.dumps(report,indent=2)+'\n')
    return report
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--destination',type=Path,required=True);a=p.parse_args()
    try:print(json.dumps(fetch(a.destination)))
    except Exception:print('{"pass":false,"reason":"caddy_extraction_unavailable"}');raise SystemExit(1)
