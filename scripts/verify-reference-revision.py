#!/usr/bin/env python3
"""Exercise synthetic reference changes and private-file refusals through the CLI."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from protocol import corpus, corpus_support
from protocol.reports import write_report
from tools import reference_revision as revision

SOURCES = ('scripts/prepare-reference-revision-demo.py', 'tools/reference_revision.py', 'scripts/review-reference-revision.py',
    'scripts/verify-reference-revision.py', 'tests/test_reference_revision.py', 'tools/blind_review_io.py',
    'protocol/corpus.py', 'protocol/corpus_support.py', 'protocol/normalization.py', 'protocol/unicode15-data.json')


def hashes():
    return {name: hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in SOURCES}


def envelope(documents):
    rows = [{'id': identity, 'sha256': corpus.sha(text.encode()), 'text': text} for identity, text in sorted(documents.items())]
    content = {'format': corpus.VERSION, 'documents': rows}
    return dict(content, manifest_sha256=corpus.sha(corpus.encoded(content)))


def verify():
    before = hashes(); controls = []
    with tempfile.TemporaryDirectory(prefix='aitrust-reference-revision-') as temporary:
        base = Path(temporary).resolve(); base.chmod(0o700)
        old = envelope({'manual': 'The fee is 25 dollars.\n', 'policy': 'Use a blue bicycle.\n'})
        changed = envelope({'manual': 'The fee is 26 dollars.\n', 'policy': 'Use a blue bicycle.\n'})
        subject = 'The fee is 25 dollars.\nUse a blue bicycle.'
        observed = corpus_support.observe(old, subject, 1)
        policy = {'profile': revision.POLICY, 'manifest_sha256': changed['manifest_sha256'], 'documents': [
            {'document_id': d['id'], 'document_sha256': d['sha256'], 'opens_at': '2026-10-01T00:00:00Z',
             'expires_at': '2026-11-01T00:00:00Z'} for d in changed['documents']]}
        files = {'old.json': corpus.encoded(old), 'new.json': corpus.encoded(changed), 'subject.txt': subject.encode(),
                 'observation.json': corpus.encoded(observed), 'windows.json': corpus.encoded(policy)}
        for name, data in files.items():
            (base/name).write_bytes(data); (base/name).chmod(0o600)
        prepared = subprocess.run([sys.executable, str(ROOT/'scripts/prepare-reference-revision-demo.py'),
            '--output', str(base/'practice')], capture_output=True, timeout=15, cwd=ROOT)
        assert prepared.returncode == 0 and not prepared.stderr and str(base).encode() not in prepared.stdout
        assert json.loads(prepared.stdout)['state'] == 'synthetic_practice_created'
        assert set(p.name for p in (base/'practice').iterdir()) == {'old.json', 'new.json', 'subject.txt', 'observation.json', 'windows.json', 'README.txt'}
        controls.append({'case': 'actual_private_practice_generator', 'pass': True, 'exit_status': 0})
        command = [sys.executable, str(ROOT/'scripts/review-reference-revision.py'),
            '--previous-corpus', str(base/'old.json'), '--current-corpus', str(base/'new.json'),
            '--subject', str(base/'subject.txt'), '--observation', str(base/'observation.json'),
            '--review-windows', str(base/'windows.json'), '--at', '2026-10-12T12:00:00Z']
        def run(name, extra=(), expected=0):
            output = subprocess.run(command + list(extra), capture_output=True, timeout=15, cwd=ROOT)
            assert output.returncode == expected, name
            for secret in [str(base).encode(), b'document_sha256', b'manual', b'blue bicycle', b'PRIVATE_CANARY']:
                assert secret not in output.stdout + output.stderr, name
            if expected:
                assert not output.stdout and json.loads(output.stderr)['state'] == 'UNAVAILABLE', name
            else:
                assert not output.stderr and not json.loads(output.stdout)['tag_asserted'], name
            controls.append({'case': name, 'pass': True, 'exit_status': expected})
            return json.loads(output.stdout) if not expected else None
        result = run('changed_source_selectively_invalidates_context_and_global_ranking')
        assert result['unchanged_pair_contexts'] == result['changed_or_removed_pair_contexts'] == 1
        assert result['global_retrieval_must_rerun']
        run('explicit_new_private_details', ['--details', str(base/'details')])
        detail = base/'details/reference-revision.json'; captured = detail.read_bytes()
        assert not detail.stat().st_mode & 0o077 and not detail.parent.stat().st_mode & 0o077
        run('existing_details_never_overwritten', ['--details', str(base/'details')], 2)
        assert detail.read_bytes() == captured
        (base/'new.json').write_bytes(corpus.encoded(old)); (base/'windows.json').write_bytes(corpus.encoded(
            dict(policy, manifest_sha256=old['manifest_sha256'], documents=[])))
        result = run('identical_corpus_unknown_declared_windows')
        assert not result['global_retrieval_must_rerun'] and result['unchanged_pair_contexts'] == 2
        assert result['declared_review_windows']['unknown'] == 2
        (base/'windows.json').write_bytes(files['windows.json'])
        run('policy_bound_to_wrong_corpus_refused', expected=2)
        (base/'new.json').write_bytes(files['new.json']); policy['documents'][0]['expires_at'] = '2026-10-12T12:00:00Z'
        (base/'windows.json').write_bytes(corpus.encoded(policy))
        result = run('elapsed_boundary_separate_from_pair_context')
        assert result['declared_review_windows']['elapsed'] == 1 and not result['source_freshness_authenticated']
        (base/'observation.json').write_bytes(corpus.encoded(dict(observed, truth_established=True)))
        run('altered_truth_claim_refused', expected=2); (base/'observation.json').write_bytes(files['observation.json'])
        (base/'subject.txt').chmod(0o644); run('public_subject_refused', expected=2); (base/'subject.txt').chmod(0o600)
        (base/'subject.txt').write_bytes(b'PRIVATE_CANARY\xff'); run('invalid_utf8_private_input_refused', expected=2)
    assert hashes() == before
    return {'captured_at': datetime.now(timezone.utc).isoformat(), 'pass': True, 'synthetic_only': True,
        'controls': controls, 'sources': before, 'source_unchanged_during_execution': True,
        'private_test_directory_removed': not base.exists(), 'tag_asserted': False,
        'independent_accuracy_evidence': False, 'physical_device_tested': False,
        'source_freshness_authenticated': False, 'requirements_closed': 0}


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    proof = verify(); write_report(args.output, proof)
    print(json.dumps({'pass': True, 'actual_cli_controls': len(proof['controls']), 'requirements_closed': 0}))
