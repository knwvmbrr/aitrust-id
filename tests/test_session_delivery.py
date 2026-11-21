"""Delivery accounting must not confuse components with original closures."""
from copy import deepcopy
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest
from tools import session_delivery as tool

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def case(tmp_path):
    board = json.loads((ROOT / 'docs/session-delivery.json').read_bytes())
    baseline = tool.parse(tool.git_bytes(ROOT, board['base_commit'], 'docs/scope-progress.json'))
    master = tool.parse(tool.git_bytes(ROOT, board['base_commit'], 'docs/master-scope.json'))
    # The fixture is a frozen baseline, independent of later genuine closures.
    board['tasks'] = [dict(task_id='fixture-check', original_ids=['T-HP'], worker='builder',
        status='active', deliverable='A complete bounded fixture', done_evidence=['Run and review it'])]
    board['closure_recommendations'] = []
    board['counters'] = dict(finished_scoped_tasks=0, original_requirement_closures=0)
    board['goals']['requirement_goal_status'] = 'NOT MET'
    board['goals']['original_closure_milestone_status'] = 'NOT MET'
    board['goals']['original_open_target_status'] = 'NOT MET'
    board['session_success'] = False
    proof = tmp_path / 'runs' / 'reviewed.json'
    proof.parent.mkdir()
    proof.write_text(json.dumps({'pass': True, 'kind': 'unit_fixture_only',
        'captured_at': datetime.now(timezone.utc).isoformat()}))
    return dict(board=board, baseline=baseline, baseline_master=master,
                current=deepcopy(baseline), current_master=deepcopy(master), root=tmp_path)


def proof(case):
    return [dict(path='runs/reviewed.json', sha256=tool.digest(
        (case['root'] / 'runs/reviewed.json').read_bytes()))]


def close_task(case):
    board = case['board']
    task = board['tasks'][0]
    task['status'] = 'closed'
    task['closure_record'] = dict(closed_at=datetime.now(timezone.utc).isoformat(),
        completed_by='builder', verified_by='reviewer', evidence=proof(case))
    board['counters']['finished_scoped_tasks'] = 1


def close_original(case):
    board = case['board']
    key = 'T-HP'
    old = tool.rows(case['baseline'])[key]
    row = tool.rows(case['current'])[key]
    now = datetime.now(timezone.utc).isoformat()
    row.update(percent_complete=100, queue='completed', completed_by=['builder'],
        completed_at=now, required_acceptance=[], next_fix=None, next_owner=None)
    row['evidence'].append('runs/reviewed.json')
    board['closure_recommendations'] = [dict(id=key, status='verified_complete',
        reviewed_by='reviewer', verified_at=now, original_acceptance_sha256=tool.acceptance_hash(
            tool.rows(case['baseline_master'])[key], old), evidence=proof(case))]
    board['counters']['original_requirement_closures'] = 1
    board['goals']['original_closure_milestone_status'] = 'MET'
    board['goals']['original_open_target_status'] = 'NOT MET'
    board['goals']['requirement_goal_status'] = 'NOT MET'
    board['session_success'] = False


def test_component_completion_never_reduces_original_count(case):
    close_task(case)
    result = tool.inspect(**case)
    assert result['finished_scoped_tasks'] == ['fixture-check']
    assert result['original_open'] == 70
    assert result['new_original_closures'] == []
    assert result['session_success'] is False
    assert result['activity_is_live_heartbeat'] is False


def test_new_original_and_component_are_counted_separately(case):
    close_task(case)
    close_original(case)
    result = tool.inspect(**case)
    assert result['new_original_closures'] == ['T-HP']
    assert result['original_open'] == 69
    assert result['original_closure_milestone_met'] is True
    assert result['original_open_target_met'] is False
    assert result['closures_to_target'] == 9
    assert result['session_success'] is False
    assert result['scope_approval_granted'] is False
    assert result['independent_accuracy_evidence'] is False


@pytest.mark.parametrize('target,expected', [(68, False), (69, True), (70, True), (0, False), (202, True)])
def test_strict_target_above_equal_below_actual_open_count(case, target, expected):
    close_task(case); close_original(case)
    case['board']['goals'].update(original_open_target=target,
        original_open_target_status='MET' if expected else 'NOT MET',
        requirement_goal_status='MET' if expected else 'NOT MET')
    case['board']['session_success'] = expected
    result = tool.inspect(**case)
    assert result['original_open'] == 69
    assert result['original_closure_milestone_met'] is True
    assert result['original_open_target_met'] is expected
    assert result['original_requirement_goal_met'] is expected
    assert result['session_success'] is expected


