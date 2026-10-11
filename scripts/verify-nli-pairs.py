"""Execute synthetic local-model privacy/refusal controls; never claim accuracy."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from protocol.reports import write_report


def verify(executable, cache):
    controls = []
    with tempfile.TemporaryDirectory(prefix='aitrust-nli-controls-') as directory:
        folder = Path(directory).resolve()
        folder.chmod(0o700)
        # Synthetic strings only. Real examples are never read by this verifier.
        text = 'The room is empty. There are people in the room. synthetic-private-canary-27'
        request = {'schema_version': 1, 'language': 'en', 'text': text,
                   'pairs': [{'id': 'synthetic', 'first': [0, 18], 'second': [19, 48]}]}
        input_file = folder / 'input.json'
        input_file.write_text(json.dumps(request))
        input_file.chmod(0o600)
        command = [str(executable), str(ROOT / 'scripts/check-nli-pairs.py')]
        def execute(name, args, expected, data=None):
            result = subprocess.run(command + args, input=data, capture_output=True,
                                    timeout=55, cwd=ROOT)
            assert result.returncode == expected, name
            assert b'synthetic-private-canary-27' not in result.stdout + result.stderr, name
            assert str(folder).encode() not in result.stdout + result.stderr, name
            if expected:
                assert not result.stdout and b'Sentence-pair' in result.stderr, name
            controls.append({'case': name, 'exit_status': expected, 'pass': True})
            return result
        args = [str(input_file), '--model-cache', str(cache)]
        success = execute('actual_summary_omits_text_spans_hash_scores', args, 0)
        summary = json.loads(success.stdout)
        assert summary['evaluation_obtained'] and summary['pairs_evaluated'] == 1
        assert summary['tag_asserted'] is False and summary['release_approved'] is False
        assert 'subject_sha256' not in summary and 'pairs' not in summary
        details = folder / 'details'
        execute('private_details_opt_in', args + ['--details', str(details)], 0)
        record = details / 'observations.json'
        before = record.read_bytes()
        assert details.stat().st_mode & 0o077 == 0 and record.stat().st_mode & 0o077 == 0
        assert text.encode() not in before
        execute('existing_details_never_overwritten', args + ['--details', str(details)], 2)
        assert record.read_bytes() == before
        input_file.chmod(0o644)
        execute('nonprivate_input_refused', args, 2)
        input_file.chmod(0o600)
        link = folder / 'link.json'
        link.symlink_to(input_file)
        execute('input_symlink_refused', [str(link), '--model-cache', str(cache)], 2)
        for name, data in [('duplicate_json', '{"schema_version":1,"schema_version":1}'),
                           ('unsupported_language', json.dumps({**request, 'language': 'fr'})),
                           ('overlapping_spans', json.dumps({**request, 'pairs': [{'id': 'x', 'first': [0, 18], 'second': [1, 17]}]})),
                           ('oversized_input', 'x' * 262145)]:
            input_file.write_text(data)
            execute(name, args, 2)
        input_file.write_text(json.dumps(request))
        bad_cache = folder / 'tampered-cache'
        bad_cache.mkdir(mode=0o700)
        (bad_cache / 'model.onnx').write_bytes(b'changed pinned artifact')
        execute('tampered_model_refused', [str(input_file), '--model-cache', str(bad_cache)], 2)
        execute('missing_model_refused', [str(input_file), '--model-cache', str(folder)], 2)
        execute('arguments_do_not_echo_private_values', ['--unknown-private-value'], 2)
        # Internal worker invocation cannot silently bypass the public private-file
        # workflow. Normal operation supplies its marker in a cleared environment.
        execute('direct_internal_worker_refused', ['--worker', '--model-cache', str(cache)], 2,
                json.dumps(request).encode())
    return {'captured_at': datetime.now(timezone.utc).isoformat(), 'pass': True,
            'actual_model_inference': True, 'synthetic_only': True, 'controls': controls,
            'independent_accuracy_evidence': False, 'tag_asserted': False,
            'release_approved': False, 'private_test_directory_removed': True}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--python', required=True, type=Path)
    parser.add_argument('--model-cache', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    report = verify(args.python.absolute(), args.model_cache.absolute())
    write_report(args.output, report)
    print(json.dumps({'pass': True, 'actual_synthetic_controls': len(report['controls']),
                      'independent_accuracy': False}))
