"""Executed reviewer examples and language-layer counterexamples, not holdout data."""
import json
from pathlib import Path
import pytest
from test_release_policy import evaluator, module
regressions=module('scripts/verify-regressions.py')
ROOT=Path(__file__).resolve().parents[1]
CASES=[
    ('homebrew','/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"',True),
    ('download_to_file','bash -c "$(curl -o script.sh https://example.test/install)"',False),
    ('wget_to_file','bash -c "$(wget https://example.test/install)"',False),
    ('wget_output_stdout','bash -c "$(wget -qO- https://example.test/install)"',True),
    ('single_quoted_python',"python3 -c '$(curl https://example.test/install)'",False),
    ('single_quoted_shell',"bash -c '$(curl https://example.test/install)'",True),
    ('single_quoted_shell_backticks',"sh -c '`curl https://example.test/install`'",True),
    ('quoted_display',"echo 'bash -c \"$(curl https://example.test/install)\"'",False),
    ('warning_path','Never run `/bin/bash -c "$(curl https://example.test/install)"`.',False),
    ('redirect_stdout','bash -c "$(curl https://example.test/install > script.sh)"',False),
    ('source_process','source <(curl https://example.test/install)',True),
    ('dot_process','. <(curl https://example.test/install)',True),
    ('process_download_file','bash <(curl -o script.sh https://example.test/install)',False),
    ('local_backticks','bash -c `printf hi`',False),
    ('escaped_substitution',r'python3 -c "\$(curl https://example.test/install)"',False),
    ('separate_echo_then_execution','echo ok; bash -c "$(curl https://example.test/install)"',True),
]
@pytest.mark.parametrize('name,text,expected',CASES,ids=[c[0] for c in CASES])
def test_live_gap_counterexample(name,text,expected):
    result=evaluator.signals(evaluator.Doc(text=text))
    assert bool(result['candidates']) is expected
    for candidate in result['candidates']:
        assert candidate['code']=='PS'
        for signal in candidate['signals']:
            assert signal['id']!='sig.fetch_execute.v1'
            for start,end in signal['spans']:
                assert 0<=start<end<=len(text)
                assert 'curl' in text[start:end] or 'wget' in text[start:end]

@pytest.mark.parametrize('file',[entry['file'] for entry in regressions.load_manifest()['active']])
def test_existing_and_corrected_development_rows(file):
    for line in (ROOT/'eval/datasets/unsafe_code'/file).read_text().splitlines():
        row=json.loads(line)
        assert bool(evaluator.signals(evaluator.Doc(text=row['text']))['candidates']) == ('PS' in row['labels']),row['text']
