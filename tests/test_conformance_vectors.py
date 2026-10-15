"""Exercise the real interoperability runner and hostile implementation outputs."""
import json
from pathlib import Path
import subprocess
import sys
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools import conformance_vectors as module
from scripts.worker_process import run_worker


def adapter(tmp_path, program):
    file = tmp_path / 'adapter.py'
    file.write_text(program)
    return [sys.executable, str(file)]


def test_reference_both_profiles_execute_all_pinned_cases():
    result = module.run()
    assert result['pass'] and result['cases_run'] == result['cases_passed'] == 28
    assert {r['profile'] for r in result['checks']} == {'schema', 'extension'}
    assert all(result[k] is False for k in ('independent_accuracy_evidence',
        'outside_person_acceptance', 'certification', 'release_approved'))


def test_explicit_external_adapter_uses_json_stdin_and_profile(tmp_path):
    # A separately launched adapter demonstrates the interface; it is not an
    # independently written validator or an outside-person acceptance claim.
    command = adapter(tmp_path, 'import subprocess,sys\n'
        + 'raise SystemExit(subprocess.call([sys.executable,'
        + repr(str(ROOT/'scripts/check-assertion.py')) + ',*sys.argv[1:]]))\n')
    result = module.run(command, ('extension',))
    assert result['pass'] and result['cases_run'] == 14
    assert result['implementation'] == 'owner_selected_executable'
    assert result['outside_person_acceptance'] is False
    assert str(tmp_path) not in json.dumps(result)


def response(status='accepted', **changes):
    value = {'status': status, 'profile': 'schema', 'supported_version': '0.1.0',
        'offline': True, 'signature_verified': False,
        'independent_accuracy_verified': False, 'certification': False}
    value.update(changes)
    return json.dumps(value)


@pytest.mark.parametrize('raw,exit_code', [
    (response(), 0),  # An always-pass implementation must fail negative vectors.
    (response(), 7),
    (response(certification=True), 0),
    (response(offline=False), 0),
    (response()[:-1] + ',"status":"accepted"}', 0),
    ('{"private-canary":"must-not-appear"}', 0),
])
def test_bad_adapter_cannot_pass_or_echo_arbitrary_output(tmp_path, raw, exit_code):
    command = adapter(tmp_path, 'import sys\nprint(' + repr(raw) + ')\nraise SystemExit(' + str(exit_code) + ')\n')
    result = module.run(command, ('schema',))
    assert result['pass'] is False
    assert result['cases_passed'] < result['cases_run'] == 14
    assert 'private-canary' not in json.dumps(result)


def test_missing_executable_is_unavailable_without_echo(tmp_path):
    result = module.run([str(tmp_path/'private-canary')], ('schema',))
    assert not result['pass']
    assert all(r['failure'] == 'implementation_unavailable' for r in result['checks'])
    assert 'private-canary' not in json.dumps(result)


def test_output_flood_and_timeout_are_bounded(tmp_path):
    for program, expected in [('import sys\nsys.stdout.write("x"*100_000)',
                               'implementation_output_limit'),
                              ('import time\ntime.sleep(5)', 'implementation_timeout')]:
        command = adapter(tmp_path, program)
        def short(argv, **kwargs):
            return run_worker(argv, **{**kwargs, 'timeout': .05})
        result = module.run(command, ('schema',), supervisor=short)
        assert not result['pass']
        assert all(r['failure'] == expected for r in result['checks'])


def test_vector_drift_refused_before_implementation(tmp_path):
    target = tmp_path / module.VECTORS
    target.parent.mkdir(parents=True)
    target.write_bytes((ROOT/module.VECTORS).read_bytes().replace(b'0.1.0', b'0.9.0'))
    with pytest.raises(ValueError, match='identity changed'):
        module.load(tmp_path)


def test_cli_missing_vector_is_fixed_unavailable(tmp_path):
    # The actual CLI handles unsafe command input with a safe fixed response.
    result = subprocess.run([sys.executable, str(ROOT/'scripts/check-conformance-vectors.py'),
                             '--implementation'], capture_output=True, timeout=5)
    assert result.returncode == 2 and not result.stderr
    assert json.loads(result.stdout) == {'pass': False, 'state': 'Unavailable',
                                         'reason': 'vector_or_tooling_refused'}
