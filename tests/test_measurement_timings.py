"""Timing summaries must be derived from explicit, bounded observation rows."""
import copy
import json
from pathlib import Path
import pytest
from protocol.measurements import validate_timing
ROOT=Path(__file__).resolve().parents[1]
def timing():return json.loads((ROOT/'runs/2026-10-10-observed-device-timings.json').read_text())['engines'][0]['timing']
def test_actual_record_is_reproducible():
    r=timing();assert validate_timing(r,127)==r
    assert len(r['per_category'])==7
@pytest.mark.parametrize('change',[lambda r:r.update(p95_ms=999999),lambda r:r['samples'].pop(),lambda r:r['samples'][0].update(duration_ms=float('nan')),lambda r:r['samples'][0].update(duration_ms=True),lambda r:r['samples'][0].update(case_id=r['samples'][1]['case_id']),lambda r:r.update(per_category={}),lambda r:r.update(input_lengths_codepoints={'min':0,'max':1}),lambda r:r.update(cold_load_ms=-1)])
def test_corrupt_summary_or_observation_fails(change):
    r=timing();change(r)
    with pytest.raises(ValueError):validate_timing(r,127)
