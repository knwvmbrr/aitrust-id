import math
import pytest
from protocol.repetition import inspect

def test_repeated_grams_report_exact_subject_spans():
    text='one two three one two three one two three'
    r=inspect(text)
    assert r['matched'] and r['findings'][0]['spans']==[[0,13],[14,27],[28,41]]
    assert r['repeated_token_coverage']==1 and r['tags']==[]

@pytest.mark.parametrize('text',['','one two three','One two three one two three ONE two three','alpha beta gamma delta epsilon zeta eta theta'])
def test_no_unjustified_repetition(text):
    assert not inspect(text)['matched']

def test_legitimate_refrain_is_observation_not_hallucination():
    r=inspect('Sing with me Sing with me Sing with me')
    assert r['matched'] and r['tags']==[] and 'intentional' in r['warning']

def test_normalization_and_unicode_scalar_spans():
    r=inspect('e\u0301 😀 é 😀 é 😀',n=2)
    assert r['findings'][0]['spans']==[[0,3],[4,7],[8,11]]

def test_sparse_repetition_requires_declared_coverage():
    text='x x x '+ ' '.join(str(i) for i in range(30))
    assert not inspect(text,n=1)['matched']
    assert inspect(text,n=1,coverage_threshold=.05)['matched']

@pytest.mark.parametrize('options',[{'n':True},{'n':0},{'n':9},{'minimum_occurrences':1},{'coverage_threshold':math.nan},{'coverage_threshold':math.inf},{'coverage_threshold':True}])
def test_invalid_configuration(options):
    with pytest.raises(ValueError):inspect('x x x',**options)

@pytest.mark.parametrize('text',[None,'x'*20001,'x\x00x'])
def test_bounds(text):
    with pytest.raises(ValueError):inspect(text)

def test_fragmented_output_refused_instead_of_truncated():
    with pytest.raises(ValueError):inspect(' '.join([str(i) for i in range(65)]*3),n=1)

def test_method_configuration_and_source_identity_are_bound():
    r=inspect('x x x',n=1)
    assert r['signal']=='sig.duplicate_loop.v1' and len(r['source_sha256'])==64
    assert r['configuration']=={'n':1,'minimum_occurrences':3,'coverage_threshold':.2}
