import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest
from test_release_policy import module

runner = module('scripts/verify-regressions.py')


def manifest_for(tmp_path, text, labels):
    dataset = tmp_path / 'sample.jsonl'
    dataset.write_text(json.dumps({'text': text, 'labels': labels}) + '\n')
    path = tmp_path / 'manifest.json'
    path.write_text(json.dumps({'version': 1, 'kind': 'development_regression',
        'independent_accuracy_evidence': False,
        'active': [{'file': dataset.name, 'sha256': hashlib.sha256(dataset.read_bytes()).hexdigest()}],
        'historical': []}))
    return path, dataset


def test_current_manifest_covers_all_active_files():
    report = runner.verify()
    assert report['regression_pass']
    assert len(report['datasets']) == 4
    assert report['case_count'] == 60
    assert [entry['file'] for entry in report['historical']] == ['counterexamples_v1.jsonl']
    assert report['independent_accuracy_evidence'] is False
    assert report['release_assessed'] is False


def test_changed_labels_require_manifest_update(tmp_path):
    manifest, dataset = manifest_for(tmp_path, 'Ordinary text.', [])
    dataset.write_text(json.dumps({'text': 'Ordinary text.', 'labels': ['PS']}) + '\n')
    with pytest.raises(ValueError, match='hash mismatch'):
        runner.verify(manifest)


def test_unregistered_dataset_fails(tmp_path):
    manifest, _ = manifest_for(tmp_path, 'Ordinary text.', [])
    (tmp_path / 'forgotten.jsonl').write_text('{}\n')
    with pytest.raises(ValueError, match='Every JSONL'):
        runner.verify(manifest)


def test_cli_fails_on_real_misclassification(tmp_path):
    manifest, _ = manifest_for(tmp_path, 'Ordinary text.', ['PS'])
    output = tmp_path / 'report.json'
    result = subprocess.run([sys.executable, str(Path(runner.__file__)), '--manifest',
                             str(manifest), '--output', str(output)], capture_output=True, text=True)
    assert result.returncode == 1
    report = json.loads(output.read_text())
    assert report['failures'] == [{'file': 'sample.jsonl', 'fp': 0, 'fn': 1}]
    assert report['regression_pass'] is False
