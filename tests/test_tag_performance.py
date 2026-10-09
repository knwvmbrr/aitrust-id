"""Guard published measurement attribution and statistical denominator planning."""
import importlib.util
from pathlib import Path
import pytest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('tag_performance',ROOT/'scripts/build-tag-performance.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


def test_sizing_uses_lower_bound_and_correct_denominator():
    assert module.minimum_denominator(.93)==52
    assert module.minimum_denominator(.93,1)==77
    assert module.minimum_denominator(.75)==12
    assert module.harness.wilson(51,51)[0]<.93
    assert module.harness.wilson(52,52)[0]>=.93
    assert module.harness.wilson(75,76)[0]<.93
    assert module.harness.wilson(76,77)[0]>=.93


@pytest.mark.parametrize('errors',[True,-1,1.5])
def test_invalid_error_counts_fail(errors):
    with pytest.raises(ValueError):module.minimum_denominator(.93,errors)


def test_changed_method_cannot_publish_old_results(tmp_path,monkeypatch):
    import json
    report=json.loads((ROOT/'runs/2026-10-09-performance-regressions.json').read_text())
    report['method_sha256']='0'*64
    path=tmp_path/'regressions.json';path.write_text(json.dumps(report))
    with pytest.raises(ValueError,match='Stale'):
        module.build(path,ROOT/'runs/2026-10-09-performance-device-local.json')
