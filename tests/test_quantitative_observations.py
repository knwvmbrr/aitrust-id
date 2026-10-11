"""Independent literal observation, span and real CLI privacy controls."""
import json
import os
from pathlib import Path
import stat
import subprocess
import sys

import pytest
from protocol.corpus import CorpusError
from protocol.normalization import normalize_nfc
from tools import quantitative_observations as tool
ROOT=Path(__file__).resolve().parents[1]


def cli(text,extra=()):
    return subprocess.run([sys.executable,str(ROOT/'scripts/quantitative-observations.py'),
        '--language','en',*extra],input=text,capture_output=True,timeout=5)


@pytest.mark.parametrize('text,expected',[
    ('There are 12 items.',1),('There are -12 items and +25 items.',2),
    ('It costs 1,250.50 dollars.',1),('A rate of 12.5% was stated.',1),
    ('The stated date is 2026-10-11.',1),('The date-shaped token is 2026-99-99.',1),
    ('There are 12, 25, and 37 entries.',3),('The number is 12,34.',0),
    ('ID123 abc-123 #123 abc123x 123abc é123 表123.',0),
    ('An IPv4-shaped string is 192.0.2.1.',0),('Version v1.2.3 applies.',0),
    ('Written-out twelve and May tenth are outside this method.',0),
    ('https://example.invalid/2026/page?item=12 [45]',0),
])
def test_complete_literal_tokens_without_identifier_or_marker_fragments(text,expected):
    brief,detail=tool.observe(text,'en')
    assert brief['supported_detail_count']==expected
    assert brief['without_same_unit_marker']==expected
    assert len(detail['details'])==expected and brief['tags']==[]
    assert brief['truth_established'] is False and brief['calendar_validity_checked'] is False


def test_source_marker_is_local_not_a_resolution_or_truth_claim():
    brief,detail=tool.observe('The report has 12 items [1]. Another has 25 items.','en')
    assert brief['with_same_unit_marker']==1 and brief['without_same_unit_marker']==1
    assert detail['details'][0]['source_marker_spans'] and not detail['details'][1]['source_marker_spans']
    assert detail['details'][0]['id'] is None and detail['details'][0]['signal_candidate'] is False
    assert detail['details'][1]['id']=='sig.unsourced_specificity.v1' and detail['details'][1]['signal_candidate'] is True
    assert brief['source_lookup_performed'] is False and brief['source_support_established'] is False


def test_unicode_normalized_spans_refer_to_supported_details_only():
    original='Cafe\u0301 reports 12.5% and 2026-10-11.'
    brief,detail=tool.observe(original,'en');normalized=normalize_nfc(original)
    assert [normalized[d['span'][0]:d['span'][1]] for d in detail['details']]==['12.5%','2026-10-11']
    assert detail['subject_text_included'] is False
    assert 'Café' not in json.dumps(detail) and 'Cafe' not in json.dumps(brief)


@pytest.mark.parametrize('text,language',[('', 'en'),('  ','en'),('PRIVATE_CANARY\x00 12','en'),('\ud800','en'),('x'*8001,'en'),('There are 12.','fr')])
def test_unsupported_subjects_fail_without_verdict(text,language):
    with pytest.raises(CorpusError):tool.observe(text,language)


def test_limits_do_not_silently_clip_details_or_parse_huge_integers():
    with pytest.raises(CorpusError):tool.observe(' '.join('12' for _ in range(257)),'en')
    brief,detail=tool.observe('9'*100,'en')
    assert brief['skipped_detail_count']==1 and not detail['details']


def test_default_actual_cli_outputs_only_brief_counts_and_makes_no_file(tmp_path):
    private=tmp_path/'report.json';result=cli(b'PRIVATE_QUANTITATIVE_CANARY reports 12 items.')
    assert result.returncode==0 and not result.stderr and not private.exists()
    record=json.loads(result.stdout)
    assert 'subject_sha256' not in record and 'details' not in record
    assert b'PRIVATE_QUANTITATIVE_CANARY' not in result.stdout


@pytest.mark.parametrize('raw',[b'\xff PRIVATE_QUANTITATIVE_CANARY',b'PRIVATE_QUANTITATIVE_CANARY\0',b'x'*32001])
def test_actual_cli_bad_input_has_fixed_unavailable_output(raw):
    result=cli(raw);assert result.returncode==2 and not result.stderr
    assert json.loads(result.stdout)['state']=='UNAVAILABLE'
    assert b'PRIVATE_QUANTITATIVE_CANARY' not in result.stdout


def test_private_report_requires_explicit_new_private_destination(tmp_path):
    directory=tmp_path.resolve()/'private';directory.mkdir(mode=0o700);report=directory/'details.json'
    result=cli(b'There are 12 items.',('--private-report',str(report)))
    assert result.returncode==0 and json.loads(result.stdout)['private_report_saved']
    assert stat.S_IMODE(report.stat().st_mode)==0o600
    original=report.read_bytes();retry=cli(b'There are 25 items.',('--private-report',str(report)))
    assert retry.returncode==2 and report.read_bytes()==original


def test_private_report_rejects_public_directory_symlink_and_checkout(tmp_path):
    directory=tmp_path.resolve()/'private';directory.mkdir(mode=0o700)
    target=directory/'existing';target.write_bytes(b'keep');link=directory/'link';link.symlink_to(target)
    with pytest.raises(CorpusError):tool.save_private({},link)
    assert target.read_bytes()==b'keep'
    directory.chmod(0o755)
    with pytest.raises(CorpusError):tool.save_private({},directory/'new')
    with pytest.raises(CorpusError):tool.save_private({},ROOT/'output/never-private.json')


def test_non_ascii_boundaries_are_explicitly_unsupported_not_host_unicode_dependent():
    brief,detail=tool.observe('é123 表456 78́ 90 ','en')
    assert not detail['details'] and brief['skipped_detail_count']==4


def test_actual_verifier_runs_all_supported_and_failure_routes():
    result=subprocess.run([sys.executable,str(ROOT/'scripts/verify-quantitative-observations.py')],capture_output=True,timeout=10)
    assert result.returncode==0 and not result.stderr
    record=json.loads(result.stdout)
    assert record['pass'] and record['case_count']==11 and record['source_unchanged_during_execution']
    assert len(record['sources'])==8 and record['tag_assertions']==0
    assert record['independent_accuracy_evidence'] is False
