"""Use only an authored, harmless local payload to check curl pipe semantics."""
import shutil
import subprocess
import json
from pathlib import Path
import pytest
from test_release_policy import evaluator


@pytest.mark.skipif(shutil.which('curl') is None, reason='curl not installed')
def test_file_routing_matches_observed_shell_behavior(tmp_path):
    payload = tmp_path / 'owned-script.sh'
    payload.write_text("printf '%s' 'AITRUST_SYNTHETIC_PIPE_EXECUTED'\n")
    for routed_to_file in (False, True):
        # No remote URL, arbitrary input, or user-provided script is executed.
        command = ['curl', '--proto', '=file', '--noproxy', '*', '-fsS']
        if routed_to_file:
            command += ['-o', str(tmp_path / 'download.sh')]
        command += [payload.as_uri()]
        fetched = subprocess.run(command, check=True, capture_output=True, timeout=5)
        executed = subprocess.run(['sh'], input=fetched.stdout, check=True,
                                  capture_output=True, timeout=5)
        assert bool(executed.stdout) is (not routed_to_file)
        text = ' '.join(command) + ' | sh'
        assert bool(evaluator.signals(evaluator.Doc(text=text))['candidates']) is (not routed_to_file)


def test_changed_methods_have_new_versions():
    result = evaluator.signals(evaluator.Doc(text='curl https://example.test/i | sh'))
    assert result['calibration_id'] == 'uncalibrated-rules-v6'
    assert result['models'][0]['revision'] == 'context-v6'
    assert result['candidates'][0]['signals'][0]['id'] == 'sig.piped_installer.v4'


@pytest.mark.parametrize('row', [json.loads(line) for line in
    (Path(__file__).resolve().parents[1]/'eval/datasets/unsafe_code/routing_boundaries_v1.jsonl').read_text().splitlines()],
    ids=lambda row: row['case'])
def test_routing_through_executed_http_endpoint(row):
    from fastapi.testclient import TestClient
    with TestClient(evaluator.app) as client:
        response = client.post('/signals', json={'text':row['text']})
    assert response.status_code == 200
    record = response.json()
    assert bool(record['candidates']) == ('PS' in row['labels'])
    assert record['models'] == evaluator.MODELS
