#!/usr/bin/env python3
"""Exercise the actual standalone framing workflow with invented examples only."""
import argparse
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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    checks = []
    command = [sys.executable, '-I', '-S', '-B', str(ROOT/'scripts/check-mt-evidence.py'), '--language', 'en']
    def case(name, argv, text, code, required=()):
        child = subprocess.run(argv, input=text, capture_output=True, timeout=15)
        assert child.returncode == code, name
        assert all(value.encode() in child.stdout for value in required), name
        assert b'SYNTHETIC_SECRET_374' not in child.stdout + child.stderr, name
        checks.append({'id': name, 'expected_exit': code, 'observed_exit': child.returncode, 'passed': True})
        return child
    case('complete_two_checks', command+['--check', 'urgency', '--check', 'authority'],
         b'Buy now. Experts agree SYNTHETIC_SECRET_374.', 0, ('Urgency:', 'Authority:'))
    case('explicit_no_pattern', command+['--check', 'urgency'], b'The sky is blue.', 0, ('No supported urgency pattern',))
    case('choice_unavailable_does_not_disable_urgency', command+['--check', 'choice', '--check', 'urgency'],
         b'Buy now.', 3, ('Choice: unavailable', 'Urgency: A supported'))
    case('all_unavailable', command+['--check', 'choice'], b'Buy now.', 2, ('Choice: unavailable',))
    case('invalid_utf8', command+['--check', 'urgency'], b'\xffSYNTHETIC_SECRET_374', 2)
    case('oversized_input', command+['--check', 'urgency'], b'x'*32001, 2)
    with tempfile.TemporaryDirectory(prefix='aitrust-mt-controls-') as folder:
        os.chmod(folder, 0o700)
        packet = Path(folder)/'packet'
        case('prepare_private_invented_context', [sys.executable, '-I', '-S', '-B', str(ROOT/'scripts/prepare-choice-demo.py'), '--output', str(packet)], b'', 0)
        case('complete_all_three', command+['--check', 'urgency', '--check', 'authority', '--check', 'choice', '--choice-packet', str(packet)],
             b'Either agree or oppose.', 0, ('Choice: Your selected wording',))
        case('choice_subject_mismatch_is_partial', command+['--check', 'urgency', '--check', 'choice', '--choice-packet', str(packet)],
             b'Buy now.', 3, ('Urgency: A supported', 'Choice: unavailable'))
        details = Path(folder)/'details'
        case('explicit_private_export', command+['--check', 'urgency', '--details', str(details)], b'Buy now. SYNTHETIC_SECRET_374', 0)
        artifact = details/'framing-evidence.json'
        original = artifact.read_bytes()
        assert b'SYNTHETIC_SECRET_374' not in original
        assert artifact.stat().st_mode & 0o777 == 0o600
        assert details.stat().st_mode & 0o777 == 0o700
        case('no_overwrite', command+['--check', 'urgency', '--details', str(details)], b'Read later.', 2)
        assert artifact.read_bytes() == original
    names = ['tools/mt_workflow.py', 'scripts/mt-evidence-worker.py', 'scripts/check-mt-evidence.py',
             'scripts/verify-mt-evidence.py', 'scripts/worker_process.py', 'tools/choice_framing.py',
             'tools/language_observations.py', 'protocol/normalization.py', 'protocol/unicode15-data.json',
             'protocol/corpus.py', 'tools/blind_review_io.py', 'tests/test_mt_workflow.py']
    report = {'format': 'ai-trust-id-mt-workflow-controls/v1', 'recorded_at': datetime.now(timezone.utc).isoformat(),
              'executed_by': 'Codex PM', 'platform': platform.platform(), 'python': platform.python_version(),
              'pass': True, 'controls': checks, 'sources': {name: hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in names},
              'synthetic_only': True, 'network_namespace_isolation_exercised': False,
              'tag_asserted': False, 'independent_accuracy_evidence': False,
              'limits': 'Actual local command execution, not independent MT accuracy or human route acceptance. No OS network sandbox claim.'}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x') as out:
        json.dump(report, out, indent=2);out.write('\n')
    print(json.dumps({'pass': True, 'actual_cli_controls': len(checks), 'tag_asserted': False}))


if __name__ == '__main__':
    main()
