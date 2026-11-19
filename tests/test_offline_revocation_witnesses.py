"""Exercise the optional revocation witness workflow with actual Node subprocesses."""
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def test_selected_witness_observations_on_actual_node():
    result = subprocess.run(
        ['node', '--test', '--test-reporter=tap', 'tests/offline-revocation-witnesses.cjs'],
        cwd=ROOT, capture_output=True, text=True, timeout=90, check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    for tally in ('# tests 9', '# pass 9', '# fail 0', '# skipped 0'):
        assert tally in result.stdout.splitlines()
