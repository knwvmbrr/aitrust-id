import copy
import pytest
from protocol import corpus
from tools.language_observations import digest
from tools import choice_framing as module

TEXT='Either agree or oppose.'
def packet(text=TEXT,source='You can remain undecided.',words=('agree','oppose')):
    row={'id':'reference','text':source,'sha256':corpus.sha(source.encode())};content={'format':corpus.VERSION,'documents':[row]};record={**content,'manifest_sha256':corpus.sha(corpus.encoded(content))}
    first=[text.index(words[0]),text.index(words[0])+len(words[0])];second=[text.index(words[1]),text.index(words[1])+len(words[1])]
    context={'format':'choice-frame-context/v1','language':'en','subject_sha256':digest(text),'manifest_sha256':record['manifest_sha256'],'frames':[{'span':[0,len(text)],'choices':[first,second],'additional_reference':{'document_id':'reference','document_sha256':row['sha256'],'source_span':[0,len(source)]}}]}
    return record,context

def test_bound_observation_not_false_dilemma_verdict():
    record,context=packet();result=module.observe(TEXT,record,context);row=result['observations'][0]
    assert row['binary_marker_spans']==[[0,6],[13,15]]
    assert row['choice_spans']==[[7,12],[16,22]]
    assert not row['additional_option_verified'] and not row['manipulation_established'] and not row['exhaustiveness_established']
    assert not result['tag_asserted'] and not result['truth_established'] and 'You can' not in str(result)

@pytest.mark.parametrize('field',['format','language','subject_sha256','manifest_sha256','extra'])
def test_unbound_context_refuses(field):
    record,context=packet();context[field]='changed'
    with pytest.raises(module.FrameError):module.observe(TEXT,record,context)

@pytest.mark.parametrize('choices',[[[7,12],[10,22]],[[True,12],[16,22]],[[7.,12],[16,22]],[[7,12],[16,999]],[[7,12]],[],None])
def test_choices_must_be_two_exact_ordered_nonoverlapping_spans(choices):
    record,context=packet();context['frames'][0]['choices']=choices
    with pytest.raises(module.FrameError):module.observe(TEXT,record,context)

@pytest.mark.parametrize('field',['document_id','document_sha256','source_span','extra'])
def test_wrong_additional_reference_refuses(field):
    record,context=packet();context['frames'][0]['additional_reference'][field]='changed'
    with pytest.raises(module.FrameError):module.observe(TEXT,record,context)

@pytest.mark.parametrize('text',['I could agree and oppose.','I agree or oppose.','Either agree rather than oppose.'])
def test_unmatched_context_is_not_manipulation(text):
    record,context=packet(text);result=module.observe(text,record,context)
    assert result['state']=='NO_SUPPORTED_PATTERN' and not result['tag_asserted']

@pytest.mark.parametrize('text',['A quoted example: "Either agree or oppose."','Emergency choices: either agree or oppose.'])
def test_quote_and_legitimate_choices_do_not_get_intent_verdict(text):
    record,context=packet(text);result=module.observe(text,record,context)
    assert result['state']=='OBSERVATIONS' and not result['observations'][0]['manipulation_established']
    assert not result['observations'][0]['quoted_or_recommended_resolved']

@pytest.mark.parametrize('source',['agree','oppose'])
def test_repeated_choice_cannot_be_called_an_additional_passage(source):
    record,context=packet(source=source)
    with pytest.raises(module.FrameError):module.observe(TEXT,record,context)

@pytest.mark.parametrize('field',['text','sha256'])
def test_altered_corpus_is_unavailable(field):
    record,context=packet();record['documents'][0][field]='changed'
    with pytest.raises(corpus.CorpusError):module.observe(TEXT,record,context)

@pytest.mark.parametrize('text,source,choices',[
    ('Either evacuate or shelter.','Ask emergency services for situation-specific advice.',('evacuate','shelter')),
    ('Either tea or coffee.','The menu also lists water.',('tea','coffee')),
    ('A lesson quotes: "Either agree or oppose."','The lesson also discusses staying neutral.',('agree','oppose')),
])
def test_ordinary_and_safety_choices_are_never_an_accusation(text,source,choices):
    record,context=packet(text,source,choices)
    result=module.observe(text,record,context)
    assert result['state']=='OBSERVATIONS'
    assert not result['tag_asserted'] and not result['release_approved']
    row=result['observations'][0]
    assert not row['manipulation_established'] and not row['additional_option_verified']
    assert not row['quoted_or_recommended_resolved']


def test_all_context_validates_before_any_output():
    record,context=packet();context['frames'].append(copy.deepcopy(context['frames'][0]))
    with pytest.raises(module.FrameError):module.observe(TEXT,record,context)


def test_reference_unicode_spans_bind_normalized_text():
    from protocol.normalization import normalize_nfc
    source='The menu also lists cafe\u0301 options.'
    record,context=packet('Either tea or coffee.',source,('tea','coffee'))
    normalized=normalize_nfc(source)
    context['frames'][0]['additional_reference']['source_span']=[0,len(normalized)]
    result=module.observe('Either tea or coffee.',record,context)
    row=result['observations'][0]['additional_reference']
    assert row['document_sha256']==corpus.sha(source.encode())
    assert row['normalized_source_sha256']==corpus.sha(normalized.encode())
    assert row['source_span']==[0,len(normalized)]
