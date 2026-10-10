"""Execute the configured hosted report command against the real report writer."""
import json
from pathlib import Path
import shlex
import subprocess
import sys
import yaml
ROOT=Path(__file__).resolve().parents[1]


def test_ci_generates_the_exact_artifact_path_without_weaker_report_policy():
    workflow=yaml.safe_load((ROOT/'.github/workflows/ci.yml').read_text())
    steps=workflow['jobs']['regressions']['steps']
    command=next(shlex.split(step['run']) for step in steps
                 if 'scripts/verify-regressions.py --output' in step.get('run',''))
    assert command[0]=='python' and len(command)==4 and command[2]=='--output'
    path=Path(command[3])
    assert path.parts[:2]==('output','verification') and '..' not in path.parts
    upload=next(step for step in steps if step.get('uses','').startswith('actions/upload-artifact@'))
    assert upload['with']['path']==str(path)
    assert upload['with']['if-no-files-found']=='error'
    target=ROOT/path
    existed=target.exists()
    previous=target.read_bytes() if existed else None
    try:
        result=subprocess.run([sys.executable,*command[1:]],cwd=ROOT,
                              capture_output=True,timeout=30)
        assert result.returncode==0, result.stderr.decode()
        record=json.loads(target.read_text())
        assert record['regression_pass'] and record['case_count']==86
        assert len(record['datasets'])==5
        assert record['independent_accuracy_evidence'] is False
        assert record['release_assessed'] is False
    finally:
        if existed:target.write_bytes(previous)
        else:target.unlink(missing_ok=True)
