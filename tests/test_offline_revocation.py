"""Execute optional selected-log controls; never substitute them for public transparency."""
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def test_optional_revocation_controls_on_actual_node():
    result = subprocess.run(['node', '--test', '--test-reporter=tap', 'tests/offline-revocation.cjs'],
                            cwd=ROOT, capture_output=True, timeout=90, check=False)
    assert result.returncode == 0, result.stdout.decode() + result.stderr.decode()
    assert b'# tests 62' in result.stdout and b'# pass 62' in result.stdout
    assert b'# fail 0' in result.stdout and b'# skipped 0' in result.stdout
