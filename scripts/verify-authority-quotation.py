#!/usr/bin/env python3
"""Bounded synthetic checks against actual old and opt-in authority executables."""
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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output')
    args = parser.parse_args()
    paths = ['tools/authority_quotation.py', 'scripts/authority-quotation.py',
             'scripts/verify-authority-quotation.py', 'tests/test_authority_quotation.py',
             'tools/language_observations.py', 'scripts/language-observations.py',
             'protocol/normalization.py', 'protocol/unicode15-data.json', 'protocol/corpus.py',
             'tools/blind_review_io.py', 'protocol/reports.py']
    inventory = lambda: {p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths}
    before = inventory()
    cases = []
    current = 'initialization'
    def run(name, raw, expected, status=0, extra=(), legacy=False):
        nonlocal current
        current = name
        command = ([sys.executable, str(ROOT/'scripts/language-observations.py'), 'authority'] if legacy
                   else [sys.executable, str(ROOT/'scripts/authority-quotation.py')])
        result = subprocess.run([*command, '--language', 'en', *map(str, extra)],
                                input=raw, capture_output=True, timeout=5)
        assert result.returncode == status and not result.stderr
        assert b'PRIVATE_AUTHORITY_CANARY' not in result.stdout
        value = json.loads(result.stdout)
        assert all(value.get(key) == wanted for key,wanted in expected.items())
        assert value['tags'] == []
        cases.append({'case':name, 'pass':True})
        return value
    try:
        quoted = b'The training example says "Experts agree".'
        borrowed = b'Experts agree; the quoted example is "https://example.invalid".'
        old_quote = run('legacy_quoted_phrase_unchanged', quoted, {'state':'OBSERVATIONS'}, legacy=True)
        old_marker = run('legacy_quoted_marker_unchanged', borrowed, {'state':'NO_SUPPORTED_PATTERN'}, legacy=True)
        regression = {'old_quote_findings':len(old_quote['findings']),
                      'old_borrowed_marker_findings':len(old_marker['findings']),
                      'target_contract_passes_legacy':False}
        assert regression['old_quote_findings'] == 1 and regression['old_borrowed_marker_findings'] == 0
        run('quoted_mention_separated', quoted, {'quoted_phrase_count':1, 'outside_supported_quotes_without_marker':0})
        run('quoted_url_not_borrowed', borrowed, {'quoted_phrase_count':0, 'outside_supported_quotes_without_marker':1})
        run('unquoted_marker_preserved', b'Experts agree; see https://example.invalid.',
            {'outside_supported_quotes_with_marker':1, 'outside_supported_quotes_without_marker':0})
        run('mixed_contexts_independent', b'"Experts agree [1]"; studies show benefits.',
            {'quoted_phrase_count':1, 'outside_supported_quotes_without_marker':1})
        run('different_quotes_no_marker_borrowing', b'"Experts agree" and "https://example.invalid".',
            {'quoted_phrase_count':1, 'outside_supported_quotes_without_marker':0})
        run('phrase_does_not_cross_quote', b'Experts "agree".', {'quoted_phrase_count':0, 'outside_supported_quotes_without_marker':0})
        run('brief_has_no_input', b'PRIVATE_AUTHORITY_CANARY Experts agree.', {'outside_supported_quotes_without_marker':1})
        for name, raw in [('unbalanced_quote', b'"Experts agree'), ('escaped_quote', b'"Experts \\"agree"'),
                          ('curly_quotes', '“Experts agree”'.encode()), ('backtick', b'`Experts agree`'),
                          ('invalid_utf8', b'\xff PRIVATE_AUTHORITY_CANARY'), ('nul', b'Experts agree\0'),
                          ('input_bytes', b'x'*32001), ('quote_limit', b'"" '*65),
                          ('phrase_limit', b'Experts agree; '*129), ('marker_limit', b'[1] '*257),
                          ('unit_limit', b'x. '*513)]:
            run(name, raw, {'state':'UNAVAILABLE'}, status=2)
        with tempfile.TemporaryDirectory(prefix='aitrust-authority-private-') as directory:
            folder = Path(directory).resolve()/'details'
            subject = 'Cafe\u0301: "Experts agree [1]"; studies show benefits.'
            run('private_normalized_details', subject.encode(), {'private_details_saved':True}, extra=('--details', folder))
            detail_file = folder/'authority-quotation.json'
            original = detail_file.read_bytes()
            detail = json.loads(original)
            assert folder.stat().st_mode & 0o777 == 0o700
            assert detail_file.stat().st_mode & 0o777 == 0o600
            assert detail['subject_sha256'] == hashlib.sha256(subject.replace('e\u0301','é').encode()).hexdigest()
            assert detail['quoted_phrases'][0]['phrase_span'] == [7,20]
            assert detail['quoted_phrases'][0]['source_marker_spans'] == [[21,24]]
            assert detail['source_sha256'] == {p:before[p] for p in detail['source_sha256']}
            assert detail['subject_text_included'] is False and subject.encode() not in original
            run('private_output_never_overwritten', b'Experts agree.', {'state':'UNAVAILABLE'}, status=2, extra=('--details',folder))
            assert detail_file.read_bytes() == original
        assert before == inventory()
        record = {'captured_at':datetime.now(timezone.utc).isoformat(), 'pass':True,
                  'method':'ascii-quoted-authority-observations/1.0.0', 'case_count':len(cases), 'cases':cases,
                  'legacy_target_regression':regression, 'sources':before, 'source_unchanged_during_execution':True,
                  'only_authored_synthetic_inputs':True, 'tag_assertions':0, 'independent_accuracy_evidence':False,
                  'isolated_linux':False, 'network_namespace_checked':False,
                  'limit':'Local executable regression controls; no MT release, semantic attribution, quote endorsement or model accuracy.'}
    except (ValueError, OSError, AssertionError, subprocess.SubprocessError) as error:
        record = {'captured_at':datetime.now(timezone.utc).isoformat(), 'pass':False,
                  'current_case':current, 'completed_cases':cases, 'failure_kind':type(error).__name__,
                  'sources':before, 'independent_accuracy_evidence':False}
    if args.output: write_report(args.output, record, root=ROOT)
    print(json.dumps({'pass':record['pass'], 'case_count':len(cases), 'current_case':current}))
    return 0 if record['pass'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
