"""Real child failure controls and publication inputs belong to build evidence."""
from pathlib import Path
import json
import os
import shutil
import signal
import subprocess
import time

import pytest

from protocol.revalidation import ROOT, fingerprint


def test_real_child_build_phase_controls():
    result = subprocess.run(
        ['node', '--test', '--test-reporter=tap', 'tests/website-build-phases.cjs'],
        cwd=ROOT, capture_output=True, timeout=30, check=False)
    assert result.returncode == 0, result.stdout.decode() + result.stderr.decode()
    assert b'# tests 8' in result.stdout
    assert b'# fail 0' in result.stdout


def test_diagnostic_runner_and_guarded_writer_are_bound():
    required = {'scripts/website-build-phases.cjs',
                'scripts/verify-built-website.cjs', 'scripts/execution-report.cjs',
                'tests/website-build-phases.cjs',
                'tests/test_website_build_diagnostics.py'}
    current = fingerprint('website')
    assert required <= current['sources'].keys()
    assert 'tests/test_website_build_diagnostics.py' in current['commands'][0]


@pytest.mark.parametrize('name', [
    'session-revision-plan.md', 'session-revisions.md',
    'session-revision-result.md'])
def test_public_revision_guide_projection_is_exact_and_bound(name):
    public = Path('site/public/reference') / name
    assert (ROOT / public).read_bytes() == (ROOT / 'docs' / name).read_bytes()
    assert public.as_posix() in fingerprint('website')['sources']


@pytest.fixture
def controller_fixture(tmp_path):
    scripts = tmp_path / 'scripts'
    scripts.mkdir()
    (tmp_path / 'tests').mkdir()
    for name in ['verify-built-website.cjs', 'website-build-phases.cjs',
                 'execution-report.cjs', 'static-headers.cjs']:
        shutil.copyfile(ROOT / 'scripts' / name, scripts / name)
    report = tmp_path / 'output/verification/website-build-phases.json'
    report.parent.mkdir(parents=True)
    report.write_text(json.dumps({'pass': True, 'old_success': True}))
    return tmp_path, report


def test_actual_controller_replaces_old_success_with_real_child_failure(controller_fixture):
    root, report = controller_fixture
    (root / 'tests/blind-review-files.cjs').write_text('process.exit(7);\n')
    result = subprocess.run(['node', 'scripts/verify-built-website.cjs'],
                            cwd=root, capture_output=True, timeout=15)
    assert result.returncode == 1
    observed = json.loads(report.read_text())
    assert observed['pass'] is False
    assert 'old_success' not in observed
    # The first command is Node's test runner, which reports a failed worker as 1.
    # The direct child-exit-7 contract is exercised separately by the core tests.
    assert observed['phases'][0]['exit_status'] == 1
    assert observed['controller_aborted'] is True


def test_report_destination_refusal_prevents_the_first_child(controller_fixture):
    root, report = controller_fixture
    marker = root / 'child-started'
    (root / 'tests/blind-review-files.cjs').write_text(
        "require('node:fs').writeFileSync('child-started','started');\n")
    report.unlink()
    outside = root / 'original.json'
    outside.write_text('original public fixture\n')
    report.symlink_to(outside)
    result = subprocess.run(['node', 'scripts/verify-built-website.cjs'],
                            cwd=root, capture_output=True, timeout=15)
    assert result.returncode == 1
    assert not marker.exists()
    assert outside.read_text() == 'original public fixture\n'
    assert b'BUILD_PHASE_REPORT_UNAVAILABLE' in result.stderr


@pytest.mark.skipif(os.name != 'posix', reason='Owned process-group interruption control requires POSIX')
def test_actual_parent_interruption_cannot_leave_a_previous_pass(controller_fixture):
    root, report = controller_fixture
    marker = root / 'child-started'
    (root / 'tests/blind-review-files.cjs').write_text(
        "require('node:fs').writeFileSync('child-started','started');"
        'setInterval(()=>{},1000);\n')
    process = subprocess.Popen(['node', 'scripts/verify-built-website.cjs'],
                               cwd=root, stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL, start_new_session=True)
    try:
        deadline = time.monotonic() + 10
        while not marker.exists() and process.poll() is None and time.monotonic() < deadline:
            time.sleep(.02)
        assert marker.exists()
        observed = json.loads(report.read_text())
        assert observed['pass'] is False
        assert 'old_success' not in observed
    finally:
        # This process and its child were created for this disposable test only.
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        process.wait(timeout=10)
    assert json.loads(report.read_text())['pass'] is False
