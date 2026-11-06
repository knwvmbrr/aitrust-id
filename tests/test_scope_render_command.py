"""The canonical renderer must repair all views or fail without claiming a pass."""
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import pytest
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('scope_index_gate',ROOT/'scripts/verify-scope-plan.py')
gate=importlib.util.module_from_spec(spec);spec.loader.exec_module(gate)

@pytest.fixture
def selected(tmp_path):
    root=tmp_path/'source';root.mkdir();(root/'scripts').mkdir()
    shutil.copytree(ROOT/'docs',root/'docs')
    data=json.loads((ROOT/'docs/scope-progress.json').read_bytes())
    for group in ('records','packages','subtasks','enhancements'):
        for row in data[group]:
            for name in row['evidence']:
                relative=name.split('#')[0];target=root/relative
                if not target.exists():
                    target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/relative,target)
    for name in ('scope-progress.py','render-scope-plan.py'):shutil.copyfile(ROOT/'scripts'/name,root/'scripts'/name)
    index=root/'docs/scope-task-index.md'
    lines=index.read_text().splitlines()
    for i,line in enumerate(lines):
        if line.startswith('| TASK-F-158 |'):
            import re
            lines[i]=re.sub(r'\| [0-9]+% ·', '| 0% ·',line)
    index.write_text('\n'.join(lines)+'\n')
    return root,data

def test_canonical_render_repairs_all_202_task_percentages(selected):
    root,data=selected
    with pytest.raises(ValueError):gate.verify_task_percentages((root/'docs/scope-task-index.md').read_text(),data['records'])
    p=subprocess.run([sys.executable,str(root/'scripts/scope-progress.py'),'--render'],cwd=root,capture_output=True,timeout=15)
    assert p.returncode==0
    assert gate.verify_task_percentages((root/'docs/scope-task-index.md').read_text(),data['records'])==202
    assert json.loads(p.stdout)['pass'] is True

def test_secondary_renderer_failure_is_not_a_success(selected):
    root,_=selected
    (root/'scripts/render-scope-plan.py').write_text("raise RuntimeError('synthetic renderer failure')\n")
    p=subprocess.run([sys.executable,str(root/'scripts/scope-progress.py'),'--render'],cwd=root,capture_output=True,timeout=15)
    assert p.returncode!=0 and b'"pass": true' not in p.stdout
