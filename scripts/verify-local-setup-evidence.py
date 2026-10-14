#!/usr/bin/env python3
"""Check source-bound Linux setup evidence without granting human/tag acceptance."""
import hashlib
import json
from pathlib import Path
import re
import shlex
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from protocol.evidence import read_evidence

RECEIPT = 'runs/2026-10-13-draft-privacy-clean-setup-linux.json'
CLI_INPUTS = ('.dockerignore', 'scripts/setup-local.py', 'scripts/aitrust.py',
              'scripts/check-assertion.py', 'protocol/assertions.py',
              'protocol/evidence.py', 'eval/requirements.lock', 'spec/assertion.schema.json')
CASES = ['actual_port_collision_preserves_running_installation',
         'actual_changed_ownership_refuses_all_removal',
         'actual_user_checker_finding_exit_2_without_input_execution',
         'synthetic_input_and_token_absent_from_application_logs',
         'actual_owned_stop_and_private_credential_retention',
         'actual_existing_private_installation_never_overwritten',
         'actual_missing_engine_refused_before_mutation',
         'actual_hash_locked_dependency_failure_without_credential',
         'actual_build_failure_owned_cleanup', 'actual_startup_failure_owned_cleanup']


def build_inputs(root=ROOT):
    """Bind the actual simple COPY graph; refuse unsupported external/build-stage inputs."""
    inputs = set(CLI_INPUTS)
    for role in ('gateway', 'anonymizer', 'evaluator'):
        name = 'services/' + role + '/Dockerfile'
        inputs.add(name)
        for line in (root / name).read_text().splitlines():
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if line.endswith('\\'):
                raise ValueError('Unsupported multiline container build input')
            parts = shlex.split(line)
            instruction = parts[0].upper()
            if instruction == 'FROM' and (len(parts) != 2 or not re.fullmatch(r'[^\s]+@sha256:[a-f0-9]{64}', parts[1])):
                raise ValueError('Container base identity is not pinned')
            if instruction == 'ADD':
                raise ValueError('Unbound container ADD input')
            if instruction != 'COPY':
                continue
            args = parts[1:]
            if args and args[0].startswith('--chmod='):
                args = args[1:]
            if len(args) < 2:
                raise ValueError('Invalid container COPY input')
            for source in args[:-1]:
                if (not re.fullmatch(r'[a-zA-Z0-9_./-]+', source)
                        or Path(source).is_absolute() or '..' in Path(source).parts):
                    raise ValueError('Unsupported container COPY input')
                inputs.add(source)
    for name in inputs:
        path = root / name
        if path.is_symlink() or not path.is_file() or any(
                parent.is_symlink() for parent in path.parents if parent != root and root in parent.parents):
            raise ValueError('Container/CLI build input is missing or linked')
    return {name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in sorted(inputs)}


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
    if row.get('source_binding_profile') != 'local-stack-complete-build-inputs/v1':
        raise ValueError('Incomplete setup build-input profile')
    expected = build_inputs(root)
    if row.get('sources') != expected:
        raise ValueError('Setup execution source changed')
    commit = row.get('source_commit')
    if not isinstance(commit, str) or not re.fullmatch(r'[a-f0-9]{40}', commit):
        raise ValueError('Invalid setup source commit')
    # A downloaded tree or an ordinary squash may not retain the execution
    # commit. Exact input bytes establish identity; the commit is an execution
    # reference, never a Git-history prerequisite or independent attestation.
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
            'source_files': len(expected), 'human_acceptance_requirement': 'F-142',
            'git_history_required': False,
            'independent_accuracy_evidence': False, 'collection_enabled': False,
            'scope': 'Source-bound cached-dependency Linux clean-clone setup; no outside-user or tag release acceptance.'}


if __name__ == '__main__':
    try:
        print(json.dumps(verify()))
    except (ValueError, OSError, TypeError, KeyError):
        print('Current bounded setup evidence is unavailable.', file=sys.stderr)
        raise SystemExit(1)
