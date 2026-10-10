"""Inspectable selected-route hash inventory; no security or license certification."""
import argparse
import base64
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sys
from urllib.parse import urlsplit
import yaml
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from protocol.reports import write_report
from scripts.dependency_pins import python_lock, verify_inputs
BASE='python:3.12-slim@sha256:a6e34c598f2467ed0e9a8d349809fcd8b5c603269512df273a0bb1784edc11b1'

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def npm_lock(value):
    if value.get('lockfileVersion')!=3:raise ValueError('Unsupported npm lock version')
    rows=[]
    for path,row in value['packages'].items():
        if not path:continue
        version=row.get('version');integrity=row.get('integrity','');resolved=urlsplit(row.get('resolved',''))
        if not isinstance(integrity,str):raise ValueError('Missing or invalid npm integrity')
        if not isinstance(version,str) or not re.fullmatch(r'\d+\.\d+\.\d+(?:[-+][A-Za-z0-9.-]+)?',version):raise ValueError('Unpinned npm version')
        if resolved.scheme!='https' or resolved.hostname!='registry.npmjs.org' or resolved.username or resolved.query:raise ValueError('Unexpected npm artifact origin')
        try:
            alg,encoded=integrity.split('-',1);raw=base64.b64decode(encoded,validate=True)
            if alg not in ('sha512','sha256') or len(raw)!={'sha512':64,'sha256':32}[alg]:raise ValueError('Invalid npm integrity')
        except (ValueError,KeyError):raise ValueError('Missing or invalid npm integrity') from None
        rows.append({'path':path,'version':version,'integrity':integrity,'resolved':row['resolved']})
    if not rows:raise ValueError('Empty npm lock')
    return rows

def verify(root=ROOT):
    compose=yaml.safe_load((root/'deploy/docker-compose.yml').read_text())
    active={name for name,row in compose['services'].items() if not row.get('profiles')}
    if active!={'gateway','anonymizer','evaluator'}:raise ValueError('Uninventoried active service')
    files={};py={};npm={}
    for name in sorted(active):
        path=Path('services')/name/'Dockerfile';text=(root/path).read_text()
        if text.splitlines()[0]!='FROM '+BASE or 'pip install --no-cache-dir --require-hashes -r requirements.lock' not in text:raise ValueError('Mutable base or unhashed active installation')
        files[str(path)]=digest(root/path)
    for name in ('gateway','anonymizer','evaluator'):
        path=Path('services')/name/'requirements.lock';py[str(path)]=python_lock((root/path).read_text());files[str(path)]=digest(root/path)
    path=Path('eval/requirements.lock');py[str(path)]=python_lock((root/path).read_text());files[str(path)]=digest(root/path)
    for lock_name, locked in py.items():
        parent=Path(lock_name).parent
        manifest=parent/'requirements.txt';freeze=parent/'requirements.freeze'
        verify_inputs((root/manifest).read_text(), (root/lock_name).read_text(), (root/freeze).read_text() if str(parent).startswith('services/') else None)
        files[str(manifest)]=digest(root/manifest)
        if str(parent).startswith('services/'):files[str(freeze)]=digest(root/freeze)
    eval_names={r['name'] for r in py[str(path)]}
    if not {'jsonschema','rfc3339-validator','six','pyyaml','pytest'}<=eval_names:raise ValueError('Required format/test dependencies missing')
    # CI uses one environment for gateway and evaluation checks. Individually valid
    # locks must also be jointly satisfiable; sequential installation can hide drift.
    gateway_pins={r['name']:r['requirement'] for r in py['services/gateway/requirements.lock']}
    for row in py['eval/requirements.lock']:
        if row['name'] in gateway_pins and row['requirement']!=gateway_pins[row['name']]:
            raise ValueError('Gateway and evaluation lock pins conflict')
    for prefix in ('','site/'):
        path=Path(prefix+'package-lock.json');value=json.loads((root/path).read_text());npm[str(path)]=npm_lock(value);files[str(path)]=digest(root/path)
        package=json.loads((root/(prefix+'package.json')).read_text())
        for group in ('dependencies','devDependencies'):
            for name,version in package.get(group,{}).items():
                if value['packages'][''].get(group,{}).get(name)!=version or value['packages'].get('node_modules/'+name,{}).get('version')!=version:raise ValueError('npm manifest and lock disagree')
    return {'captured_at':datetime.now(timezone.utc).isoformat(),'pass':True,'active_services':sorted(active),
            'base_index':BASE,'files':files,'python':py,'npm':npm,
            'model_asset_sealing':'services/anonymizer/model_identity.py; separately exercised at startup',
            'inactive_unlocked_proposals':['registry'],'installations_executed_by_this_command':False,
            'license_or_security_certification':False,'independent_tag_validation':False}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--report');a=p.parse_args();r=verify()
    if a.report:write_report(a.report,r)
    print(json.dumps({'pass':r['pass'],'python_packages':{p:len(v) for p,v in r['python'].items()},'npm_packages':{p:len(v) for p,v in r['npm'].items()}}))
