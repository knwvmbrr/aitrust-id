"""Nominal agreement controls: worked references, missingness, invariants and privacy."""
import copy,importlib.util,json,sys
from fractions import Fraction
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
spec=importlib.util.spec_from_file_location('reviewer_agreement',ROOT/'tools/reviewer_agreement.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

def matrix(rows,categories=None):
    values=categories or sorted({x for row in rows for x in row if x is not None})
    names=[f'Observer{i}' for i in range(len(rows))]
    return {'schema_version':1,'kind':'nominal_agreement_ratings','target_tag':'MT','reviewers':names,
        'categories':values,'units':[{'id':f'Item{i}','ratings':dict(zip(names,values))} for i,values in enumerate(zip(*rows))]}

def binary():return matrix([list('abab'),list('abab')])

def test_primary_binary_reference():
    # The separately written exact reference below encodes the paper's numeric example.
    d=matrix([list('0100000010'),list('1110010000')],['0','1'])
    d['categories']=['Zero','One']
    for u in d['units']:
        u['ratings']={k:'One' if v=='1' else 'Zero' for k,v in u['ratings'].items()}
    r=m.nominal_agreement(d);assert r['alpha']['value']==pytest.approx(2/21);assert r['alpha']['exact_fraction']=='2/21';assert r['pairable_rating_count']==20

def test_primary_five_category_reference():
    d=matrix([list('aabbdcccedda'),list('babbbccceddd')]);r=m.nominal_agreement(d)
    assert r['alpha']['exact_fraction']=='155/224';assert r['alpha']['value']==pytest.approx(.6919642857142857)

def test_primary_missingness_reference():
    rows=[list('123321412')+[None,None,None],list('1233224125')+[None,'3'],[None]+list('3332342251')+[None],list('12332441251')+[None]]
    d=matrix(rows,['1','2','3','4','5']);aliases={'1':'One','2':'Two','3':'Three','4':'Four','5':'Five'};d['categories']=list(aliases.values())
    for u in d['units']:u['ratings']={k:None if v is None else aliases[v] for k,v in u['ratings'].items()}
    r=m.nominal_agreement(d);assert r['pairable_rating_count']==40;assert r['supplied_rating_count']==41;assert r['unpaired_unit_count']==1;assert r['alpha']['value']==pytest.approx(.7434210526315789)

def test_constant_labels_are_undefined_not_perfect():
    r=m.nominal_agreement(matrix([list('aaaa'),list('aaaa')],['a','b']))
    assert r['state']=='UNAVAILABLE' and r['alpha'] is None and r['reason']=='no_category_variation' and not r['candidate_met']

def test_missing_only_one_reviewer_cannot_create_agreement():
    r=m.nominal_agreement(matrix([list('ab'),[None,None]],['a','b']))
    assert r['state']=='UNAVAILABLE' and r['reason']=='no_pairable_ratings' and r['pairable_rating_count']==0

def test_negative_alpha_is_preserved():
    r=m.nominal_agreement(matrix([list('ab'),list('ba')]));assert r['alpha']['exact_fraction']=='-1/2'

def test_perfect_agreement_with_variation_is_one_but_not_release():
    r=m.nominal_agreement(binary());assert r['alpha']['value']==1 and r['candidate_met']
    for key in ['candidate_is_adopted','release_approved','accuracy_evidence','independence_verified','collection_performed','private_input_identifiers_exported']:assert r[key] is False
    assert r['confidence_interval'] is None

def test_unpaired_value_has_no_effect_on_expected_disagreement():
    d=binary();before=m.nominal_agreement(d);d['units'].append({'id':'Solo','ratings':{'Observer0':'a','Observer1':None}});after=m.nominal_agreement(d)
    for key in ['alpha','observed_disagreement','expected_disagreement','category_counts','pairable_rating_count']:assert before[key]==after[key]
    assert after['unpaired_unit_count']==1 and after['supplied_rating_count']==before['supplied_rating_count']+1

def test_observer_and_unit_order_do_not_change_coefficient():
    d=matrix([list('aabba'),list('abbba'),list('abaaa')]);r=m.nominal_agreement(d);d['units'].reverse();d['reviewers'].reverse()
    for u in d['units']:u['ratings']=dict(reversed(list(u['ratings'].items())))
    assert m.nominal_agreement(d)==r

def test_nominal_category_rename_does_not_change_agreement_or_export_names():
    d=binary();r=m.nominal_agreement(d);aliases={'a':'PrivateCategoryOne','b':'PrivateCategoryTwo'};d['categories']=list(aliases.values())
    for u in d['units']:u['ratings']={k:aliases[v] for k,v in u['ratings'].items()}
    result=m.nominal_agreement(d);assert result==r;assert 'PrivateCategory' not in json.dumps(result)

def test_reviewer_and_item_aliases_are_never_exported():
    d=binary();d['reviewers']=['PrivateReviewerOne','PrivateReviewerTwo']
    for i,u in enumerate(d['units']):u['id']='PrivateUnit'+str(i);u['ratings']=dict(zip(d['reviewers'],u['ratings'].values()))
    assert 'Private' not in json.dumps(m.nominal_agreement(d))

def test_variable_rater_count_uses_pairable_values_not_unweighted_pairs():
    d=matrix([list('aa'),list('ab'),['a',None]],['a','b']);r=m.nominal_agreement(d)
    assert r['pairable_rating_count']==5;assert r['observed_disagreement']['exact_fraction']=='2/5';assert r['expected_disagreement']['exact_fraction']=='2/5';assert r['alpha']['value']==0

BAD=[lambda d:d.update(schema_version=True),lambda d:d.update(schema_version=2),lambda d:d.update(kind='preview'),lambda d:d.update(target_tag='PS'),
 lambda d:d.update(prompt='private'),lambda d:d.update(reviewers=['Only']),lambda d:d.update(reviewers=['A','A']),lambda d:d.update(reviewers='A,B'),
 lambda d:d.update(categories=['a']),lambda d:d.update(categories=['a','a']),lambda d:d.update(categories=[True,'b']),lambda d:d.update(categories=['a','b','c']*6),
 lambda d:d.update(units=[]),lambda d:d.update(units='secret'),lambda d:d['units'].append(copy.deepcopy(d['units'][0])),
 lambda d:d['units'][0].update(text='private'),lambda d:d['units'][0].update(id='bad@id'),lambda d:d['units'][0].update(id=None),
 lambda d:d['units'][0].update(ratings=[]),lambda d:d['units'][0]['ratings'].update(Observer0='unknown'),lambda d:d['units'][0]['ratings'].update(Observer0=True),
 lambda d:d['units'][0]['ratings'].update(Observer0=1),lambda d:d['units'][0]['ratings'].update(Observer2='a'),lambda d:d['units'][0]['ratings'].pop('Observer1'),
 lambda d:d.update(reviewers=['Observer0','Observer1']+['A'+str(i) for i in range(31)]),lambda d:d.update(units=[{'id':'I'+str(i),'ratings':{'Observer0':'a','Observer1':'b'}} for i in range(2049)])]
@pytest.mark.parametrize('change',BAD)
def test_invalid_matrix_refuses_without_input_reflection(change):
    d=binary();change(d)
    with pytest.raises(ValueError,match='^Invalid agreement matrix$'):m.nominal_agreement(d)
