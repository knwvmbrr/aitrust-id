"""Exercise the pinned Uvicorn loader without a container or listening socket."""
import importlib.metadata
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
LOAD_ONLY = """
import uvicorn
def load_only(self):
    self.config.load()
    self.started = True
    print("factory-loaded")
uvicorn.Server.run = load_only
from uvicorn.main import main
main(args=["protocol.http_privacy:application", "--factory", "--no-access-log"], standalone_mode=False)
"""


def invoke(root, program):
    return subprocess.run([sys.executable, '-B', '-c', program], cwd=root,
        env={**os.environ, 'PYTHONPATH': '', 'PYTHONDONTWRITEBYTECODE': '1'},
        capture_output=True, timeout=10)


def test_nontraversable_directory_reproduces_hosted_cli_failure_and_corrected_import(tmp_path):
    if os.geteuid() == 0:
        pytest.skip('The permission refusal control requires the nonroot test user.')
    assert importlib.metadata.version('uvicorn') == '0.34.0'
    directory = tmp_path/'protocol'
    directory.mkdir()
    module = directory/'http_privacy.py'
    original = (ROOT/'protocol/http_privacy.py').read_bytes()
    module.write_bytes(original)
    module.chmod(0o444)
    (tmp_path/'app.py').write_text('from fastapi import FastAPI\napp = FastAPI()\n')
    try:
        directory.chmod(0o444)
        refused = invoke(tmp_path, LOAD_ONLY)
        assert refused.returncode == 1 and not refused.stdout
        assert b'Could not import module "protocol.http_privacy".' in refused.stderr
        directory.chmod(0o555)
        loaded = invoke(tmp_path, LOAD_ONLY)
        assert loaded.returncode == 0 and loaded.stdout == b'factory-loaded\n' and not loaded.stderr
        assert module.read_bytes() == original and module.stat().st_mode & 0o777 == 0o444
        assert not (directory/'__init__.py').exists()
    finally:
        directory.chmod(0o755)


@pytest.mark.parametrize('service', ['gateway', 'anonymizer', 'evaluator'])
def test_selected_image_resolves_exact_module_as_runtime_user_without_loading_model(tmp_path, service):
    dockerfile = (ROOT/'services'/service/'Dockerfile').read_text().splitlines()
    copy = next(line for line in dockerfile if line.startswith('COPY --chmod=0444 protocol/http_privacy.py'))
    chmod = 'RUN chmod 0555 /app/protocol'
    observation = next(line for line in dockerfile if line.startswith('RUN python -c ') and 'stat.S_IMODE' in line)
    assertion = next(line for line in dockerfile if line.startswith('RUN python -c ') and 'find_spec' in line)
    assert dockerfile.index(copy) < dockerfile.index(observation) < dockerfile.index(chmod)
    assert dockerfile.index(chmod) < dockerfile.index('USER 10001:10001') < dockerfile.index(assertion)
    cmd = json.loads(next(line.removeprefix('CMD ') for line in dockerfile if line.startswith('CMD ')))
    assert cmd == ['uvicorn', 'protocol.http_privacy:application', '--factory',
                   '--host', '0.0.0.0', '--port', '8000', '--no-access-log']
    package = tmp_path/'protocol'
    package.mkdir(mode=0o755)
    for source in shlex.split(copy)[2:-1]:
        target = package/Path(source).name
        target.write_bytes((ROOT/source).read_bytes())
        target.chmod(0o444)
    try:
        package.chmod(0o444)
        observe = shlex.split(observation.removeprefix('RUN '))[2].replace('/app/protocol', str(package))
        observed = invoke(tmp_path, observe)
        assert observed.returncode == 0 and not observed.stderr
        assert observed.stdout == b'protocol directory mode before correction: 0444\n'
        package.chmod(0o555)
        # No app.py exists. Resolving the factory must not import service/model code.
        program = shlex.split(assertion.removeprefix('RUN '))[2].replace(
            '/app/protocol/http_privacy.py', str(package/'http_privacy.py'))
        passed = invoke(tmp_path, program)
        assert passed.returncode == 0 and not passed.stdout and not passed.stderr
        assert all(target.stat().st_mode & 0o777 == 0o444 for target in package.iterdir())
        package.chmod(0o755)
        (package/'http_privacy.py').unlink()
        package.chmod(0o555)
        refused = invoke(tmp_path, program)
        assert refused.returncode != 0
    finally:
        package.chmod(0o755)
