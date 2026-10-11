import copy,math
import pytest
from research.nli.pairs import validate,analyze,PairError

def request():return {'schema_version':1,'language':'en','text':'The door is closed. The door is open.','pairs':[{'id':'one','first':[0,19],'second':[20,37]}]}

def backend(a,b):return [-1.0,0.5,2.0],12

def test_actual_original_spans_and_scores():
 r=request();result=analyze(r,backend,{'research_only':True});assert result['pairs'][0]['top_model_labels']==['neutral'];assert abs(sum(result['pairs'][0]['normalized_model_scores'].values())-1)<1e-12;assert not result['truth_established'] and not result['tag_asserted'] and not result['release_approved'];assert result['span_units']=='original_unicode_codepoints'

@pytest.mark.parametrize('field,value',[('schema_version',True),('schema_version',2),('language','fr'),('language',None),('text',''),('text',' '*3),('text','a'*20001),('text',True),('text','a\x00b'),('text','a\ud800b'),('pairs',[]),('pairs',{}),('pairs',[{}])])
def test_invalid_request_never_reaches_model(field,value):
 r=request();r[field]=value
 def forbid(a,b):pytest.fail('Invalid input reached the model')
 with pytest.raises(PairError):analyze(r,forbid,{})

@pytest.mark.parametrize('value',[None,{},[0],['0',19],[False,19],[-1,19],[19,0],[0,100],[0,0],[0,19,20]])
def test_bad_spans_refuse(value):
 r=request();r['pairs'][0]['first']=value
 with pytest.raises(PairError):validate(r)

@pytest.mark.parametrize('value',['ONE','has space','a'*65,'α',None,False,'../x','', 'a\n'])
def test_invalid_ids(value):
 r=request();r['pairs'][0]['id']=value
 with pytest.raises(PairError):validate(r)

@pytest.mark.parametrize('kind',['extra-root','extra-pair','duplicate-id','overlap','too-many','oversized-span','blank-span'])
def test_structure_limits(kind):
 r=request()
 if kind=='extra-root':r['extra']=True
 if kind=='extra-pair':r['pairs'][0]['extra']=True
 if kind=='duplicate-id':r['pairs']*=2
 if kind=='overlap':r['pairs'][0]['second']=[1,19]
 if kind=='too-many':r['pairs']=[{**r['pairs'][0],'id':str(i)} for i in range(17)]
 if kind=='oversized-span':r['text']='a'*3000+'b';r['pairs'][0].update(first=[0,3000],second=[3000,3001])
 if kind=='blank-span':r['pairs'][0]['second']=[19,20]
 with pytest.raises(PairError):validate(r)

@pytest.mark.parametrize('logits',[[1,2],[1,2,3,4],[True,2,3],[None,2,3],['1',2,3],[float('nan'),2,3],[float('inf'),2,3],[float('-inf'),2,3],[1e7,2,3]])
def test_invalid_method_values_refuse(logits):
 with pytest.raises(PairError):analyze(request(),lambda a,b:(logits,12),{})

@pytest.mark.parametrize('tokens',[True,None,0,-1,513,12.0,'12'])
def test_token_contract(tokens):
 with pytest.raises(PairError):analyze(request(),lambda a,b:([1.,2.,3.],tokens),{})

@pytest.mark.parametrize('values',[[0.,0.,0.],[-1e6,0.,1e6],[3.,3.,1.]])
def test_extreme_and_tied_scores_remain_explicit(values):
 r=analyze(request(),lambda a,b:(values,12),{});row=r['pairs'][0];assert all(math.isfinite(x) and 0<=x<=1 for x in row['normalized_model_scores'].values());assert len(row['top_model_labels'])==values.count(max(values));assert not row['calibrated_probability']

def test_validate_every_pair_before_any_call():
 r=request();r['pairs'].append({'id':'two','first':[False,19],'second':[20,37]})
 def forbid(a,b):pytest.fail('Partial input reached model')
 with pytest.raises(PairError):analyze(r,forbid,{})

def test_unicode_offsets_are_not_normalized():
 r={'schema_version':1,'language':'en','text':'e\u0301 α 😀 abc','pairs':[{'id':'one','first':[0,2],'second':[5,6]}]};observed=[]
 def collect(a,b):observed.extend([a,b]);return [1.,2.,3.],6
 analyze(r,collect,{});assert observed==['e\u0301','😀']
