"""Validate the bound current inventories against the pinned SPDX 2.3.1 schema."""
import argparse
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from protocol.evidence import read_evidence
from protocol.reports import write_report


def verify(root=ROOT):
    # Keep the simpler identity guard available in the dependency-free CI job.
    from scripts.spdx_inventory import pinned_validator, document_profile, HASHES, COMMIT
    spec = importlib.util.spec_from_file_location('runtime_sbom_identity', ROOT / 'scripts/verify-runtime-sbom.py')
    identity = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(identity)
    binding = identity.verify(root)
    validator = pinned_validator(root)
    manifest = read_evidence(root / 'eval/dependencies/runtime-sbom.json')
    images = []
    for row in manifest['images']:
        document = read_evidence(root / row['artifact'], limit=4_000_000)
        images.append({'role': row['role'], 'artifact': row['artifact'],
                      'sha256': row['sha256'], **document_profile(document, validator)})
    return {
        'captured_at': datetime.now(timezone.utc).isoformat(), 'pass': True,
        'kind': 'bound_spdx_schema_and_selected_consistency_verification',
        'schema_upstream_commit': COMMIT, 'schema_sha256': HASHES['schema.json'],
        'verification_network_requests': 0, 'images': images,
        'package_occurrences': binding['package_occurrences'],
        'license_cleared': False, 'release_signed': False,
        'scanner_signed_identity_verified': False, 'source_files_authenticated': False,
        'vulnerabilities_assessed': False, 'tag_release_approved': False,
        'coverage': 'Observed Linux amd64 images; official JSON schema and selected local consistency checks. '
                    'Not complete SPDX semantic conformance, client/build inventory, or license clearance.',
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    try:
        report = verify()
        if args.output:
            write_report(args.output, report)
        print(json.dumps(report))
    except (ValueError, KeyError, TypeError, OSError, ImportError) as error:
        print('SPDX verification refused: ' + str(error), file=sys.stderr)
        raise SystemExit(1)
