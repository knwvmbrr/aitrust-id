"""Offline policy verification; GitHub parsing and scheduled execution are separate."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = {('github-actions', '/'), ('npm', '/'), ('npm', '/site'),
            ('pip', '/eval'), ('pip', '/services/gateway'),
            ('pip', '/services/evaluator'), ('pip', '/services/anonymizer'),
            ('docker', '/services/gateway'), ('docker', '/services/evaluator'),
            ('docker', '/services/anonymizer')}
OWNER = 'knwvmbrr'


def file(root, name):
    if root.is_symlink():
        raise ValueError('Dependency policy root symlink refused')
    path = root / name
    for candidate in (path, *path.parents):
        if candidate == root:
            break
        if candidate.is_symlink():
            raise ValueError('Dependency policy symlink refused')
    if not path.is_file() or path.stat().st_size > 500_000:
        raise ValueError('Dependency policy source missing or oversized: ' + name)
    return path


def unique(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError('Duplicate configuration key')
        value[key] = item
    return value


def verify(root=ROOT):
    owners = [line.strip() for line in file(root, '.github/CODEOWNERS').read_text().splitlines()
              if line.strip() and not line.lstrip().startswith('#')]
    if owners != ['* @' + OWNER]:
        raise ValueError('Whole-tree accountable ownership changed or omitted')
    data = json.loads(file(root, '.github/dependabot.yml').read_text(), object_pairs_hook=unique)
    if set(data) != {'version', 'updates'} or type(data['version']) is not int or data['version'] != 2:
        raise ValueError('Unexpected dependency configuration or registry privileges')
    rows = data['updates']
    if not isinstance(rows, list) or len(rows) != len(EXPECTED):
        raise ValueError('Missing or duplicate dependency monitoring roots')
    seen = set()
    for index, row in enumerate(rows):
        if not isinstance(row, dict) or set(row) != {'package-ecosystem', 'directory', 'schedule',
                                                    'open-pull-requests-limit', 'assignees', 'commit-message'}:
            raise ValueError('Unsupported dependency update permissions or overrides')
        key = (row['package-ecosystem'], row['directory'])
        if key not in EXPECTED or key in seen:
            raise ValueError('Missing, duplicated or inactive monitoring root')
        seen.add(key)
        schedule = row['schedule']
        if schedule != {'interval': 'weekly', 'day': 'monday', 'time': f'04:{index * 5:02d}', 'timezone': 'Etc/UTC'}:
            raise ValueError('Scheduled proposal contract changed')
        if (type(row['open-pull-requests-limit']) is not int or row['open-pull-requests-limit'] != 1
                or row['assignees'] != [OWNER] or row['commit-message'] != {'prefix': 'deps', 'include': 'scope'}):
            raise ValueError('Proposal limits, accountable assignment or attribution changed')
        ecosystem, directory = key
        base = directory.lstrip('/')
        required = {'npm': ['package.json', 'package-lock.json'],
                    'pip': ['requirements.txt', 'requirements.lock'],
                    'docker': ['Dockerfile'], 'github-actions': ['.github/workflows/ci.yml']}[ecosystem]
        for name in required:
            file(root, str(Path(base) / name))
    return {'pass': True, 'kind': 'offline_dependency_proposal_policy', 'monitoring_roots': len(seen),
            'active_install_roots': 6, 'active_images': 3, 'actions_monitored': True,
            'whole_tree_owner': OWNER, 'proposals_per_root_limit': 1, 'auto_merge_configured': False,
            'github_configuration_accepted': False, 'scheduled_jobs_observed': False,
            'independent_review': False, 'release_gates_waived': False}


if __name__ == '__main__':
    try:
        result = verify()
    except (OSError, ValueError, TypeError, KeyError):
        result = {'pass': False, 'reason': 'dependency_proposal_policy_refused'}
    print(json.dumps(result))
    raise SystemExit(0 if result['pass'] else 1)
