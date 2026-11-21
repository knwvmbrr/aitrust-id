"""Count delivery honestly; never approve tag, human or legal acceptance."""
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess

ROOT = Path(__file__).resolve().parents[1]
LIMIT = 4 * 1024 * 1024
SHA = re.compile(r'[a-f0-9]{64}')
COMMIT = re.compile(r'[a-f0-9]{40}')
PROFILE = 'session-delivery-plan/v2'
LEGACY_PROFILE = 'session-delivery-plan/v1'


class DeliveryError(ValueError):
    pass


def require(condition):
    if not condition:
        raise DeliveryError('Delivery accounting contract refused.')


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=True, allow_nan=False).encode('ascii')


def unique(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result)
        result[key] = value
    return result


def parse(raw):
    require(type(raw) is bytes and 0 < len(raw) <= LIMIT)
    def number(value):
        require(len(value) <= 64)
        result = float(value)
        require(math.isfinite(result))
        return result
    def constant(_):
        raise DeliveryError('Delivery accounting contract refused.')
    return json.loads(raw, object_pairs_hook=unique, parse_float=number,
                      parse_constant=constant)


def moment(value):
    require(type(value) is str)
    result = datetime.fromisoformat(value)
    require(result.tzinfo is not None and result <= datetime.now(timezone.utc))
    return result


def identity(value):
    require(type(value) is str and 0 < len(value.strip()) <= 128
            and value == value.strip() and all(ord(c) >= 32 for c in value))
    return value


def local_name(name):
    require(type(name) is str and 0 < len(name) <= 256 and '\0' not in name)
    path = PurePosixPath(name)
    require(not path.is_absolute() and '..' not in path.parts
            and path.as_posix() == name and bool(path.parts))
    return path


def read_local(root, name):
    """Descriptor-relative no-follow reads of bounded public project files."""
    path = local_name(name)
    owned = []
    try:
        directory = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        owned.append(directory)
        for part in path.parts[:-1]:
            directory = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                                dir_fd=directory)
            owned.append(directory)
        fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
                     dir_fd=directory)
        owned.append(fd)
        before = os.fstat(fd)
        require(stat.S_ISREG(before.st_mode) and before.st_nlink == 1
                and 0 < before.st_size <= LIMIT)
        raw = bytearray()
        while len(raw) <= LIMIT:
            chunk = os.read(fd, min(65536, LIMIT + 1 - len(raw)))
            if not chunk:
                break
            raw.extend(chunk)
        after = os.fstat(fd)
        named = os.stat(path.name, dir_fd=directory, follow_symlinks=False)
        fields = lambda s: (s.st_dev, s.st_ino, s.st_mode, s.st_nlink,
                            s.st_size, s.st_mtime_ns, s.st_ctime_ns)
        require(len(raw) == before.st_size and fields(before) == fields(after)
                == fields(named))
        return bytes(raw)
    finally:
        first = None
        for fd in reversed(owned):
            try:
                os.close(fd)
            except OSError as error:
                if first is None:
                    first = error
        if first:
            raise DeliveryError('Delivery accounting handles unavailable.') from None


def git_bytes(root, revision, name):
    require(type(revision) is str and COMMIT.fullmatch(revision) is not None)
    local_name(name)
    spec = revision + ':' + name
    size = subprocess.run(['git', 'cat-file', '-s', spec], cwd=root,
                          capture_output=True, timeout=10, check=True).stdout
    require(size.strip().isdigit() and 0 < int(size) <= LIMIT)
    raw = subprocess.run(['git', 'cat-file', 'blob', spec], cwd=root,
                         capture_output=True, timeout=10, check=True).stdout
    require(len(raw) == int(size))
    return raw


def rows(value):
    require(type(value) is dict and type(value.get('records')) is list
            and len(value['records']) == 202)
    result = {}
    for row in value['records']:
        require(type(row) is dict and type(row.get('id')) is str
                and row['id'] not in result)
        result[row['id']] = row
    return result


def complete(row):
    value = row.get('percent_complete')
    require(type(value) is int and value in range(0, 101, 20))
    if value == 100:
        require(row.get('queue') == 'completed' and row.get('completed_by')
                and row.get('completed_at') and not row.get('required_acceptance')
                and row.get('next_fix') in (None, '') and row.get('next_owner') in (None, ''))
        moment(row['completed_at'])
        return True
    require(row.get('queue') == 'open' and row.get('required_acceptance')
            and row.get('next_fix') and row.get('next_owner')
            and not row.get('completed_by') and row.get('completed_at') is None)
    return False


def acceptance_hash(master, ledger):
    return digest(canonical({'master': {k: master[k] for k in
                                      ('baseline_job', 'outcome', 'acceptance')},
                             'required_acceptance': ledger['required_acceptance']}))


