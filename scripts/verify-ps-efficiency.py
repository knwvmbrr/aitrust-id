"""Admit paired PS efficiency data only when raw samples and current sources agree."""
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import statistics
ROOT = Path(__file__).resolve().parents[1]
REPORT = 'runs/2026-10-13-ps-lazy-context-paired.json'

def validate(data, root=ROOT):
    spec = importlib.util.spec_from_file_location('paired_measure', root/'scripts/measure-ps-efficiency.py')
    measure = importlib.util.module_from_spec(spec); spec.loader.exec_module(measure)
    if data.get('kind') != 'paired_synthetic_ps_efficiency' or data.get('pass') is not True:
        raise ValueError('Wrong paired measurement kind')
    expected = [measure.BASELINE, 'services/evaluator/app.py', 'scripts/measure-ps-efficiency.py']
    hashes = {p: hashlib.sha256((root/p).read_bytes()).hexdigest() for p in expected}
    if data.get('sources') != hashes or hashes[measure.BASELINE] != measure.BEFORE_SHA:
        raise ValueError('Stale paired source')
    if (data.get('source_unchanged_during_execution') is not True or
        data.get('alternating_execution_order') is not True or data.get('repeats_per_profile') != 21 or
        data.get('scope') != 'Warm rule calls only; not imports, browser startup, redaction, network or physical-phone latency.' or
        data.get('network_requests') != 0 or isinstance(data.get('network_requests'), bool) or
        any(data.get(k) is not False for k in ['population_performance_claimed', 'independent_accuracy_evidence',
                                            'user_content_used', 'commands_executed', 'release_approved'])):
        raise ValueError('Wrong paired evidence boundary')
    profiles=data.get('profiles'); seen=set()
    if not isinstance(profiles,list) or len(profiles)!=12:raise ValueError('Incomplete paired profiles')
    def positive(v):return type(v) in (int,float) and math.isfinite(v) and v>0
    for row in profiles:
        key=(row.get('profile'),row.get('input_codepoints'))
        if key in seen or key[0] not in measure.FORMS or type(key[1]) is not int or key[1] not in measure.SIZES:
            raise ValueError('Unknown or duplicate profile')
        seen.add(key)
        if row.get('candidate_outputs_equal') is not True or row.get('peak_measurement_is_not_process_rss') is not True:
            raise ValueError('Changed semantics or memory scope')
        for side in ('before','after'):
            summary=row.get(side); samples=summary.get('samples_ms') if isinstance(summary,dict) else None
            if (not isinstance(samples,list) or len(samples)!=21 or not all(positive(v) for v in samples) or
                summary!=measure.quantiles(samples)):
                raise ValueError('Invalid paired samples or quantiles')
            peak=row.get(side+'_peak_python_traced_bytes')
            if type(peak) is not int or peak<=0:raise ValueError('Invalid traced allocation')
        ratios=[a/b for a,b in zip(row['before']['samples_ms'],row['after']['samples_ms'])]
        if not positive(row.get('paired_median_speedup')) or row['paired_median_speedup']!=statistics.median(ratios):
            raise ValueError('Speedup differs from paired observations')
    return data

if __name__=='__main__':
    validate(json.loads((ROOT/REPORT).read_text()))
    print('12 source-bound paired profiles valid; no accuracy or population performance claim.')
