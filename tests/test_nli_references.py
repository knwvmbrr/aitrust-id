"""Reference selection and classifier relationships do not establish facts."""
import copy,math
import pytest
from protocol import corpus
from research.nli.references import observe
from research.nli.pairs import PairError

@pytest.fixture
def record(tmp_path):
 tmp_path.chmod(0o700);p=tmp_path/'manual.txt';p.write_text('The room is empty.\nThe door was closed yesterday.\n');target=tmp_path/'corpus.json';corpus.create([('manual',p)],target);return corpus.load(target)

def backend(a,b):return [4.,-2.,-1.],15

def test_distinct_reference_and_claim_bindings_and_direction(record):
 seen=[]
 def collect(a,b):seen.append((a,b));return backend(a,b)
 result=observe(record,'There are people in the room.',collect,{},.4)
 assert seen==[('The room is empty.','There are people in the room.')]
 row=result['observations'][0];assert row['proposed_signal']=='sig.corpus_contradiction.v1'
 assert row['reference']['document_sha256']==record['documents'][0]['sha256']
 assert row['direction']=='reference_is_premise_claim_is_hypothesis'
 assert row['top_model_labels']==['contradiction']
 assert result['model_evaluation_obtained'] and result['retrieval_evaluation_obtained']
 assert result['reference_freshness']=='unestablished'
 assert not result['truth_established'] and not result['independent_corroboration'] and not result['tag_asserted'] and not result['release_approved']
 assert 'The room is empty.' not in str(result)

@pytest.mark.parametrize('threshold',[.5,.75])
def test_observed_paraphrase_selection_miss_is_preserved(record,threshold):
 def forbid(a,b):pytest.fail('Unselected passage reached model')
 result=observe(record,'There are people in the room.',forbid,{},threshold)
 assert result['state']=='no_similar_passage' and not result['model_evaluation_obtained']
 assert not result['absence_proves_false'] and result['observations']==[]

@pytest.mark.parametrize('field',['sha256','text','id'])
def test_corrupted_source_cannot_reach_model(record,field):
 r=copy.deepcopy(record);r['documents'][0][field]='changed'
 def forbid(a,b):pytest.fail('Corrupted reference reached model')
 with pytest.raises(corpus.CorpusError):observe(r,'The room is empty.',forbid,{})

@pytest.mark.parametrize('value',[[],None,True,{},[1.,2.],[True,2.,3.],[float('nan'),1.,2.],[float('inf'),1.,2.],[1e7,1.,2.]])
def test_invalid_method_output_has_no_usable_result(record,value):
 with pytest.raises(PairError):observe(record,'The room is empty.',lambda a,b:(value,10),{})

@pytest.mark.parametrize('value',[True,0,513,12.,None])
def test_token_failure_refuses(record,value):
 with pytest.raises(PairError):observe(record,'The room is empty.',lambda a,b:([1.,2.,3.],value),{})

@pytest.mark.parametrize('subject',['','é','\ud800','\x00','a '*513])
def test_unsupported_query_refuses_before_model(record,subject):
 def forbid(a,b):pytest.fail('Unsupported query reached model')
 with pytest.raises(corpus.CorpusError):observe(record,subject,forbid,{})

def test_no_reference_is_not_fabrication(record):
 result=observe(record,'Orange bicycle highway.',backend,{})
 assert not result['truth_established'] and not result['absence_proves_false'] and not result['model_evaluation_obtained']

def test_all_selected_passages_validate_before_first_model(record):
 r=copy.deepcopy(record);r['documents'][0]['text']='word\n'+'word '*500+'\n';r['documents'][0]['sha256']=corpus.sha(r['documents'][0]['text'].encode());r['manifest_sha256']=corpus.sha(corpus.encoded({'format':r['format'],'documents':r['documents']}))
 def forbid(a,b):pytest.fail('Partial unsupported reference job reached model')
 with pytest.raises(PairError):observe(r,'word',forbid,{},.75)