def test_target_met_does_not_waive_closure_or_scoped_minima(case):
    close_task(case); close_original(case)
    goals=case['board']['goals']; goals.update(original_open_target=69, original_open_target_status='MET',
        minimum_original_requirement_closures=2, original_closure_milestone_status='NOT MET')
    result=tool.inspect(**case)
    assert result['original_open_target_met'] and not result['original_closure_milestone_met']
    assert not result['session_success']
    goals.update(minimum_original_requirement_closures=1, original_closure_milestone_status='MET',
        requirement_goal_status='MET', minimum_finished_named_deliverables=2)
    result=tool.inspect(**case)
    assert result['original_requirement_goal_met'] and not result['scoped_delivery_goal_met']
    assert not result['session_success']


def test_reopened_original_refuses_success_even_when_numeric_target_and_milestone_met(case):
    close_task(case); close_original(case)
    key=next(row['id'] for row in case['baseline']['records'] if row['percent_complete']==100)
    reopened=tool.rows(case['current'])[key]
    reopened.update(percent_complete=80, queue='open', completed_by=None, completed_at=None,
        required_acceptance=['Revalidate the preserved original acceptance'], next_fix='Revalidate', next_owner='builder')
    case['board']['goals'].update(original_open_target=70, original_open_target_status='MET')
    result=tool.inspect(**case)
    assert result['reopened_originals']==[key]
    assert result['original_open_target_met'] and result['original_closure_milestone_met']
    assert not result['no_original_reopens'] and not result['session_success']


def test_legacy_v1_minimum_success_is_historical_not_target_success(case):
    close_task(case); close_original(case)
    board=case['board'];board.update(profile=tool.LEGACY_PROFILE,schema_version=1,session_success=True)
    board['goals']['requirement_goal_status']='MET'
    board['goals'].pop('original_closure_milestone_status');board['goals'].pop('original_open_target_status')
    result=tool.inspect(**case)
    assert result['board_recorded_session_success'] is True
    assert result['board_recorded_status_scope']=='minimum-closure-milestone/v1'
    assert result['original_closure_milestone_met'] is True
    assert result['original_open_target_met'] is False and result['session_success'] is False


@pytest.mark.parametrize('schema,profile',[(1,tool.PROFILE),(2,tool.LEGACY_PROFILE),(True,tool.LEGACY_PROFILE),(2,'unknown')])
def test_board_profile_version_mismatch_is_refused(case,schema,profile):
    case['board'].update(schema_version=schema,profile=profile)
    with pytest.raises(ValueError):tool.inspect(**case)


def test_v2_cannot_relabel_minimum_milestone_as_strict_success(case):
    close_task(case);close_original(case)
    case['board']['goals']['requirement_goal_status']='MET';case['board']['session_success']=True
    with pytest.raises(ValueError):tool.inspect(**case)


@pytest.mark.parametrize('change', [
    lambda c: c['board']['counters'].update(original_requirement_closures=1),
    lambda c: c['board']['counters'].update(finished_scoped_tasks=False),
    lambda c: c['board'].update(session_success=True),
    lambda c: c['board']['goals'].update(requirement_goal_status='MET'),
    lambda c: c['board']['original_open_requirements'].pop(),
    lambda c: c['board']['original_open_requirements'][0].update(required_acceptance=['weakened']),
    lambda c: tool.rows(c['current_master'])['T-HP'].update(acceptance='weakened before closure'),
    lambda c: tool.rows(c['current'])['T-HP'].update(required_acceptance=['weakened before closure']),
    lambda c: c['current']['records'].pop(),
    lambda c: c['current']['records'][-1].update(id='invented'),
    lambda c: c['board']['tag_bots'][0].update(status='active', actual_worker=None),
])
def test_false_progress_or_invented_inventory_is_refused(case, change):
    change(case)
    with pytest.raises(ValueError):
        tool.inspect(**case)


@pytest.mark.parametrize('change', [
    lambda c: c['board']['tasks'][0]['closure_record'].update(verified_by='builder'),
    lambda c: c['board']['tasks'][0]['closure_record'].update(completed_by='reviewer'),
    lambda c: c['board']['tasks'][0]['closure_record'].update(closed_at='2020-01-01T00:00:00+00:00'),
    lambda c: c['board']['tasks'][0]['closure_record'].update(evidence=[]),
    lambda c: c['board']['tasks'][0]['closure_record']['evidence'][0].update(sha256='0' * 64),
    lambda c: (c['root'] / 'runs/reviewed.json').write_text('{"pass":false}'),
    lambda c: (c['root'] / 'runs/reviewed.json').write_text('{"pass":true,"pass":false}'),
])
def test_closed_task_requires_new_reviewed_intact_passing_evidence(case, change):
    close_task(case)
    change(case)
    with pytest.raises(ValueError):
        tool.inspect(**case)


