import copy,importlib.util,json,sys
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
spec=importlib.util.spec_from_file_location('redaction_builder',ROOT/'scripts/build-redaction-performance.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
r=json.loads((ROOT/m.REPORT).read_text())
def test_current_source_bound_errors_can_be_published_without_clearance():
 s=m.public_summary(r);assert s['english']['fully_masked']==34 and s['english']['partial']==0
 assert s['english']['cases_with_extra_masking']==2 and s['challenges']['fully_masked']==2
 assert len(s['categories'])==7 and not s['privacy_clearance']
@pytest.mark.parametrize('mutate',[
 lambda d:d.update(candidate_recognizer_override=True),lambda d:d.update(privacy_clearance=True),
 lambda d:d.update(http_route_tested=True),lambda d:d.update(independent_accuracy_evidence=True),
 lambda d:d['client_sources'].update({'services/anonymizer/app.py':'a'*64}),
 lambda d:d['client_sources'].pop('scripts/redaction-development-worker.py'),
 lambda d:d['sources'].update(app='a'*64),lambda d:d['redactor_identity'].update(sha256='a'*64),
 lambda d:d['measurement']['slices']['en'].update(fn=1),
 lambda d:d['measurement']['redaction_coverage'][0].update(fully_masked_expected_spans=7),
 lambda d:d['rows'][0].update(text='private'),lambda d:d['rows'].pop(),
 lambda d:d['rows'].append(copy.deepcopy(d['rows'][0])),
 lambda d:d.update(captured_at='2099-01-01T00:00:00+00:00'),lambda d:d.update(captured_at='not a date'),lambda d:d.update(captured_at='2026-10-11'),
])
def test_altered_evidence_cannot_reach_chart(mutate):
 d=copy.deepcopy(r);mutate(d)
 with pytest.raises((ValueError,TypeError)):m.public_summary(d)
