"""Exercise the default evidence check and its selected archive member boundary."""

import io
import json
from pathlib import Path
import runpy
import subprocess
import sys
import tarfile

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/verify-pyodide-release-origin.py"
read_members = runpy.run_path(str(SCRIPT))["tar_members"]


def test_default_check_describes_only_the_pinned_evidence():
    result = subprocess.run([sys.executable, str(SCRIPT)], capture_output=True, check=True, timeout=10)
    report = json.loads(result.stdout)
    assert report["pass"] and report["archives_replayed"] == 0
    assert report["runtime_members_compared"] == 0
    assert report["wasm_rebuilt_from_source"] is False


def test_member_reader_refuses_an_ambiguous_selected_path():
    out = io.BytesIO()
    with tarfile.open(fileobj=out, mode="w") as archive:
        for content in (b"first", b"second"):
            member = tarfile.TarInfo("package/selected")
            member.size = len(content)
            archive.addfile(member, io.BytesIO(content))
    with pytest.raises(ValueError, match="Duplicate"):
        read_members(out.getvalue(), "package/", {"selected"})
