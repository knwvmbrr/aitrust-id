"""Misattributed, incomplete or embellished performance observations must fail admission."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('efficiency_check',ROOT/'scripts/verify-ps-efficiency.py')
check=importlib.util.module_from_spec(spec);spec.loader.exec_module(check)
DATA=json.loads((ROOT/check.REPORT).read_text())

def test_current_observations_recompute_and_bind():
    assert check.validate(deepcopy(DATA))==DATA

@pytest.mark.parametrize('mutation', ['source','baseline','quantile','median','boolean_sample','duplicate','missing',
                                      'memory','rss','accuracy','startup','order'])
def test_unsupported_performance_evidence_refused(mutation):
    d=deepcopy(DATA); r=d['profiles'][0]
    if mutation=='source':d['sources']['services/evaluator/app.py']='0'*64
    elif mutation=='baseline':d['sources']['eval/methods/context-v6-eager.py']='0'*64
    elif mutation=='quantile':r['after']['p95_ms']+=1
    elif mutation=='median':r['paired_median_speedup']+=1
    elif mutation=='boolean_sample':r['after']['samples_ms'][0]=True
    elif mutation=='duplicate':d['profiles'][1]=deepcopy(r)
    elif mutation=='missing':d['profiles'].pop()
    elif mutation=='memory':r['after_peak_python_traced_bytes']=True
    elif mutation=='rss':r['peak_measurement_is_not_process_rss']=False
    elif mutation=='accuracy':d['independent_accuracy_evidence']=True
    elif mutation=='startup':d['scope']='Cold whole-pipeline performance'
    elif mutation=='order':d['alternating_execution_order']=False
    with pytest.raises(ValueError):check.validate(d)
