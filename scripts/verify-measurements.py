"""Reproduce every PS published statistical/timing summary; never approve release."""
import argparse
from datetime import datetime,timezone
import importlib.util
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from protocol.reports import write_report
from protocol.measurements import measurements_match, WILSON_ENDPOINT_ABS_TOLERANCE
spec=importlib.util.spec_from_file_location('build_measurement',ROOT/'scripts/build-tag-performance.py')
builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder)
def verify(path=ROOT/'eval/tag-performance-evidence.json'):
    current=json.loads(Path(path).read_text())
    rebuilt=builder.build(*(ROOT/p for p in current['evidence']))
    current.pop('captured_at');rebuilt.pop('captured_at')
    if not measurements_match(current,rebuilt):raise ValueError('Published measurement differs from full source recomputation')
    return {'captured_at':datetime.now(timezone.utc).isoformat(),'pass':True,'fixture_rows':rebuilt['case_count'],'counts':rebuilt['counts'],'source_categories':len(rebuilt['category_metrics']),'distinct_categories':len({r['category'] for r in rebuilt['category_metrics']}),'timing_observations':sum(len(e['timing']['samples']) for e in rebuilt['mobile']['engines']),'provenance_sha256':rebuilt['provenance']['provenance_sha256'],'interval':'wilson_95','wilson_endpoint_absolute_tolerance':WILSON_ENDPOINT_ABS_TOLERANCE,'non_interval_values_compared_exactly':True,'calibration_ece':None,'independent_accuracy':False,'release_validated':False,'physical_device_tested':False}
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,default=ROOT/'eval/tag-performance-evidence.json');p.add_argument('--output',type=Path,default=ROOT/'output/verification/measurement-ledger.json');a=p.parse_args();r=verify(a.evidence);write_report(a.output,r);print(json.dumps(r))
