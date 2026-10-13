#!/usr/bin/env python3
"""Check source-bound Linux setup evidence without granting human/tag acceptance."""
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from protocol.evidence import read_evidence

RECEIPT = 'runs/2026-10-13-one-command-linux-setup.json'
SOURCES = ('scripts/setup-local.py', 'scripts/aitrust.py', 'services/gateway/app.py',
           'services/anonymizer/app.py', 'services/evaluator/app.py',
           'eval/requirements.lock', 'spec/assertion.schema.json')
CASES = ['actual_port_collision_preserves_running_installation',
         'actual_changed_ownership_refuses_all_removal',
         'actual_user_checker_finding_exit_2_without_input_execution',
         'synthetic_input_and_token_absent_from_application_logs',
         'actual_owned_stop_and_private_credential_retention',
         'actual_existing_private_installation_never_overwritten',
         'actual_missing_engine_refused_before_mutation',
         'actual_hash_locked_dependency_failure_without_credential',
         'actual_build_failure_owned_cleanup', 'actual_startup_failure_owned_cleanup']


def verify(row=None, root=ROOT):
    if row is None:
        row = read_evidence(root / RECEIPT)
    if not isinstance(row, dict):
        raise ValueError('Invalid setup receipt')
    for key in ('pass', 'actual_clean_clone', 'actual_one_command_start',
                'real_pipeline_and_schema_verified', 'loopback_only',
                'credential_permissions_0600', 'state_permissions_0700', 'source_unchanged',
                'original_staging_restored_same_ids_images_configuration'):
        if row.get(key) is not True:
            raise ValueError('Missing actual setup acceptance')
    for key in ('original_input_executed', 'collection_enabled',
                'independent_accuracy_evidence', 'human_acceptance_complete', 'physical_phone_tested'):
        if row.get(key) is not False:
            raise ValueError('Setup receipt overclaims acceptance')
    if row.get('actual_container_engine') != 'Podman' or row.get('initial_dependency_downloads_cached') is not True:
        raise ValueError('Unsupported setup evidence scope')
    if row.get('cases') != CASES or type(row.get('case_count')) is not int or row['case_count'] != 10:
        raise ValueError('Missing actual setup failure controls')
    expected = {name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in SOURCES}
    if row.get('sources') != expected:
        raise ValueError('Setup execution source changed')
    commit = row.get('source_commit')
    if not isinstance(commit, str) or not re.fullmatch(r'[a-f0-9]{40}', commit):
        raise ValueError('Invalid setup source commit')
    result = subprocess.run(['git', 'merge-base', '--is-ancestor', commit, 'HEAD'], cwd=root, capture_output=True)
    if result.returncode:
        raise ValueError('Setup execution commit is not in current history')
    services = row.get('services', {})
    if set(services) != {'gateway', 'anonymizer', 'evaluator'}:
        raise ValueError('Missing actual service identity')
    for role, service in services.items():
        if (service.get('source_sha256') != expected['services/' + role + '/app.py']
                or service.get('uid') != 10001 or service.get('pids_limit') != 128
                or service.get('memory_mib') != (1024 if role == 'anonymizer' else 256)
                or any(service.get(key) is not True for key in ('read_only', 'capabilities_dropped', 'no_new_privileges'))):
            raise ValueError('Actual service safety/identity changed')
    return {'pass': True, 'requirement': 'F-105', 'actual_failure_cases': 10,
            'source_files': len(SOURCES), 'human_acceptance_requirement': 'F-142',
            'independent_accuracy_evidence': False, 'collection_enabled': False,
            'scope': 'Source-bound cached-dependency Linux clean-clone setup; no outside-user or tag release acceptance.'}


if __name__ == '__main__':
    try:
        print(json.dumps(verify()))
    except (ValueError, OSError, TypeError, KeyError):
        print('Current bounded setup evidence is unavailable.', file=sys.stderr)
        raise SystemExit(1)
