"""Fail closed on incomplete native workflow results and unsafe output locations."""
import runpy
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
verifier = runpy.run_path(str(ROOT / 'scripts/verify-ios-share.py'))


def test_complete_native_summary():
    assert verifier['accepted_summary']({'result': 'Passed', 'totalTestCount': 5,
                                        'passedTests': 5, 'failedTests': 0, 'skippedTests': 0})


@pytest.mark.parametrize('field,value', [('result', 'Failed'), ('totalTestCount', 4),
    ('totalTestCount', 6), ('totalTestCount', 5.0), ('passedTests', 4), ('failedTests', 1),
    ('failedTests', False), ('skippedTests', 1), ('skippedTests', False), ('testFailures', ['failure'])])
def test_incomplete_summary_refused(field, value):
    summary = {'result': 'Passed', 'totalTestCount': 5, 'passedTests': 5, 'failedTests': 0, 'skippedTests': 0}
    summary[field] = value
    assert not verifier['accepted_summary'](summary)


@pytest.mark.parametrize('value', [None, [], {}, {'result': 'Passed'}])
def test_missing_summary_refused(value):
    assert not verifier['accepted_summary'](value)


@pytest.mark.parametrize('git_kind', ['directory', 'worktree-file'])
def test_every_git_checkout_refused_before_output_creation(tmp_path, git_kind):
    root = tmp_path / 'unrelated'; root.mkdir()
    if git_kind == 'directory': (root / '.git').mkdir()
    else: (root / '.git').write_text('gitdir: /unrelated/checkout')
    with pytest.raises(ValueError): verifier['destination'](root / 'new-proof')
    assert not (root / 'new-proof').exists()


def test_existing_destination_and_broken_symlink_refused(tmp_path):
    target = tmp_path / 'keep'; target.mkdir(); (target / 'sentinel').write_text('unchanged')
    link = tmp_path / 'link'; link.symlink_to(tmp_path / 'missing')
    for path in [target, link]:
        with pytest.raises(ValueError): verifier['destination'](path)
    assert (target / 'sentinel').read_text() == 'unchanged'


def test_new_non_git_destination_is_only_validated(tmp_path):
    target = tmp_path / 'new-proof'
    assert verifier['destination'](target) == target
    assert not target.exists()


def test_simulator_uuid_case_is_preserved_for_xcode_destination():
    identity = '706597C7-9A9E-4F75-9DE8-48F211D005D4'
    assert verifier['simulator_identity'](identity) == identity
    for invalid in ['not-a-device', '{' + identity + '}', identity.replace('-', '')]:
        with pytest.raises(ValueError): verifier['simulator_identity'](invalid)


@pytest.mark.parametrize('exit_status', [0, 7])
def test_actual_command_exit_and_diagnostics_retained(tmp_path, exit_status):
    import sys
    report = {'command_events': []}
    argv = [sys.executable, '-c', f"import sys; print('synthetic diagnostic'); sys.exit({exit_status})"]
    options = dict(output=tmp_path, stage='synthetic', report=report, created=True)
    if exit_status:
        with pytest.raises(ValueError, match='command failed'):
            verifier['run_command'](argv, **options)
    else:
        assert verifier['run_command'](argv, **options) == 'synthetic diagnostic'
    event = report['command_events'][0]
    assert event['returncode'] == exit_status
    assert event['outcome'] == ('nonzero_exit' if exit_status else 'passed')
    assert event['finished_at'] >= event['started_at']
    assert 'synthetic diagnostic' in (tmp_path / 'synthetic.log').read_text()


def test_actual_deadline_kills_child_and_records_failure(tmp_path):
    import sys, os
    pid = tmp_path / 'child.pid'
    report = {'command_events': []}
    code = f"import os,time,pathlib; pathlib.Path({str(pid)!r}).write_text(str(os.getpid())); time.sleep(20)"
    with pytest.raises(ValueError, match='deadline'):
        verifier['run_command']([sys.executable, '-c', code], output=tmp_path,
            stage='synthetic_deadline', report=report, created=True, timeout=.5)
    assert report['command_events'][0]['outcome'] == 'deadline'
    with pytest.raises(ProcessLookupError): os.kill(int(pid.read_text()), 0)
    assert (tmp_path / 'synthetic_deadline.log').exists()