@pytest.mark.parametrize('change', [
    lambda c: c['board']['closure_recommendations'].clear(),
    lambda c: c['board']['closure_recommendations'][0].update(original_acceptance_sha256='0' * 64),
    lambda c: tool.rows(c['current_master'])['T-HP'].update(acceptance='weakened'),
    lambda c: tool.rows(c['current'])['T-HP'].update(completed_at='2020-01-01T00:00:00+00:00'),
    lambda c: tool.rows(c['current'])['T-HP']['evidence'].remove('runs/reviewed.json'),
    lambda c: tool.rows(c['baseline'])['T-HP']['evidence'].append('runs/reviewed.json'),
])
def test_original_closure_requires_preserved_criteria_and_new_ledger_evidence(case, change):
    close_task(case)
    close_original(case)
    change(case)
    with pytest.raises(ValueError):
        tool.inspect(**case)


@pytest.mark.parametrize('raw', [b'{"x":1,"x":2}', b'{"n":NaN}', b'{"n":1e999}', b''])
def test_ambiguous_json_is_refused(raw):
    with pytest.raises(ValueError):
        tool.parse(raw)


@pytest.mark.parametrize('name', ['../secret', '/absolute', 'runs/../secret', './runs/x', 'runs//x'])
def test_unsafe_paths_are_refused(name):
    with pytest.raises(ValueError):
        tool.local_name(name)


def test_regular_bounded_reads_refuse_symlinks_hardlinks_and_fifo(tmp_path):
    target = tmp_path / 'target'
    target.write_bytes(b'public fixture')
    assert tool.read_local(tmp_path, 'target') == b'public fixture'
    (tmp_path / 'link').symlink_to(target)
    with pytest.raises((ValueError, OSError)):
        tool.read_local(tmp_path, 'link')
    os.link(target, tmp_path / 'hardlink')
    with pytest.raises(ValueError):
        tool.read_local(tmp_path, 'hardlink')
    os.mkfifo(tmp_path / 'pipe')
    with pytest.raises(ValueError):
        tool.read_local(tmp_path, 'pipe')


def test_mutable_or_option_like_commit_refused_before_git(monkeypatch):
    calls = []
    monkeypatch.setattr(tool, 'read_local', lambda *args: b'{"base_commit":"--help"}')
    monkeypatch.setattr(tool.subprocess, 'run', lambda *a, **k: calls.append(a))
    with pytest.raises(ValueError):
        tool.inspect_project()
    assert calls == []


def test_actual_cli_reports_real_board_and_unmet_goal_distinctly():
    command = [sys.executable, str(ROOT / 'scripts/session-delivery.py')]
    report = subprocess.run(command, cwd=ROOT, capture_output=True, timeout=15)
    assert report.returncode == 0, report.stdout
    value = json.loads(report.stdout)
    assert value['pass'] is True and value['tag_bots'] == 14
    check = subprocess.run(command + ['--check-session'], cwd=ROOT, capture_output=True, timeout=15)
    checked = json.loads(check.stdout)
    assert check.returncode == (0 if checked['session_success'] else 1)
    assert checked['original_open'] == value['original_open']


def test_invalid_board_cli_has_fixed_text_without_path_disclosure():
    report = subprocess.run([sys.executable, str(ROOT / 'scripts/session-delivery.py'),
        '--board', '../private-marker'], cwd=ROOT, capture_output=True, timeout=15)
    assert report.returncode == 2
    assert b'private-marker' not in report.stdout + report.stderr
    assert json.loads(report.stdout)['pass'] is False


def test_unrecognized_argument_cli_does_not_echo_the_argument():
    report = subprocess.run([sys.executable, str(ROOT / 'scripts/session-delivery.py'),
        '--unknown=PRIVATE_CANARY'], cwd=ROOT, capture_output=True, timeout=15)
    assert report.returncode == 2
    assert b'PRIVATE_CANARY' not in report.stdout + report.stderr
    assert json.loads(report.stdout)['pass'] is False


def test_historical_passing_report_cannot_close_a_new_task(case):
    (case['root'] / 'runs/reviewed.json').write_text(json.dumps({
        'pass': True, 'captured_at': '2020-01-01T00:00:00+00:00'}))
    close_task(case)
    with pytest.raises(ValueError):
        tool.inspect(**case)