def evidence(items, root, since):
    require(type(items) is list and 0 < len(items) <= 32)
    seen = set()
    for row in items:
        require(type(row) is dict and set(row) == {'path', 'sha256'})
        name = row['path']
        local_name(name)
        require(name.startswith('runs/') and name.endswith('.json') and name not in seen
                and type(row['sha256']) is str and SHA.fullmatch(row['sha256']))
        seen.add(name)
        raw = read_local(root, name)
        require(digest(raw) == row['sha256'])
        report = parse(raw)
        require(type(report) is dict and report.get('pass') is True
                and moment(report.get('captured_at')) >= since)
    return seen


def inspect(board, baseline, baseline_master, current, current_master, root=ROOT):
    require(type(board) is dict and board.get('profile') in (PROFILE, LEGACY_PROFILE))
    legacy = board['profile'] == LEGACY_PROFILE
    require(type(board.get('schema_version')) is int
            and board['schema_version'] == (1 if legacy else 2))
    started = moment(board['recorded_at'])
    before, after = rows(baseline), rows(current)
    old_master, new_master = rows(baseline_master), rows(current_master)
    require(before.keys() == after.keys() == old_master.keys() == new_master.keys())
    for key in before:
        # Prevent laundering weaker criteria into the next session's baseline,
        # even when this session does not yet claim that original as complete.
        require({k: new_master[key][k] for k in ('baseline_job', 'outcome', 'acceptance')}
                == {k: old_master[key][k] for k in ('baseline_job', 'outcome', 'acceptance')})
        if before[key]['percent_complete'] < 100 and after[key]['percent_complete'] < 100:
            require(after[key]['required_acceptance'] == before[key]['required_acceptance'])
    old_done = {key for key, row in before.items() if complete(row)}
    new_done = {key for key, row in after.items() if complete(row)}
    old_open = set(before) - old_done
    require(board['baseline']['original_total'] == len(before)
            and type(board['baseline']['original_total']) is int
            and board['baseline']['original_complete'] == len(old_done)
            and type(board['baseline']['original_complete']) is int
            and board['baseline']['original_open'] == len(old_open)
            and type(board['baseline']['original_open']) is int
            and type(board['baseline']['open_ids']) is list
            and len(board['baseline']['open_ids']) == len(old_open)
            and set(board['baseline']['open_ids']) == old_open)
    snapshots = board['original_open_requirements']
    require(type(snapshots) is list and len(snapshots) == len(old_open))
    indexed = {}
    for row in snapshots:
        require(type(row) is dict and row.get('id') in old_open and row['id'] not in indexed)
        key = row['id']
        require(type(row['percent_at_baseline']) is int and row['percent_at_baseline'] == before[key]['percent_complete']
                and row['required_acceptance'] == before[key]['required_acceptance']
                and row['baseline_job'] == old_master[key]['baseline_job']
                and row['outcome'] == old_master[key]['outcome']
                and row['master_acceptance'] == old_master[key]['acceptance']
                and row['stable_next_fix'] == before[key]['next_fix'])
        require(row.get('accountable_lane') and row.get('done_evidence')
                and row.get('next_unblocked_action') and row.get('blocker'))
        indexed[key] = row
    tag_ids = {key for key in before if key.startswith('T-')}
    bots = board['tag_bots']
    require(type(bots) is list and len(bots) == len(tag_ids) == 14)
    bot_ids, workers, seen_tags = set(), set(), set()
    for bot in bots:
        require(bot['tag_id'] in tag_ids and bot['tag_id'] not in seen_tags
                and type(bot['bot_id']) is str and bot['bot_id'] not in bot_ids
                and bot['status'] in ('queued', 'active', 'blocked', 'reviewed', 'published'))
        moment(bot['checked_at'])
        seen_tags.add(bot['tag_id']); bot_ids.add(bot['bot_id'])
        if bot['status'] == 'active':
            require(type(bot['actual_worker']) is str and bot['actual_worker']
                    and bot['actual_worker'] not in workers)
            workers.add(bot['actual_worker'])
        else:
            require(bot['actual_worker'] is None)
    require(board['activity_semantics'] ==
            'Dated assignment snapshot; not a background process/heartbeat')
    tasks = board['tasks']
    require(type(tasks) is list and 0 < len(tasks) <= 256)
    task_ids, finished = set(), []
    for task in tasks:
        require(task['task_id'] not in task_ids and task['original_ids']
                and set(task['original_ids']) <= before.keys()
                and task['status'] in ('queued', 'active', 'blocked', 'in_review', 'closed')
                and task.get('deliverable') and task.get('done_evidence'))
        task_ids.add(task['task_id'])
        if task['status'] == 'closed':
            closed = task['closure_record']
            require(moment(closed['closed_at']) >= started
                    and identity(closed['verified_by']) != identity(closed['completed_by'])
                    and closed['verified_by'] != identity(task['worker']))
            evidence(closed['evidence'], root, started)
            finished.append(task['task_id'])
        else:
            require(not task.get('closure_record'))
    transitions = new_done - old_done
    reopened = old_done - new_done
    recommendations = board['closure_recommendations']
    require(type(recommendations) is list and len(recommendations) == len(transitions))
    recommended = set()
    for row in recommendations:
        key = row['id']
        require(key in transitions and key not in recommended
                and row['status'] == 'verified_complete' and identity(row.get('reviewed_by'))
                and moment(row['verified_at']) >= started
                and moment(after[key]['completed_at']) >= started
                and row['original_acceptance_sha256'] == acceptance_hash(old_master[key], before[key]))
        require({k: new_master[key][k] for k in ('baseline_job', 'outcome', 'acceptance')}
                == {k: old_master[key][k] for k in ('baseline_job', 'outcome', 'acceptance')})
        require(type(after[key]['completed_by']) is list
                and row['reviewed_by'] not in after[key]['completed_by'])
        supplied = evidence(row['evidence'], root, started)
        require(supplied <= set(after[key]['evidence'])
                and bool(supplied - set(before[key]['evidence'])))
        recommended.add(key)
    require(type(board['counters']) is dict and all(type(v) is int for v in board['counters'].values()))
    require(board['counters'] == {'finished_scoped_tasks': len(finished),
                                   'original_requirement_closures': len(transitions)})
    goals = board['goals']
    for field in ('minimum_finished_named_deliverables', 'minimum_original_requirement_closures'):
        require(type(goals[field]) is int and 1 <= goals[field] <= 202)
    require(type(goals['original_open_target']) is int and 0 <= goals['original_open_target'] <= 202)
    closure_milestone_met = len(transitions) >= goals['minimum_original_requirement_closures']
    original_open = len(after) - len(new_done)
    target_met = original_open <= goals['original_open_target']
    no_reopens = not reopened
    original_met = closure_milestone_met and target_met and no_reopens
    tasks_met = len(finished) >= goals['minimum_finished_named_deliverables']
    strict_success = original_met and tasks_met
    # V1 recorded the minimum-closure milestone. Preserve its historical meaning,
    # but never use that boolean as authority for the strict numeric target.
    recorded_original_met = closure_milestone_met and no_reopens if legacy else original_met
    require(goals['requirement_goal_status'] == ('MET' if recorded_original_met else 'NOT MET')
            and type(board['session_success']) is bool
            and board['session_success'] == (recorded_original_met and tasks_met))
    if not legacy:
        require(goals['original_closure_milestone_status'] == ('MET' if closure_milestone_met else 'NOT MET')
                and goals['original_open_target_status'] == ('MET' if target_met else 'NOT MET'))
    return {'captured_at': datetime.now(timezone.utc).isoformat(), 'pass': True,
            'kind': 'session_delivery_accounting', 'session_id': board['session_id'],
            'baseline_original_complete': len(old_done), 'original_complete': len(new_done),
            'original_open': original_open,
            'new_original_closures': sorted(transitions), 'reopened_originals': sorted(reopened),
            'finished_scoped_tasks': finished, 'original_requirement_goal_met': original_met,
            'scoped_delivery_goal_met': tasks_met, 'session_success': strict_success,
            'original_closure_milestone_met': closure_milestone_met,
            'original_open_target_met': target_met, 'no_original_reopens': no_reopens,
            'requirement_goal_status': 'MET' if original_met else 'NOT MET',
            'board_profile': board['profile'],
            'board_recorded_session_success': board['session_success'],
            'board_recorded_status_scope': 'minimum-closure-milestone/v1' if legacy else 'strict-open-target/v2',
            'target_open': goals['original_open_target'],
            'closures_to_target': max(0, len(after) - len(new_done) - goals['original_open_target']),
            'tag_bots': len(bots), 'active_tag_assignments_at_snapshot': len(workers),
            'activity_is_live_heartbeat': False, 'scope_approval_granted': False,
            'independent_accuracy_evidence': False,
            'scope': 'Identity, evidence hashes and delivery accounting only; full acceptance remains a review judgment.'}


def inspect_project(root=ROOT, board_name='docs/session-delivery.json'):
    board = parse(read_local(root, board_name))
    base = board['base_commit']
    require(type(base) is str and COMMIT.fullmatch(base))
    subprocess.run(['git', 'merge-base', '--is-ancestor', base, 'HEAD'], cwd=root,
                   capture_output=True, timeout=10, check=True)
    inputs = board['input_sha256']
    require(type(inputs) is dict and 3 <= len(inputs) <= 64)
    require({'docs/master-scope.json', 'docs/scope-progress.json', 'docs/scope-delivery.json'} <= inputs.keys())
    cache = {}
    for name, expected in inputs.items():
        require(type(expected) is str and SHA.fullmatch(expected))
        cache[name] = git_bytes(root, base, name)
        require(digest(cache[name]) == expected)
    result = inspect(board, parse(cache['docs/scope-progress.json']),
                     parse(cache['docs/master-scope.json']),
                     parse(read_local(root, 'docs/scope-progress.json')),
                     parse(read_local(root, 'docs/master-scope.json')), root)
    result['baseline_commit'] = base
    result['board_sha256'] = digest(canonical(board))
    return result
