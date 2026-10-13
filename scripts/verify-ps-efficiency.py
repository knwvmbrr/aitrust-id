"""Admit paired PS efficiency data only when raw samples and current sources agree."""
import hashlib
import importlib.util
import json
import math
import re
from datetime import datetime, timezone
from pathlib import Path
import statistics
ROOT = Path(__file__).resolve().parents[1]
REPORT = 'runs/2026-10-13-ps-lazy-context-paired.json'

def validate(data, root=ROOT):
    fields = {'captured_at','pass','kind','sources','source_unchanged_during_execution',
              'execution_host','profiles','repeats_per_profile','alternating_execution_order',
              'scope','population_performance_claimed','independent_accuracy_evidence',
              'user_content_used','commands_executed','network_requests','release_approved'}
    if type(data) is not dict or set(data)!=fields:
        raise ValueError('Unexpected paired evidence fields')
    raw_date=data['captured_at']
    if type(raw_date) is not str:raise ValueError('Invalid measurement timestamp')
    try:date=datetime.fromisoformat(raw_date)
    except ValueError:raise ValueError('Invalid measurement timestamp') from None
    if date.utcoffset() is None or date.utcoffset().total_seconds()!=0 or date>datetime.now(timezone.utc):
        raise ValueError('Measurement timestamp must be past or current UTC')
    host=data['execution_host']
    if (type(host) is not dict or set(host)!={'system','machine','logical_cpus','python'} or
        host['system'] not in ('Darwin','Linux','Windows') or type(host['system']) is not str or
        type(host['machine']) is not str or host['machine'] not in ('arm64','aarch64','x86_64','AMD64') or
        type(host['logical_cpus']) is not int or not 1<=host['logical_cpus']<=4096 or
        type(host['python']) is not str or not re.fullmatch(r'3\.[0-9]{1,2}\.[0-9]{1,3}',host['python'])):
        raise ValueError('Invalid declared measurement host')
    if type(data['repeats_per_profile']) is not int or type(data['network_requests']) is not int:
        raise ValueError('Invalid measurement count types')
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
        if type(row) is not dict or set(row)!={'profile','input_codepoints','before','after',
                'paired_median_speedup','before_peak_python_traced_bytes','after_peak_python_traced_bytes',
                'peak_measurement_is_not_process_rss','candidate_outputs_equal'}:
            raise ValueError('Unexpected paired profile fields')
        if type(row['profile']) is not str or type(row['input_codepoints']) is not int:
            raise ValueError('Invalid profile condition types')
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
