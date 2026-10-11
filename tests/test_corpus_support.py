"""Actual local retrieval with misleading resemblance kept separate from truth."""
import copy
import json
import math
from pathlib import Path
import subprocess
import sys
import pytest
from protocol import corpus as c, corpus_support as s
ROOT=Path(__file__).resolve().parents[1]

@pytest.fixture
def attached(tmp_path):
    tmp_path.chmod(0o700);source=tmp_path/'source.txt'
    source.write_text('  Water is safe.\nWater is not safe.\nThe fee is 25 dollars.\nCafe\n')
    output=tmp_path/'corpus.json';c.create([('handbook',source)],output)
    return tmp_path,c.load(output),output

def test_mathematics_and_exact_spans(attached):
    _,r,_=attached;subject='  Water is safe.\nThe fee is 25 dollars.\n'
    out=s.observe(r,subject,1)
    assert out['state']=='SIMILAR_PASSAGE';assert out['truth_established'] is False
    assert out['tags']==[] and out['reference_freshness']=='unestablished'
    assert out['findings'][0]['id']=='sig.corpus_support.v1'
    for finding in out['findings']:
        a,b=finding['spans'][0];x,y=finding['reference']['source_span']
        assert subject[a:b]==r['documents'][0]['text'][x:y]
        assert finding['score']==1
    assert math.isclose(s.cosine(s.vector('a a b'),s.vector('a b b')), .8)

@pytest.mark.parametrize('claim',['Water is not safe.','The fee is 26 dollars.','"Water is safe" is fictional.'])
def test_misleading_similarity_never_becomes_truth(attached,claim):
    out=s.observe(attached[1],claim,.5)
    assert out['findings'] and out['tags']==[]
    assert not out['truth_established'] and not out['entailment_checked'] and not out['score_is_probability']

def test_no_match_is_not_false_and_order_deterministic(attached):
    out=s.observe(attached[1],'Orange bicycle highway.',.75)
    assert out['state']=='NO_SIMILAR_PASSAGE' and not out['truth_established']
    assert s.observe(attached[1],'Water is safe.')==s.observe(attached[1],'Water is safe.')

@pytest.mark.parametrize('subject',['','\x00','\ud800','é','word '*501,'a\n'*33,'!'*5])
def test_unsupported_subject_refused(attached,subject):
    with pytest.raises(c.CorpusError):s.observe(attached[1],subject)

@pytest.mark.parametrize('threshold',[True,0,1.01,float('nan'),float('inf'),None])
def test_invalid_threshold_refused(attached,threshold):
    with pytest.raises(c.CorpusError):s.observe(attached[1],'Water',threshold)

@pytest.mark.parametrize('maximum',[True,0,11,1.5])
def test_invalid_result_limit_refused(attached,maximum):
    with pytest.raises(c.CorpusError):s.observe(attached[1],'Water',maximum=maximum)

def test_unicode_reference_skipped_and_no_usable_reference_refused(attached):
    r=copy.deepcopy(attached[1]);r['documents'][0]['text']='é\nWater is safe.'
    out=s.observe(r,'Water is safe.');assert out['unsupported_reference_passages']==1
    r['documents'][0]['text']='é'
    with pytest.raises(c.CorpusError):s.observe(r,'Water')

def test_reference_count_and_output_limits(attached):
    r=copy.deepcopy(attached[1]);r['documents'][0]['text']='word\n'*100
    assert len(s.observe(r,'word\n'*32,maximum=3)['findings'])==3
    r['documents'][0]['text']='word\n'*4097
    with pytest.raises(c.CorpusError):s.observe(r,'word')

def test_actual_cli_private_query_and_corrupt_corpus(attached):
    folder,_,file=attached;command=[sys.executable,str(ROOT/'scripts/corpus-support.py'),'--corpus',str(file)]
    good=subprocess.run(command,input='Water is safe.',text=True,capture_output=True,cwd=ROOT)
    assert good.returncode==0;out=json.loads(good.stdout);assert out['findings'] and 'Water' not in good.stdout
    file.write_text(file.read_text().replace('Water','Altered'))
    bad=subprocess.run(command,input='PRIVATE_QUERY_CANARY',text=True,capture_output=True,cwd=ROOT)
    assert bad.returncode==2 and json.loads(bad.stdout)['state']=='UNAVAILABLE'
    assert 'PRIVATE_QUERY_CANARY' not in bad.stdout+bad.stderr
