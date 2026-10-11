"""Execute the optional group cryptographic workflow, not human authorship validation."""
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def test_group_receipt_controls_run_on_actual_node():
    result = subprocess.run(['node', '--test', '--test-reporter=tap', 'tests/group-receipts.cjs'], cwd=ROOT,
                            capture_output=True, timeout=90, check=False)
    assert result.returncode == 0, result.stdout.decode() + result.stderr.decode()
    assert b'# tests 40' in result.stdout and b'# fail 0' in result.stdout
