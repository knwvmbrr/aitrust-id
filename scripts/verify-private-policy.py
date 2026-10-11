"""Exercise actual invented private-policy commands; no enterprise release or accuracy claim."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from protocol.reports import write_report

SOURCES = ['tools/private_policy.py', 'tools/blind_review_io.py',
           'scripts/check-private-policy.py', 'scripts/prepare-private-policy-demo.py',
           'scripts/verify-private-policy.py', 'tests/test_private_policy.py',
           'tests/test_private_policy_cli.py', 'docs/private-policy.md',
           'protocol/normalization.py', 'protocol/unicode15-data.json',
           'protocol/evidence.py', 'spec/vocabulary.json']


def verify(python):
    before = {n: hashlib.sha256((ROOT / n).read_bytes()).hexdigest() for n in SOURCES}
    controls = []
    with tempfile.TemporaryDirectory(prefix='aitrust-policy-controls-') as directory:
        base = Path(directory).resolve(); base.chmod(0o700); packet = base / 'practice'
        result = subprocess.run([str(python), str(ROOT / 'scripts/prepare-private-policy-demo.py'),
                                 '--output', str(packet)], capture_output=True, timeout=15, cwd=ROOT)
        assert result.returncode == 0 and json.loads(result.stdout)['synthetic_only']
        assert str(base).encode() not in result.stdout + result.stderr
        controls.append({'case': 'actual_invented_packet_prepared', 'pass': True, 'exit_status': 0})
        args = ['--packet', str(packet), '--reviewed-policy']
        def run(name, arguments, expected):
            result = subprocess.run([str(python), str(ROOT / 'scripts/check-private-policy.py'), *arguments],
                                    capture_output=True, timeout=15, cwd=ROOT)
            assert result.returncode == expected, name
            assert str(base).encode() not in result.stdout + result.stderr, name
            assert b'confidential draft' not in result.stdout + result.stderr, name
            controls.append({'case': name, 'pass': True, 'exit_status': expected})
            assert not result.stdout if expected else not result.stderr, name
            return result
        run('review_choice_required', args[:2], 2)
        summary = json.loads(run('short_summary_no_text_hash_or_namespace', args, 0).stdout)
        assert summary['literal_occurrences'] == 1 and not summary['public_tag_asserted']
        assert not any(k in summary for k in ['subject_sha256', 'policy_sha256', 'namespace', 'observations'])
        details = base / 'details'; run('optional_private_details', args + ['--details', str(details)], 0)
        artifact = details / 'private-policy-observations.json'; original = artifact.read_bytes()
        assert details.stat().st_mode & 0o077 == 0 and artifact.stat().st_mode & 0o077 == 0
        assert json.loads(original)['observations'][0]['qualified_code'] == 'example-team:DRAFT'
        run('existing_details_refused', args + ['--details', str(details)], 2)
        assert artifact.read_bytes() == original
        for name in ['subject.txt', 'policy.json', 'selection.json']:
            item = packet / name; raw = item.read_bytes()
            item.chmod(0o644); run(name + '_public_permissions_refused', args, 2); item.chmod(0o600)
            hard = packet / 'hard'; hard.hardlink_to(item); run(name + '_hardlink_refused', args, 2); hard.unlink()
            held = packet / 'held'; item.rename(held); item.symlink_to(held)
            run(name + '_symlink_refused', args, 2); item.unlink(); held.rename(item)
            assert item.read_bytes() == raw
        policy = packet / 'policy.json'; selection = packet / 'selection.json'; subject = packet / 'subject.txt'
        originals = {p: p.read_bytes() for p in [policy, selection, subject]}
        subject.write_text('Changed confidential draft.'); run('changed_subject_refused', args, 2); subject.write_bytes(originals[subject])
        policy.write_bytes(originals[policy] + b' '); run('changed_policy_refused', args, 2); policy.write_bytes(originals[policy])
        for field, value in [('public_thresholds', {'PS': 0}), ('receipts_optional', False), ('limits_visible', False), ('personal_checks_separate', False)]:
            row = json.loads(originals[policy]); row[field] = value; raw = json.dumps(row).encode(); policy.write_bytes(raw)
            bound = json.loads(originals[selection]); bound['policy_sha256'] = hashlib.sha256(raw).hexdigest(); selection.write_text(json.dumps(bound))
            run(field + '_weakening_refused_even_with_updated_binding', args, 2)
        policy.write_bytes(originals[policy]); selection.write_bytes(originals[selection])
        row = json.loads(originals[policy]); row['rules'][0]['code'] = 'PS'; raw = json.dumps(row).encode(); policy.write_bytes(raw)
        bound = json.loads(originals[selection]); bound['policy_sha256'] = hashlib.sha256(raw).hexdigest(); selection.write_text(json.dumps(bound))
        run('public_code_reuse_refused_with_updated_binding', args, 2)
        policy.write_bytes(originals[policy]); selection.write_bytes(originals[selection])
        subject.write_bytes(b'private-canary\xff'); run('malformed_utf8_refused', args, 2); subject.write_bytes(originals[subject])
        row = json.loads(originals[policy]); row['rules'][0]['terms'] = ['unrelated']; raw = json.dumps(row).encode(); policy.write_bytes(raw)
        bound = json.loads(originals[selection]); bound['policy_sha256'] = hashlib.sha256(raw).hexdigest(); selection.write_text(json.dumps(bound))
        negative = json.loads(run('no_match_is_not_compliance', args, 0).stdout)
        assert negative['state'] == 'NO_SUPPORTED_TERM' and not negative['compliance_established']
        run('private_argument_not_echoed', ['--private-canary'], 2)
    assert before == {n: hashlib.sha256((ROOT / n).read_bytes()).hexdigest() for n in SOURCES}
    return {'captured_at': datetime.now(timezone.utc).isoformat(), 'pass': True,
            'implemented_by': 'Codex', 'actual_synthetic_cli_controls': controls,
            'sources': before, 'source_unchanged_during_execution': True,
            'private_test_directory_removed': True, 'public_tag_asserted': False,
            'standard_namespace_adopted': False, 'independent_accuracy_evidence': False,
            'organization_service_running': False, 'release_approved': False}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--python', type=Path, required=True); p.add_argument('--output', type=Path, required=True)
    a = p.parse_args(); report = verify(a.python.absolute()); write_report(a.output, report)
    print(json.dumps({'pass': True, 'actual_synthetic_controls': len(report['actual_synthetic_cli_controls']),
                      'public_tag_asserted': False, 'organization_service_running': False}))
