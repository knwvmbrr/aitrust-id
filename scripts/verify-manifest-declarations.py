#!/usr/bin/env python3
"""Run the opt-in declaration profile on frozen authored statements, not AI truth."""
from datetime import datetime, timezone
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools import manifest_inspection as parser
from tools import manifest_declarations as declarations
from protocol.reports import write_report


def main():
    args = argparse.ArgumentParser(description=__doc__)
    args.add_argument('--output'); args = args.parse_args()
    paths = ['tools/manifest_inspection.py', 'tools/manifest_presentation.py', 'tools/manifest_declarations.py',
             'scripts/inspect-manifest.py', 'scripts/verify-manifest-declarations.py',
             'tests/test_manifest_declarations.py', 'tests/test_manifest_workflow.py',
             'eval/c2pa-inspection.lock', 'eval/dependencies/c2pa-inspection.json',
             'protocol/corpus.py', 'protocol/normalization.py', 'protocol/unicode15-data.json', 'protocol/reports.py']
    for folder in ['c2pa-inspection-2026', 'c2pa-declarations-2026']:
        paths += [p.relative_to(ROOT).as_posix() for p in (ROOT/'tests/fixtures'/folder).iterdir() if p.is_file()]
    def inventory(): return {p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in sorted(paths)}
    before = inventory(); native, pins = parser.checked_sdk(); cases = []; calls = 0
    fixtures = ROOT/'tests/fixtures/c2pa-declarations-2026'
    manifest = parser.decode((fixtures/'manifest.json').read_bytes())
    assert manifest['fixture_only'] and not manifest['private_keys_written'] and not manifest['independent_accuracy_evidence']
    for name, expected in manifest['files'].items():
        raw = (fixtures/name).read_bytes(); assert hashlib.sha256(raw).hexdigest() == expected
        parser.png_container(raw)
    def invoke(image, expected, kinds=(), text=False, exit_code=0, extra=()):
        nonlocal calls
        command = [sys.executable, str(ROOT/'scripts/inspect-manifest.py'), '--image', str(image),
                   '--profile', 'action-declarations-v1', *extra]
        if text: command += ['--format', 'text']
        process = subprocess.run(command, cwd=ROOT, capture_output=True, timeout=20)
        calls += 1
        assert process.returncode == exit_code and not process.stderr
        output = process.stdout.decode('utf-8')
        assert not any(marker in output for marker in ['PRIVATE_CANARY', 'PRIVATE_METADATA_CANARY', str(ROOT), '\x1b', 'https://', 'http://'])
        if text:
            assert 'AI origin: Unknown.' in output and 'No tag issued.' in output
            for kind in kinds:
                assert ('A creation action claims generative AI use.' if kind == 'generative_ai_creation_declared'
                        else 'An editing action claims generative AI use.') in output
            if expected != 'OBSERVED': assert 'claims generative AI use.' not in output
            return output
        value = json.loads(output)
        assert value['profile'] == declarations.PROFILE and value['declaration_state'] == expected
        assert value['tags'] == [] and value['ai_origin'] == 'unknown'
        assert value['content_truth_established'] is False and value['author_identity_established'] is False
        assert value['production_assertion'] is False
        if expected != 'UNAVAILABLE':
            assert value['profile_sha256'] == before['tools/manifest_declarations.py']
            assert value['method_sha256'] == before['tools/manifest_inspection.py']
            assert value['complete_history_verified'] is False
            assert tuple(row['kind'] for row in value['declarations']) == tuple(kinds)
        return value
    expected = [
        ('declared-creation.png', 'OBSERVED', ('generative_ai_creation_declared',)),
        ('declared-edit.png', 'OBSERVED', ('generative_ai_edit_declared',)),
        ('compatible-declarations.png', 'OBSERVED', ('generative_ai_creation_declared', 'generative_ai_edit_declared')),
        ('non-generative.png', 'UNKNOWN', ()), ('custom-declaration.png', 'UNKNOWN', ()),
        ('template-only.png', 'UNKNOWN', ()), ('declared-creation-altered.png', 'UNKNOWN', ()),
    ]
    for filename, state, kinds in expected:
        value = invoke(fixtures/filename, state, kinds)
        assert value['signer_trust'] == 'untrusted' and value['revocation'] == 'unknown_skipped'
        if filename.endswith('-altered.png'):
            assert value['asset_binding'] == 'mismatched' and value['claim_signature'] == 'matched'
        else: assert value['asset_binding'] == value['claim_signature'] == 'matched'
        invoke(fixtures/filename, state, kinds, text=True)
        cases.append({'case': filename, 'declaration_state': state, 'declared_kinds': list(kinds),
                      'actual_json_and_text': True, 'ai_origin': 'unknown', 'untrusted_signer_and_unknown_revocation_visible': True})
    unsigned = ROOT/'tests/fixtures/c2pa-inspection-2026/unsigned.png'
    invoke(unsigned, 'UNKNOWN'); invoke(unsigned, 'UNKNOWN', text=True)
    cases.append({'case': 'unsigned', 'declaration_state': 'UNKNOWN', 'no_human_or_ai_inference': True})
    with tempfile.TemporaryDirectory(prefix='aitrust-declaration-control-') as directory:
        private = Path(directory).resolve(); private.chmod(0o700)
        invalid = private/'invalid.png'; invalid.write_bytes(unsigned.read_bytes()[:-1])
        oversized = private/'oversized.png'; oversized.write_bytes(b'\x89PNG\r\n\x1a\n' + b'x' * parser.MAX_ASSET_BYTES)
        for name, image in [('malformed', invalid), ('oversized', oversized), ('missing', private/'missing.png')]:
            invoke(image, 'UNAVAILABLE', exit_code=2); invoke(image, 'UNAVAILABLE', exit_code=2, text=True)
            cases.append({'case': name, 'declaration_state': 'UNAVAILABLE', 'actual_json_and_text': True})
        output = private/'selected.json'
        invoke(fixtures/'declared-creation.png', 'OBSERVED', ('generative_ai_creation_declared',),
               text=True, extra=('--private-report', str(output)))
        assert output.stat().st_mode & 0o777 == 0o600 and 'DECLARATION_PRIVATE_METADATA_CANARY' in output.read_text()
        saved = output.read_bytes()
        invoke(fixtures/'declared-creation.png', 'UNAVAILABLE', exit_code=2, extra=('--private-report', str(output)))
        assert output.read_bytes() == saved
        cases.append({'case': 'explicit_private_export_and_no_overwrite', 'owner_private': True})
    stable = inventory() == before; assert stable
    isolated = None
    if sys.platform == 'linux': isolated = os.readlink('/proc/self/ns/net') != os.readlink('/proc/1/ns/net')
    proof = {'captured_at': datetime.now(timezone.utc).isoformat(), 'pass': True,
        'profile': declarations.PROFILE, 'sources': before, 'source_unchanged_during_execution': stable,
        'cases': cases, 'case_count': len(cases), 'actual_cli_calls': calls,
        'package_version': pins['package_version'], 'sdk_version': pins['sdk_version'],
        'native_sha256': hashlib.sha256(Path(native).read_bytes()).hexdigest(),
        'effective_user_is_root': os.geteuid() == 0, 'network_namespace_differs_from_init': isolated,
        'settings': parser.SETTINGS, 'authored_declarations_are_ai_origin_ground_truth': False,
        'new_tag_releases': 0, 'independent_accuracy_evidence': False}
    if args.output: write_report(args.output, proof, root=ROOT)
    print(json.dumps(proof, indent=2))


if __name__ == '__main__': main()
