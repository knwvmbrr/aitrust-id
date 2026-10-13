"""Exercise the inactive stream component using real Node web streams."""
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_real_stream_controls():
    node = shutil.which('node')
    assert node, 'Node is required for stream boundary verification'
    result = subprocess.run([node, '--test', '--test-reporter=tap', 'tests/stream-observer.cjs'],
                            cwd=ROOT, text=True, capture_output=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
    assert '# tests 10' in result.stdout and '# pass 10' in result.stdout
    assert '# fail 0' in result.stdout
