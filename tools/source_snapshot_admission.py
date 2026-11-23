"""Finite source-copy admission, separate from runtime or tag approval.

The installed trusted checkout supplies the classifier and the selected policy.
Neither a received archive nor an evidence packet can select permissions.
"""
from pathlib import Path

from tools.artifact_evidence_io import Capture, need, sha

ROOT = Path(__file__).resolve().parents[1]
COMPONENT = 'source-snapshot-unreviewed'  # Retained registry ID, not the status.
EXPRESSION = 'LicenseRef-Source-Snapshot-Finite-Copy-Grants'
NOTICES = ['LICENSE', 'NOTICE', 'spec/LICENSE', 'eval/vectors/unicode/LICENSE.txt']
PREREQUISITES = [
    'Independently obtained CPython 3.12 or newer and a supported POSIX OS; no interpreter or OS is bundled.',
    'Only exact committed source copying with the finite reviewed grants and carried notices is admitted; runtime, SDK, model and compiled redistribution rights remain separate.',
    'Managed use requires the caller-selected trusted Git commit, protected-main artifact attestation, separately trusted roots and successful finite source-entry-point probes.',
]
SCOPE = ('Canonical whole-repository source snapshot with finite per-component copy grants, '
         'trusted-Git byte binding and retained notices; no bundled runtime, platform or model '
         'permission, whole-project legal clearance or independent tag accuracy.')
COMPONENT_FILES = frozenset({
    *NOTICES, 'eval/dependencies/source-snapshot-release.json',
    'eval/dependencies/source-snapshot-release-v2.json',
    'eval/dependencies/source-snapshot-additions-v3.json',
    'tools/source_release_policy.py', 'tools/source_release_policy_v2.py',
    'tools/source_release_policy_v3.py',
    'tools/source_snapshot_binding.py', 'tools/source_snapshot_admission.py',
    'scripts/source_snapshot.py', 'scripts/source_snapshot_v2.py',
    'scripts/source_snapshot_v3.py', 'scripts/build-source-snapshot.py',
    'scripts/worker_process.py', 'tools/artifact_evidence_io.py',
    'tools/source_snapshot_managed.py', 'scripts/verify-managed-source.py',
    'docs/source-snapshot-managed-consumer.md',
})


def review(root=ROOT, source_commit=None):
    """Actually execute the closed source classifier; no status-only approval."""
    need(Path(root).resolve() == ROOT)
    from tools import source_release_policy_v3 as copy
    result = copy.verify(root=root, source_commit=source_commit)
    need(result.get('profile') == copy.PROFILE and result.get('pass') is True
         and result.get('source_copy_profile_satisfied') is True
         and result.get('status') == 'SOURCE_COPY_PROFILE_SATISFIED'
         and type(result.get('files')) is int and 0 < result['files'] <= copy.MAX_FILES
         and type(result.get('source_bytes')) is int
         and 0 <= result['source_bytes'] <= copy.MAX_TOTAL
         and type(result.get('source_commit')) is str
         and copy.OID.fullmatch(result['source_commit'])
         and all(result.get(key) is False for key in copy.FALSE_CLAIMS))
    if source_commit is not None:
        need(result['source_commit'] == source_commit)
    return result


def component_status(component, selected, root=ROOT):
    """A reviewed copy-only component cannot approve any sibling route."""
    if component['required_processing_payment'] is True:
        return 'paid', 'required_processing_payment'
    if component['source_available'] is False:
        return 'prohibited', 'required_processor_declared_closed'
    try:
        need(component['assessment'] == 'reviewed_source_distribution'
             and component['license_expression'] == EXPRESSION
             and component['source_available'] is True
             and component['required_processing_payment'] is False
             and component['notice_paths'] == NOTICES and component['review_scope'] == SCOPE)
        need(selected == {'kind': 'whole-repository',
            'dependencies': [{'component': COMPONENT, 'required': True}],
            'prerequisites': PREREQUISITES,
            'entrypoints': ['scripts/build-source-snapshot.py'], 'release_scope': SCOPE})
        need(type(selected['dependencies'][0]['required']) is bool)
        rows = component['files']
        need(type(rows) is list and len(rows) == len(COMPONENT_FILES)
             and {row['path'] for row in rows} == COMPONENT_FILES)
        with Capture() as capture:
            for row in rows:
                raw = capture.read(Path(root) / row['path'], 12_000_000, private=False)
                need(type(row['bytes']) is int and len(raw) == row['bytes']
                     and sha(raw) == row['sha256'])
            review(root)
            capture.check()
        return 'allowed', 'finite_current_source_copy_grants_only'
    except (OSError, ValueError, TypeError, KeyError, ImportError, RuntimeError,
            OverflowError, RecursionError, UnicodeError):
        return 'blocked_unknown', 'source_copy_facts_or_consumer_changed'
