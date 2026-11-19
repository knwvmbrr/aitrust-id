"""Source-bound distribution decisions, not legal or detector clearance.

The reviewed repository and this policy are the trust root. No received archive,
package label, optional flag or caller can approve its own dependencies.
"""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat

ROOT = Path(__file__).resolve().parents[1]
POLICY = 'eval/dependency-policy.json'
PROFILE = 'technical-dependency-conflict-policy/v1'
ROUTES = frozenset({
    'ps-source', 'source-snapshot', 'web-checker', 'ios-app', 'android-app',
    'gateway-linux-amd64', 'evaluator-linux-amd64', 'anonymizer-linux-amd64',
    'nli-linux-x86_64', 'nli-macos-arm64', 'c2pa-linux-x86_64',
    'c2pa-macos-arm64', 'mcp-stdio', 'node-build-tools',
})
PROJECT_FILES = frozenset({
    'scripts/check-ps.py', 'scripts/worker_process.py',
    'scripts/build-device-detector.py', 'services/evaluator/app.py',
    'protocol/normalization.py', 'LICENSE', 'docs/ps-source-distribution.md',
})
UNICODE_FILES = frozenset({'protocol/unicode15-data.json', 'eval/vectors/unicode/LICENSE.txt'})
PROJECT_ATTRIBUTION = b'AITrust-ID\nCopyright 2026 Michael Raashad McGuire and AITrust-ID contributors.\n'
REVIEWS = {
    'project-ps-source': ('Apache-2.0', PROJECT_FILES, 'LICENSE'),
    'unicode-nfc-tables': ('Unicode-3.0', UNICODE_FILES, 'eval/vectors/unicode/LICENSE.txt'),
}
STATUSES = {'allowed', 'blocked_unknown', 'prohibited', 'paid'}
SHA = re.compile(r'[a-f0-9]{64}')
ID = re.compile(r'[a-z][a-z0-9_-]{0,79}')
MAX_MEMBER = 8_000_000
LICENSE_HASHES = {
    'Apache-2.0': 'cfc7749b96f63bd31c3c42b5c471bf756814053e847c10f3eb003417bc523d30',
    'Unicode-3.0': 'e7a93b009565cfce55919a381437ac4db883e9da2126fa28b91d12732bc53d96',
}
PS_PREREQUISITES = [
    'Independently obtained CPython 3.12 or newer; no interpreter is bundled or licensed by this source profile.',
    'macOS or Linux with the existing POSIX process/file interfaces; OS rights are external prerequisites.',
    'This profile approves only the listed source-and-notice package, not the full Python/OS distribution or independent PS accuracy.',
]


class PolicyError(ValueError):
    """Fixed messages do not disclose source values or private paths."""


def require(value):
    if not value:
        raise PolicyError('Dependency policy refused')


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=True,
                      allow_nan=False, separators=(',', ':')).encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def unique(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result)
        result[key] = value
    return result


def path_name(name):
    require(type(name) is str and 0 < len(name) <= 240 and name.isascii() and
            re.fullmatch(r'[A-Za-z0-9_.\-/]+', name) and
            not PurePosixPath(name).is_absolute() and
            all(part not in ('', '.', '..') for part in name.split('/')))
    return name


