"""Selected offline PS review recipe; consistency, not independence or attestation."""
import hashlib
from importlib import metadata
import json
from pathlib import Path
import platform
import re
import shlex
import stat
import sys

SOURCE_FILES = (
    'services/evaluator/app.py', 'services/evaluator/requirements.lock',
    'protocol/normalization.py', 'protocol/unicode15-data.json',
    'scripts/prepare-ps-review.py', 'tools/blind_review_io.py',
    'tools/review_execution.py', 'protocol/evidence.py', 'eval/harness.py',
)
MAX_FILE = 32_000_000
MAX_TOTAL = 100_000_000
MAX_FILES = 1000


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=True, allow_nan=False).encode('ascii')


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


class Reader:
    def __init__(self):
        self.total = 0
        self.count = 0

    def hashed(self, file):
        # Installation roots are trusted host configuration. Individual code
        # entries must be ordinary files; don't follow arbitrary entry links.
        before = file.lstat()
        if (not stat.S_ISREG(before.st_mode) or before.st_size > MAX_FILE
                or self.count >= MAX_FILES or self.total + before.st_size > MAX_TOTAL):
            raise ValueError('Execution identity is unavailable or exceeds its bound')
        raw = file.read_bytes()
        after = file.lstat()
        identity = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
        if identity(before) != identity(after) or len(raw) != before.st_size:
            raise ValueError('Execution source changed during identity capture')
        self.total += len(raw)
        self.count += 1
        return hashlib.sha256(raw).hexdigest()


def execution_context(root):
    """Pin this CLI's declared Python evaluator route, never call the detector."""
    reader = Reader()
    sources = {name: reader.hashed(root / name) for name in SOURCE_FILES}
    standard = {'shlex.py': reader.hashed(Path(shlex.__file__))}
    re_root = Path(re.__file__).parent
    for file in sorted(re_root.glob('*.py')):
        standard['re/' + file.name] = reader.hashed(file)
    dependencies = {}
    for distribution, package in (('fastapi', 'fastapi'), ('pydantic', 'pydantic'),
            ('pydantic_core', 'pydantic_core'), ('starlette', 'starlette'),
            ('typing_extensions', 'typing_extensions.py'), ('typing_inspection', 'typing_inspection'),
            ('annotated_types', 'annotated_types'), ('annotated_doc', 'annotated_doc'),
            ('anyio', 'anyio'), ('idna', 'idna')):
        installed = metadata.distribution(distribution)
        base = Path(installed.locate_file(package)).resolve(strict=True)
        if not base.is_dir() and not base.is_file():
            raise ValueError('Execution dependency is unavailable')
        entries = {}
        visited = 0
        for file in (base.rglob('*') if base.is_dir() else [base]):
            visited += 1
            if visited > 4000:
                raise ValueError('Execution dependency inventory exceeds its bound')
            if file.is_symlink():
                raise ValueError('Linked execution dependency refused')
            if file.is_file() and file.suffix in ('.py', '.so', '.pyd', '.dll', '.dylib'):
                entries[file.relative_to(base).as_posix() if base.is_dir() else base.name] = reader.hashed(file)
        if not entries:
            raise ValueError('Empty execution dependency refused')
        dependencies[distribution] = {'version': installed.version,
            'code_sha256': digest(entries), 'code_files': len(entries)}
    return {'format': 'blind-ps-selected-execution/v1', 'sources': sources,
        'runtime': {'implementation': sys.implementation.name,
            'version': platform.python_version(), 'cache_tag': sys.implementation.cache_tag,
            'system': platform.system(), 'machine': platform.machine(),
            'executable_sha256': reader.hashed(Path(sys.executable).resolve(strict=True)),
            'standard_library': standard}, 'dependencies': dependencies,
        'route': 'offline-python-evaluator-after-frozen-nfc',
        'dependency_scope': 'declared_import_dependencies_not_whole_host_attestation',
        'remote_attestation': False, 'independence_verified': False}
