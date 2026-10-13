import copy
import importlib.util
import json
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('setup_evidence', ROOT / 'scripts/verify-local-setup-evidence.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def receipt():
    return json.loads((ROOT / m.RECEIPT).read_text())


def test_current_actual_setup_receipt_stays_separate_from_human_accuracy_acceptance():
    result = m.verify()
    assert result['pass'] and result['human_acceptance_requirement'] == 'F-142'
    assert result['independent_accuracy_evidence'] is False and result['collection_enabled'] is False


@pytest.mark.parametrize('field,value', [('actual_clean_clone', False), ('actual_one_command_start', False),
                                      ('source_unchanged', False), ('case_count', 9), ('case_count', True),
                                      ('cases', []), ('physical_phone_tested', True),
                                      ('human_acceptance_complete', True), ('independent_accuracy_evidence', True),
                                      ('collection_enabled', True), ('source_commit', '--all')])
def test_incomplete_or_overclaiming_receipt_refused(field, value):
    row = receipt()
    row[field] = value
    with pytest.raises(ValueError):
        m.verify(row)


def test_source_change_requires_actual_setup_to_be_repeated():
    row = receipt()
    row['sources']['scripts/setup-local.py'] = 'f' * 64
    with pytest.raises(ValueError, match='source changed'):
        m.verify(row)


@pytest.mark.parametrize('name', ['services/gateway/Dockerfile', 'services/anonymizer/requirements.lock',
                                'services/evaluator/healthcheck.py', 'protocol/http_privacy.py',
                                'services/anonymizer/model_identity.py', 'services/anonymizer/replay_metadata.py',
                                'protocol/unicode15-data.json', '.dockerignore', 'scripts/check-assertion.py'])
def test_each_copied_or_bootstrap_input_is_bound(name):
    row = receipt()
    assert name in row['sources']
    row['sources'][name] = 'f' * 64
    with pytest.raises(ValueError, match='source changed'):
        m.verify(row)


def test_downloaded_source_without_git_history_still_verifies(tmp_path):
    import shutil
    row = receipt()
    for name in row['sources']:
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, target)
    assert not (tmp_path / '.git').exists()
    assert m.verify(row, root=tmp_path)['git_history_required'] is False


def test_an_extra_copy_requires_new_execution_and_notices(tmp_path):
    import shutil
    row = receipt()
    for name in row['sources']:
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, target)
    (tmp_path / 'new-input.py').write_text('changed build graph')
    with (tmp_path / 'services/gateway/Dockerfile').open('a') as stream:
        stream.write('\nCOPY new-input.py /app/new-input.py\n')
    with pytest.raises(ValueError, match='source changed'):
        m.verify(row, root=tmp_path)


@pytest.mark.parametrize('field,value', [('uid', 0), ('read_only', False), ('pids_limit', 0),
                                      ('memory_mib', 0), ('capabilities_dropped', False),
                                      ('no_new_privileges', False)])
def test_effective_runtime_weakening_reopens_acceptance(field, value):
    row = receipt()
    row['services']['gateway'][field] = value
    with pytest.raises(ValueError, match='safety/identity'):
        m.verify(row)
