"""Execute the actual parsed workflow consumers, not hand-copied test commands."""
import os
from pathlib import Path
import subprocess
import sys

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize('name', [
    'Exercise private synthetic feedback analysis without collecting participant data',
    'Refuse research collection and bound synthetic transport independently of tag routes'])
def test_parsed_feedback_workflow_commands_execute_without_folded_arguments(name):
    workflow = yaml.safe_load((ROOT/'.github/workflows/ci.yml').read_text())
    steps = workflow['jobs']['spec']['steps']
    selected = [step['run'] for step in steps if step.get('name') == name]
    assert len(selected) == 1
    # These selected steps never invoke this test file. Execute the exact parsed
    # string through the same shell mode as Actions, retaining multiline semantics.
    environment = {**os.environ, 'PATH':str(Path(sys.executable).parent)+os.pathsep+os.environ['PATH']}
    process = subprocess.run(['bash','-e','-c',selected[0]], cwd=ROOT,
        env=environment,capture_output=True,timeout=45)
    assert process.returncode == 0, 'Parsed Actions command failed: '+process.stderr.decode(errors='replace')[-2000:]


def test_folded_command_regression_is_rejected_by_actual_shell_and_pytest(monkeypatch):
    name = 'Refuse research collection and bound synthetic transport independently of tag routes'
    broken = {'jobs':{'spec':{'steps':[{'name':name,'run':
        'python -m pytest tests/test_research_http.py tests/test_worker_process.py -q '
        'python scripts/verify-feedback-analysis.py --output output/verification/feedback-analysis.json'}]}}}
    monkeypatch.setattr(yaml, 'safe_load', lambda _:broken)
    with pytest.raises(AssertionError, match='Parsed Actions command failed'):
        test_parsed_feedback_workflow_commands_execute_without_folded_arguments(name)
