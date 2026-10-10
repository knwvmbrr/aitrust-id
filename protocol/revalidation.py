"""Source-bound engineering checks, separate from independent accuracy evidence."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
COMMON = ('eval/revalidation.json','protocol/revalidation.py','scripts/revalidate.py','protocol/evidence.py')
CAPABILITIES = {'PS','PII_REDACTED','protocol','extension','website'}

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def load(root=ROOT):
    data=json.loads((root/'eval/revalidation.json').read_text())
    if data.get('schema_version')!=1 or data.get('kind')!='engineering_revalidation' or data.get('independent_accuracy_evidence') is not False or set(data['capabilities'])!=CAPABILITIES:
        raise ValueError('Unsupported revalidation manifest')
    for row in data['capabilities'].values():
        if not row['patterns'] or not row['commands']:
            raise ValueError('Revalidation requires sources and executable checks')
        for pattern in row['patterns']:
            if not isinstance(pattern,str) or pattern.startswith('/') or '..' in Path(pattern).parts:
                raise ValueError('Unsafe source pattern')
        for command in row['commands']:
            if not isinstance(command,list) or len(command)<2 or command[0] not in ('{python}','node') or any(not isinstance(a,str) or not a or len(a)>512 or '\x00' in a for a in command):
                raise ValueError('Unsupported check command')
            if command[1]=='-m':
                if command[0]!='{python}' or command[2:3]!=['pytest']:
                    raise ValueError('Unsupported Python module')
            elif not re.fullmatch(r'scripts/[a-z0-9-]+\.(?:py|cjs)',command[1]):
                raise ValueError('Checks must be repository scripts')
    return data

def fingerprint(capability,root=ROOT):
    data=load(root)
    if capability not in CAPABILITIES:
        raise ValueError('Unknown capability')
    paths=set(COMMON)
    for pattern in data['capabilities'][capability]['patterns']:
        found=[]
        for p in root.glob(pattern):
            if p.is_symlink() or any(parent.is_symlink() for parent in p.parents if parent!=root and root in parent.parents):
                raise ValueError('Source symlink refused')
            if p.is_file() and '__pycache__' not in p.parts:
                found.append(p.relative_to(root).as_posix())
        if not found:
            raise ValueError('Missing required source pattern')
        paths.update(found)
    for name in paths:
        p=root/name
        if p.is_symlink() or any(parent.is_symlink() for parent in p.parents if parent!=root and root in parent.parents):
            raise ValueError('Source symlink refused')
    inventory={name:sha((root/name).read_bytes()) for name in sorted(paths)}
    return {'capability':capability,'sources':inventory,
            'sha256':sha(json.dumps(inventory,sort_keys=True,separators=(',',':')).encode()),
            'commands':data['capabilities'][capability]['commands']}

def execute(capability,root=ROOT,runner=subprocess.run):
    before=fingerprint(capability,root);checks=[]
    for args in before['commands']:
        command=[sys.executable if arg=='{python}' else arg for arg in args]
        try:
            result=runner(command,cwd=root,capture_output=True,timeout=600,check=False)
            checks.append({'command':args,'exit':result.returncode,
                           'stdout_sha256':sha(result.stdout),'stderr_sha256':sha(result.stderr)})
        except (OSError,subprocess.TimeoutExpired):
            checks.append({'command':args,'exit':None,'failure':'check_unavailable_or_timed_out'})
            break
        if result.returncode:break
    stable=before==fingerprint(capability,root)
    passed=stable and len(checks)==len(before['commands']) and all(type(c['exit']) is int and c['exit']==0 for c in checks)
    return {'schema_version':1,'kind':'engineering_revalidation','captured_at':datetime.now(timezone.utc).isoformat(),
            'pass':passed,'source_unchanged_during_execution':stable,'fingerprint':before,'checks':checks,
            'independent_accuracy_evidence':False,'release_approved':False}

def assess(receipt,capability,root=ROOT):
    failures=[]
    if receipt.get('schema_version')!=1 or receipt.get('kind')!='engineering_revalidation' or receipt.get('pass') is not True or receipt.get('source_unchanged_during_execution') is not True or receipt.get('independent_accuracy_evidence') is not False or receipt.get('release_approved') is not False:
        failures.append('invalid_or_failed_receipt')
    try:
        date=datetime.fromisoformat(receipt['captured_at'])
        if date.tzinfo is None or date>datetime.now(timezone.utc):failures.append('invalid_execution_date')
        current=fingerprint(capability,root)
        if receipt['fingerprint']!=current:failures.append('source_dependency_fixture_or_check_changed')
        checks=receipt['checks']
        if [c['command'] for c in checks]!=current['commands'] or any(type(c['exit']) is not int or c['exit']!=0 or any(not re.fullmatch(r'[a-f0-9]{64}',c[k]) for k in ('stdout_sha256','stderr_sha256')) for c in checks):
            failures.append('incomplete_execution_evidence')
    except (KeyError,ValueError,TypeError,OSError):failures.append('invalid_or_unavailable_evidence')
    return {'pass':not failures,'capability':capability,'revalidation_required':bool(failures),
            'failures':failures,'independent_accuracy_evidence':False,'release_approved':False}
