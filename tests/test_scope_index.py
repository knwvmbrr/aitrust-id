"""Every rendered scope percentage must agree with the retained ledger."""
import importlib.util,json
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('scope_plan',ROOT/'scripts/verify-scope-plan.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
RECORDS=[{'id':'F-056','percent_complete':60},{'id':'T-PS','percent_complete':80}]
def row(id,percentage):return f'| TASK-{id} | Job | Package | {percentage}% · [evidence/fix](scope-progress.md) |'
def index():return '\n'.join(row(r['id'],r['percent_complete']) for r in RECORDS)
def test_current_all_202_percentages_agree():
 d=json.loads((ROOT/'docs/scope-progress.json').read_text());assert m.verify_task_percentages((ROOT/'docs/scope-task-index.md').read_text(),d['records'])==202
def test_valid_index_and_reordering_are_accepted():
 assert m.verify_task_percentages('\n'.join(reversed(index().splitlines())),RECORDS)==2
@pytest.mark.parametrize('value',['20','100','61','unassessed','true'])
def test_stale_or_invalid_percentage_refused(value):
 with pytest.raises(ValueError):m.verify_task_percentages(index().replace('60%',value+'%'),RECORDS)
def test_missing_row_refused():
 with pytest.raises(ValueError):m.verify_task_percentages(row('F-056',60),RECORDS)
def test_duplicate_row_refused():
 with pytest.raises(ValueError,match='Duplicate'):m.verify_task_percentages(index()+'\n'+row('F-056',60),RECORDS)
def test_orphan_row_refused():
 with pytest.raises(ValueError):m.verify_task_percentages(index()+'\n'+row('Unknown',60),RECORDS)
def test_missing_evidence_link_refused():
 with pytest.raises(ValueError):m.verify_task_percentages(index().replace('(scope-progress.md)','(elsewhere.md)'),RECORDS)


def test_actual_renderer_preserves_dated_notes_without_duplication(tmp_path):
 import shutil,subprocess,sys
 root=tmp_path/'checkout';(root/'scripts').mkdir(parents=True);(root/'docs').mkdir()
 for name in ['scripts/render-scope-plan.py','docs/scope-delivery.json','docs/master-scope.json','docs/scope-progress.json','docs/master-scope.md']:
  shutil.copyfile(ROOT/name,root/name)
 plan=json.loads((root/'docs/scope-delivery.json').read_text())
 for package in plan['packages']:(root/package['contract']).parent.mkdir(parents=True,exist_ok=True)
 note=(root/'docs/master-scope.md').read_text().split('\n## Executed component update',1)[1]
 for _ in range(2):
  subprocess.run([sys.executable,str(root/'scripts/render-scope-plan.py')],cwd=root,check=True,capture_output=True,timeout=20)
  output=(root/'docs/master-scope.md').read_text()
  assert output.split('\n## Executed component update',1)[1]==note
  assert output.count('## Executed component update')==note.count('## Executed component update')+1
  assert len([line for line in output.splitlines() if line.startswith('| F-') or line.startswith('| T-') or line.startswith('| X-') or line.startswith('| N-')])==202
