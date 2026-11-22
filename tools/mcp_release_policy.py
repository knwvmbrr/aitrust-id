"""Finite, trusted-source MCP grant assessment; never artifact-chosen permission.

The selected source checkout is the policy authority. This module does not issue
legal clearance, infer exhaustive compiled closure or authenticate an artifact.
Managed consumers must still verify its protected-main signature and runtime.
"""
from pathlib import Path

from tools.artifact_evidence_io import Capture, encoded, need, sha

ROOT = Path(__file__).resolve().parents[1]
ASSESSMENT = 'eval/dependencies/mcp-runtime-release.json'
ASSESSMENT_SHA256 = 'd0488a93ce395eb7b03aed1161977a87a81782f6af7a4bd66ba890c0f4c22c38'
FIXED_IO_SHA256 = '2d8089a460d0b70c7725ce8bfdecda88b798c70d3335cfbb22c8fe5b31ea0b4e'
COMPONENT = 'mcp-stdio-unreviewed'  # Historical registry identifier; not a status.
EXPRESSION = 'LicenseRef-MCP-Finite-Grants'
PREREQUISITES = [
    'Independently obtained matching CPython 3.12 or 3.13, pip and supported macOS-arm64 or Linux-x86_64 OS; none is bundled.',
    'Only the exact target-selected publisher wheels, project sources and carried notices are reviewed; no caller input or optional privacy service is installed.',
    'Managed use additionally requires the exact protected-main artifact attestation, separately selected trust roots and successful fresh installed-tool checks.',
]
SCOPE = ('Finite four-target MCP stdio wheel distribution with individually mapped grants and retained notices; '
         'unmodified publisher bytes and scoped native correspondence, not exhaustive compiled-build, '
         'whole-project legal clearance or independent detector accuracy.')
FACT_INPUTS = (
    'LICENSE', 'NOTICE', 'spec/LICENSE', 'eval/vectors/unicode/LICENSE.txt',
    'integrations/mcp/requirements.lock', 'sbom/mcp-runtime/targets.json',
    'sbom/mcp-runtime/source-inputs.json', 'sbom/mcp-runtime/obligations.json.gz',
    'sbom/mcp-runtime/THIRD-PARTY-NOTICES.txt', 'sbom/mcp-runtime/SCHEMA-ATTRIBUTION.txt',
    'sbom/cffi-libffi/manifest.json', 'sbom/cffi-libffi/LIBFFI-NOTICES.txt',
    'sbom/mcp-rust-stdlib/manifest.json', 'sbom/mcp-rust-stdlib/RUST-STDLIB-NOTICES.txt',
)
NOTICES = [
    'sbom/mcp-runtime/THIRD-PARTY-NOTICES.txt', 'sbom/mcp-runtime/SCHEMA-ATTRIBUTION.txt',
    'sbom/cffi-libffi/LIBFFI-NOTICES.txt', 'sbom/mcp-rust-stdlib/RUST-STDLIB-NOTICES.txt',
]
REVIEW_FILES = {
    'runs/2026-11-22-mcp-retained-grants-distinct-review.json':
        '5a74863249f73a7c092f8bbed08156b8add5ec2231e1b7e526b01a19459c23d1',
    'runs/2026-11-22-mcp-cffi-rust-notice-facts-distinct-review.json':
        '80b39cb342718c8f8c475db93d2f0a07e32f5356c3285140618c26829d8cd68e',
}
COMPONENT_FILES = frozenset({
    *FACT_INPUTS, *REVIEW_FILES, ASSESSMENT,
    'tools/mcp_release_policy.py', 'tools/mcp_managed_release.py',
    'scripts/install-managed-mcp.py', 'tools/mcp_distribution.py',
    'scripts/mcp-distribution.py', 'scripts/ai-tools-server.py',
    'sbom/mcp-runtime/manifest.json', 'tools/artifact_evidence_io.py',
    'docs/mcp-managed-release.md',
})


def facts(capture, root, profile):
    """Exact reviewed licensing facts; code changes are separately source-bound."""
    inputs = {}
    for path in FACT_INPUTS:
        raw = capture.read(Path(root) / path, 4_000_000, private=False)
        inputs[path] = {'sha256': sha(raw), 'bytes': len(raw)}
    return {'inputs': inputs, 'targets': sorted(profile['targets']),
            'wheels_sha256': sha(encoded(profile['wheels'])),
            'dependencies_sha256': sha(encoded(profile['dependencies'])),
            'retained_evidence_sha256': sha(encoded(profile['evidence_files']))}


def review(root=ROOT):
    """Return current finite facts only when exact fixed-source assessment holds."""
    from tools import mcp_distribution as runtime
    with Capture() as capture:
        raw = capture.read(Path(root) / ASSESSMENT, 128_000, private=False)
        need(sha(raw) == ASSESSMENT_SHA256)
        record = runtime.decode(raw)
        need(record['profile'] == 'mcp-stdio-technical-distribution-review/v1'
             and record['route'] == 'mcp-stdio')
        for path, digest in REVIEW_FILES.items():
            need(sha(capture.read(Path(root) / path, 500_000, private=False)) == digest)
        need(sha(capture.read(Path(root) / 'tools/artifact_evidence_io.py', 128_000,
                              private=False)) == FIXED_IO_SHA256)
        _, profile = runtime.load(capture, root)
        observed = facts(capture, root, profile)
        need(record['facts'] == observed)
        capture.check()
    return {'route': 'mcp-stdio', 'assessment_sha256': sha(raw),
            'fact_sha256': sha(encoded(observed)), 'targets': observed['targets'],
            'runtime_source_profile_verified': True,
            'complete_compiled_closure': False, 'legal_clearance': False,
            'complete_project_obligations': False}


def component_status(component, selected, root=ROOT):
    """No JSON status, caller flag or another route can approve this scope."""
    if component['required_processing_payment'] is True:
        return 'paid', 'required_processing_payment'
    if component['source_available'] is False:
        return 'prohibited', 'required_processor_declared_closed'
    try:
        need(component['assessment'] == 'reviewed_bundled_distribution'
             and component['license_expression'] == EXPRESSION
             and component['source_available'] is True
             and component['required_processing_payment'] is False
             and component['notice_paths'] == NOTICES
             and component['review_scope'] == SCOPE)
        need(selected == {'kind': 'optional-sdk',
            'dependencies': [{'component': COMPONENT, 'required': True}],
            'prerequisites': PREREQUISITES,
            'entrypoints': ['integrations/mcp/requirements.lock'], 'release_scope': SCOPE})
        need(type(selected['dependencies'][0]['required']) is bool)
        rows = component['files']
        need(type(rows) is list and len(rows) == len(COMPONENT_FILES)
             and {row['path'] for row in rows} == COMPONENT_FILES)
        with Capture() as capture:
            for row in rows:
                raw = capture.read(Path(root) / row['path'], 8_000_000, private=False)
                need(type(row['bytes']) is int and len(raw) == row['bytes']
                     and sha(raw) == row['sha256'])
            review(root)
            capture.check()
        return 'allowed', 'exact_finite_mcp_grants_notices_and_current_source'
    except (OSError, ValueError, TypeError, KeyError, ImportError, RuntimeError,
            OverflowError, RecursionError, UnicodeError):
        return 'blocked_unknown', 'mcp_reviewed_facts_or_consumer_source_changed'
