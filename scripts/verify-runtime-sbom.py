"""Verify observed SPDX artifact identities, not license clearance or signed release."""
import argparse
from datetime import datetime, timezone
import hashlib
from pathlib import Path
import re
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from protocol.evidence import read_evidence
from protocol.reports import write_report
ROLES = ['gateway', 'evaluator', 'anonymizer']
SOURCES = ['.dockerignore', 'deploy/docker-compose.yml'] + [
    f'services/{role}/{name}' for role in ROLES
    for name in ['Dockerfile', 'requirements.lock']]


def verify(root=ROOT):
    m = read_evidence(root / 'eval/dependencies/runtime-sbom.json')
    if (set(m) != {'schema_version', 'kind', 'captured_at', 'scanner',
        'scanner_archive_sha256', 'scanner_signed_identity_verified', 'license_cleared',
        'release_signed', 'platform', 'images', 'sources', 'inventory_evidence'}
        or m['schema_version'] != 1 or m['kind'] != 'unsigned_observed_runtime_sbom'
        or m['scanner'] != 'syft 1.54.1' or m['platform'] != 'linux/amd64'
        or any(m[k] is not False for k in ['scanner_signed_identity_verified',
                                          'license_cleared', 'release_signed'])
        or m['scanner_archive_sha256'] != 'c069905b391cc4c20a5ba65ad5c10be2a7ba074f8ea6ad203e24d14e303dad47'
        or not isinstance(m['images'], list) or [r.get('role') for r in m['images']] != ROLES):
        raise ValueError('Invalid or overclaimed observed SBOM manifest')
    when = datetime.fromisoformat(m['captured_at'])
    if when.tzinfo is None or when > datetime.now(timezone.utc):
        raise ValueError('Invalid inventory date')
    expected = {}
    for name in SOURCES:
        read_path = root / name
        if read_path.is_symlink() or any(parent.is_symlink() for parent in read_path.parents):
            raise ValueError('Source symlink refused')
        expected[name] = hashlib.sha256(read_path.read_bytes()).hexdigest()
    if m['sources'] != expected:
        raise ValueError('SBOM package/build inputs changed; rescan required')
    if m['inventory_evidence'] != 'runs/2026-10-10-runtime-license-inventory.json':
        raise ValueError('Invalid observed inventory evidence path')
    evidence = read_evidence(root / m['inventory_evidence'])
    if evidence.get('scan_completed') is not True or evidence.get('licenses_cleared') is not False:
        raise ValueError('Missing or overclaimed actual inventory')
    packages = 0
    for row, observed in zip(m['images'], evidence['images']):
        if (set(row) != {'role','artifact','sha256','image_id','manifest_digest','packages'}
            or row['artifact'] != f"sbom/runtime/{row['role']}-linux-amd64.spdx.json"
            or any(not isinstance(row[k],str) or not re.fullmatch('[a-f0-9]{64}',row[k])
                   for k in ['sha256','image_id','manifest_digest'])
            or type(row['packages']) is not int or row['packages'] < 2):
            raise ValueError('Invalid SBOM artifact binding')
        p = root / row['artifact']
        document = read_evidence(p, limit=4_000_000)
        if hashlib.sha256(p.read_bytes()).hexdigest() != row['sha256']:
            raise ValueError('SBOM bytes changed')
        if (document.get('spdxVersion') != 'SPDX-2.3'
            or document.get('dataLicense') != 'CC0-1.0'
            or 'Tool: syft-1.54.1' not in document.get('creationInfo',{}).get('creators',[])
            or len(document.get('packages',[])) != row['packages']):
            raise ValueError('Invalid observed SPDX inventory')
        subjects = [x for x in document['packages'] if x.get('primaryPackagePurpose') == 'CONTAINER']
        ids = [x.get('SPDXID') for x in document['packages']]
        if len(ids) != len(set(ids)) or any(not isinstance(x,str) for x in ids):
            raise ValueError('Duplicate or missing package identities')
        if (len(subjects) != 1 or subjects[0].get('name') != 'aitrust-'+row['role']
            or subjects[0].get('versionInfo') != row['image_id']
            or subjects[0].get('checksums') != [{'algorithm':'SHA256','checksumValue':row['manifest_digest']}]
            or observed.get('role') != row['role'] or observed.get('image_id') != row['image_id']
            or observed.get('spdx_sha256') != row['sha256']
            or observed.get('packages') != row['packages']-1):
            raise ValueError('Observed image identity differs')
        packages += row['packages']-1
    if len(evidence['images']) != 3: raise ValueError('Incomplete observed inventory')
    return {'captured_at':datetime.now(timezone.utc).isoformat(),'pass':True,
        'images':3,'package_occurrences':packages,'sbom_identity_verified':True,
        'license_cleared':False,'release_signed':False,'scanner_signed_identity_verified':False,
        'vulnerabilities_assessed':False,'tag_release_approved':False,
        'coverage':'Observed Linux amd64 image inventory only; not complete client/build/license coverage'}


if __name__ == '__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path);a=p.parse_args()
    try:
        r=verify()
        if a.output:write_report(a.output,r)
        import json
        print(json.dumps(r))
    except (ValueError,KeyError,TypeError,OSError) as error:
        print('SBOM verification refused: '+str(error),file=sys.stderr)
        raise SystemExit(1)
