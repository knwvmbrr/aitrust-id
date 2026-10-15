"""Versioned interoperability cases; never an accuracy or certification gate."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys

from protocol.evidence import unique, reject, finite
from scripts.source_snapshot import read_file
from scripts.worker_process import run_worker, WorkerOutputLimit

ROOT = Path(__file__).resolve().parents[1]
VECTORS = 'eval/conformance/assertion-v1.json'
VECTOR_SHA256 = 'aa30aef56eeff6657b68b315dc4f64b1756ee9eb8c9c54db76159a633c09b745'
PROFILE = 'aitrust-assertion-vectors/1.0.0'
EXITS = {'accepted': 0, 'invalid': 1, 'unsupported': 2, 'unavailable': 3}
SOURCES = (VECTORS, 'tools/conformance_vectors.py', 'scripts/check-conformance-vectors.py',
           'scripts/worker_process.py', 'scripts/source_snapshot.py', 'protocol/evidence.py',
           'scripts/check-assertion.py', 'protocol/assertions.py', 'spec/assertion.schema.json',
           'extension/src/shared/contract.js', 'tests/test_conformance_vectors.py')


def decode(raw):
    value = json.loads(raw.decode('utf-8', 'strict'), object_pairs_hook=unique, parse_constant=reject)
    finite(value)
    return value


def load(root=ROOT):
    raw = read_file(root / VECTORS, 65_536)
    if hashlib.sha256(raw).hexdigest() != VECTOR_SHA256:
        raise ValueError('Versioned vector identity changed')
    value = decode(raw)
    if (set(value) != {'profile', 'spec_version', 'synthetic_only', 'independent_accuracy_evidence', 'cases'}
            or value['profile'] != PROFILE or value['spec_version'] != '0.1.0'
            or value['synthetic_only'] is not True or value['independent_accuracy_evidence'] is not False
            or type(value['cases']) is not list or len(value['cases']) != 14):
        raise ValueError('Vector contract refused')
    names = set()
    for case in value['cases']:
        if (type(case) is not dict or set(case) != {'id', 'raw', 'expected'}
                or type(case['id']) is not str or case['id'] in names
                or not case['id'].isascii() or not case['id'].replace('-', '').isalnum()
                or type(case['raw']) is not str or not 0 < len(case['raw'].encode()) <= 8192
                or type(case['expected']) is not dict or set(case['expected']) != {'schema', 'extension'}
                or any(status not in EXITS for status in case['expected'].values())):
            raise ValueError('Vector case refused')
        names.add(case['id'])
    return value


def sources(root=ROOT):
    return {name: hashlib.sha256(read_file(root / name, 2_000_000)).hexdigest() for name in SOURCES}


def run(implementation=None, profiles=('schema', 'extension'), root=ROOT, supervisor=run_worker):
    if (type(profiles) is not tuple or not profiles or len(set(profiles)) != len(profiles)
            or not set(profiles) <= {'schema', 'extension'}):
        raise ValueError('Profile refused')
    command = [sys.executable, str(root / 'scripts/check-assertion.py')] if implementation is None else implementation
    if (type(command) is not list or not 1 <= len(command) <= 32
            or any(type(v) is not str or not 0 < len(v) <= 4096 or '\0' in v for v in command)):
        raise ValueError('Implementation command refused')
    before = sources(root)
    vectors = load(root)
    checks = []
    for profile in profiles:
        for case in vectors['cases']:
            row = {'case': case['id'], 'profile': profile, 'expected': case['expected'][profile], 'pass': False}
            try:
                result = supervisor([*command, '--profile', profile], input=case['raw'].encode(),
                                    timeout=3, output_limit=8192)
                row['exit'] = result.returncode
                row['response_sha256'] = hashlib.sha256(result.stdout).hexdigest()
                value = decode(result.stdout)
                if (type(value) is not dict or value.get('status') not in EXITS
                        or value.get('profile') != profile or value.get('supported_version') != '0.1.0'
                        or value.get('offline') is not True
                        or any(value.get(k) is not False for k in
                               ('signature_verified', 'independent_accuracy_verified', 'certification'))):
                    raise ValueError('Implementation response refused')
                row['observed'] = value['status']
                row['pass'] = (value['status'] == row['expected']
                               and type(result.returncode) is int
                               and result.returncode == EXITS[row['expected']])
                if not row['pass']:
                    row['failure'] = 'unexpected_status_or_exit'
            except subprocess.TimeoutExpired:
                row['failure'] = 'implementation_timeout'
            except WorkerOutputLimit:
                row['failure'] = 'implementation_output_limit'
            except OSError:
                row['failure'] = 'implementation_unavailable'
            except (ValueError, TypeError, RecursionError):
                row['failure'] = 'invalid_implementation_response'
            checks.append(row)
    stable = before == sources(root)
    return {'schema_version': 1, 'kind': 'assertion_conformance_vectors',
            'captured_at': datetime.now(timezone.utc).isoformat(), 'vector_profile': PROFILE,
            'sources': before, 'source_unchanged_during_execution': stable,
            'implementation': 'reference' if implementation is None else 'owner_selected_executable',
            'checks': checks, 'cases_run': len(checks), 'cases_passed': sum(c['pass'] for c in checks),
            'pass': stable and len(checks) == len(profiles) * len(vectors['cases']) and all(c['pass'] for c in checks),
            'independent_accuracy_evidence': False, 'outside_person_acceptance': False,
            'certification': False, 'release_approved': False}