def read(root, name, limit=MAX_MEMBER):
    """Descriptor-bound, no-link read with a stable regular-file identity."""
    parts = Path(root).absolute().parts
    fd = os.open(parts[0], os.O_RDONLY | os.O_DIRECTORY)
    try:
        for part in (*parts[1:], *path_name(name).split('/')[:-1]):
            require(part not in ('.', '..'))
            following = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = following
        source = os.open(name.split('/')[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
        with os.fdopen(source, 'rb') as stream:
            before = os.fstat(stream.fileno())
            require(stat.S_ISREG(before.st_mode) and before.st_nlink == 1 and 0 < before.st_size <= limit)
            raw = stream.read(limit + 1)
            after = os.fstat(stream.fileno())
            identity = lambda item: (item.st_dev, item.st_ino, item.st_size, item.st_mtime_ns, item.st_ctime_ns)
            require(len(raw) == before.st_size and identity(before) == identity(after))
            return raw
    finally:
        os.close(fd)


def stamp(value):
    require(type(value) is str and len(value) <= 50)
    when = datetime.fromisoformat(value)
    require(when.tzinfo is not None and when <= datetime.now(timezone.utc))


def file_rows(rows):
    require(type(rows) is list and 0 < len(rows) <= 64)
    seen = set()
    for row in rows:
        require(type(row) is dict and set(row) == {'path', 'sha256', 'bytes'})
        name = path_name(row['path'])
        require(name not in seen and type(row['sha256']) is str and SHA.fullmatch(row['sha256']) and
                type(row['bytes']) is int and 0 < row['bytes'] <= MAX_MEMBER)
        seen.add(name)
    return seen


def load(root=ROOT):
    raw = read(root, POLICY, 1_000_000)
    value = json.loads(raw.decode('utf-8'), object_pairs_hook=unique,
                       parse_constant=lambda _: require(False))
    require(type(value) is dict and set(value) == {
        'schema_version', 'profile', 'captured_at', 'reviewed_by', 'claims',
        'components', 'routes', 'exceptions',
    })
    require(type(value['schema_version']) is int and value['schema_version'] == 1 and
            value['profile'] == PROFILE and value['reviewed_by'] == 'Codex' and value['exceptions'] == [])
    stamp(value['captured_at'])
    require(value['claims'] == {'legal_clearance': False, 'independent_accuracy': False,
                                'complete_project_obligations': False} and
            all(type(item) is bool for item in value['claims'].values()))
    require(type(value['routes']) is dict and set(value['routes']) == ROUTES and
            type(value['components']) is dict and 2 <= len(value['components']) <= 64)
    require(all(type(identity) is str and ID.fullmatch(identity) for identity in value['components']))
    return value, raw


def validate_component(component):
    require(type(component) is dict and set(component) == {
        'assessment', 'license_expression', 'source_available', 'required_processing_payment',
        'files', 'notice_paths', 'review_scope',
    })
    require(component['assessment'] in {'reviewed_source_distribution', 'pending'} and
            (component['license_expression'] is None or
             type(component['license_expression']) is str and 0 < len(component['license_expression']) <= 160))
    for key in ('source_available', 'required_processing_payment'):
        require(component[key] is None or type(component[key]) is bool)
    names = file_rows(component['files'])
    require(type(component['notice_paths']) is list and len(component['notice_paths']) <= 16 and
            all(type(name) is str and name in names for name in component['notice_paths']) and
            len(set(component['notice_paths'])) == len(component['notice_paths']))
    require(type(component['review_scope']) is str and 1 <= len(component['review_scope']) <= 1000)


def validate_route(route, components):
    require(type(route) is dict and set(route) == {
        'kind', 'dependencies', 'prerequisites', 'entrypoints', 'release_scope',
    })
    require(route['kind'] in {'source-only', 'bundled-runtime', 'build-tools', 'optional-model',
                              'optional-sdk', 'platform-app', 'whole-repository'})
    require(type(route['dependencies']) is list and 1 <= len(route['dependencies']) <= 32)
    selected = set()
    for dependency in route['dependencies']:
        require(type(dependency) is dict and set(dependency) == {'component', 'required'} and
                dependency['required'] is True and type(dependency['required']) is bool and
                type(dependency['component']) is str and dependency['component'] in components and
                dependency['component'] not in selected)
        selected.add(dependency['component'])
        validate_component(components[dependency['component']])
    require(type(route['prerequisites']) is list and 1 <= len(route['prerequisites']) <= 16 and
            all(type(item) is str and 1 <= len(item) <= 500 for item in route['prerequisites']))
    require(type(route['entrypoints']) is list and 1 <= len(route['entrypoints']) <= 8 and
            all(type(item) is str and 1 <= len(item) <= 240 for item in route['entrypoints']))
    require(type(route['release_scope']) is str and 1 <= len(route['release_scope']) <= 1000)


def component_status(identity, component, root):
    if component['required_processing_payment'] is True:
        return 'paid', 'required_processing_payment'
    if component['source_available'] is False:
        return 'prohibited', 'required_processor_declared_closed'
    if identity not in REVIEWS or component['assessment'] != 'reviewed_source_distribution':
        return 'blocked_unknown', 'obligation_review_incomplete'
    license_id, expected, notice = REVIEWS[identity]
    if (component['license_expression'] != license_id or component['source_available'] is not True or
            component['required_processing_payment'] is not False or
            {row['path'] for row in component['files']} != expected or
            component['notice_paths'] != ([notice, 'docs/ps-source-distribution.md']
                                          if identity == 'project-ps-source' else [notice])):
        return 'blocked_unknown', 'reviewed_source_profile_changed'
    try:
        for item in component['files']:
            raw = read(root, item['path'])
            if len(raw) != item['bytes'] or sha(raw) != item['sha256']:
                return 'blocked_unknown', 'selected_source_or_notice_changed'
            if identity == 'project-ps-source' and item['path'] == 'docs/ps-source-distribution.md' and PROJECT_ATTRIBUTION not in raw:
                return 'blocked_unknown', 'applicable_project_attribution_missing'
            if item['path'] == notice and sha(raw) != LICENSE_HASHES[license_id]:
                return 'blocked_unknown', 'license_text_requires_review'
    except (OSError, ValueError, TypeError):
        return 'blocked_unknown', 'selected_source_or_notice_unavailable'
    return 'allowed', 'exact_source_and_notice_profile'


def _evaluate(route, root):
    require(type(route) is str and len(route) <= 100)
    value, raw = load(root)
    if route not in value['routes']:
        return value, None, {'profile': PROFILE, 'route': 'unrecognized', 'status': 'blocked_unknown',
                             'release_allowed': False, 'reason': 'unrecognized_route', 'components': []}
    selected = value['routes'][route]
    # A broken or unavailable optional route cannot poison a different valid
    # route. Validate the chosen graph; --all audits every declared selection.
    validate_route(selected, value['components'])
    components = []
    for dependency in selected['dependencies']:
        identity = dependency['component']
        status, reason = component_status(identity, value['components'][identity], root)
        components.append({'id': identity, 'status': status, 'reason': reason})
    # A reviewed source component cannot be reused to bless another artifact's
    # platform, compiled code, transitive graph or redistribution arrangement.
    if (route != 'ps-source' or selected['kind'] != 'source-only' or
            {row['component'] for row in selected['dependencies']} != set(REVIEWS) or
            selected['entrypoints'] != ['python3 -I -S -B scripts/check-ps.py'] or
            selected['prerequisites'] != PS_PREREQUISITES):
        if all(row['status'] == 'allowed' for row in components):
            components.append({'id': 'distribution-scope', 'status': 'blocked_unknown',
                               'reason': 'distribution_profile_not_reviewed'})
    order = {'allowed': 0, 'blocked_unknown': 1, 'prohibited': 2, 'paid': 3}
    status = max((item['status'] for item in components), key=order.__getitem__)
    require(read(root, POLICY, 1_000_000) == raw)
    result = {'profile': PROFILE, 'route': route, 'status': status,
              'release_allowed': status == 'allowed', 'components': components,
              'scope': selected['release_scope'], 'legal_clearance': False,
              'independent_accuracy_evidence': False, 'complete_project_obligations': False}
    projection = {'profile': PROFILE, 'route': selected,
                  'components': {row['component']: value['components'][row['component']]
                                 for row in selected['dependencies']}, 'claims': value['claims']}
    return value, projection, result


def evaluate(route, root=ROOT):
    """Refuse safely, without echoing private paths or malformed input."""
    try:
        return _evaluate(route, root)[2]
    except (OSError, ValueError, TypeError, KeyError, OverflowError, RecursionError):
        return {'profile': PROFILE, 'route': route if type(route) is str and route in ROUTES else 'unrecognized',
                'status': 'blocked_unknown', 'release_allowed': False,
                'reason': 'invalid_or_unavailable_policy', 'components': [],
                'legal_clearance': False, 'independent_accuracy_evidence': False,
                'complete_project_obligations': False}


def require_route(route, root=ROOT):
    """Return only the source export contract for an actually admitted route."""
    try:
        value, projection, result = _evaluate(route, root)
        require(result['release_allowed'] is True and route == 'ps-source')
        selected = value['routes'][route]
        files = [item for row in selected['dependencies']
                 for item in value['components'][row['component']]['files']]
        require(len(files) == 9 and {item['path'] for item in files} == PROJECT_FILES | UNICODE_FILES)
        # This is a selected-route digest. An unrelated blocked scope's update
        # cannot invalidate a PS artifact with identical source/notice terms.
        return {'profile': PROFILE, 'route': route,
                'files': sorted(files, key=lambda item: item['path']),
                'prerequisites': selected['prerequisites'], 'policy_sha256': sha(canonical(projection))}
    except (OSError, ValueError, TypeError, KeyError, OverflowError, RecursionError):
        raise PolicyError('Selected distribution route is not admitted') from None
