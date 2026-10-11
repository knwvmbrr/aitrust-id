"""Distinct owner-corpus/claim model observations; never a fact or tag verdict."""
import hashlib,math
from protocol import corpus,corpus_support
from protocol.normalization import normalize_nfc,NORMALIZATION_ID
from .pairs import require,LABELS,validate

def select(record,subject,threshold=.75,maximum=5):
    require(type(maximum) is int and 1<=maximum<=5)
    # Revalidate the envelope before lexical selection or model execution.
    record=corpus.parse(corpus.encoded(record))
    retrieval=corpus_support.observe(record,subject,threshold,maximum)
    normalized=normalize_nfc(subject)
    references={d['id']:d for d in record['documents']}
    selected=[]
    for candidate in retrieval['findings']:
        a,b=candidate['spans'][0];ref=candidate['reference'];doc=references[ref['document_id']]
        source=normalize_nfc(doc['text']);left,right=ref['source_span']
        require(doc['sha256']==ref['document_sha256'] and hashlib.sha256(source.encode()).hexdigest()==ref['normalized_source_sha256'])
        premise,hypothesis=source[left:right],normalized[a:b]
        require(0<len(premise)<=2000 and 0<len(hypothesis)<=2000)
        selected.append((candidate,a,b,dict(ref),premise,hypothesis))
    return record,retrieval,normalized,selected

def prepare(record,subject,threshold=.75,maximum=5):
    """Virtual offsets are internal; original claim/reference offsets stay separate."""
    _,_,_,selected=select(record,subject,threshold,maximum)
    if not selected:return None
    text='';pairs=[]
    for i,(_,a,b,ref,premise,hypothesis) in enumerate(selected):
        start=len(text);text+=premise+'\n';second=len(text);text+=hypothesis+'\n'
        pairs.append({'id':f'candidate-{i:03d}','first':[start,second-1],'second':[second,len(text)-1]})
    request={'schema_version':1,'language':'en','text':text,'pairs':pairs}
    validate(request)
    return request

def observe(record,subject,backend,identity,threshold=.75,maximum=5):
    record,retrieval,normalized,selected=select(record,subject,threshold,maximum)
    rows=[]
    for candidate,a,b,ref,premise,hypothesis in selected:
        values,tokens=backend(premise,hypothesis)
        require(isinstance(values,(list,tuple)) and len(values)==3 and all(type(x) in (int,float) and math.isfinite(x) and abs(x)<=1e6 for x in values))
        require(type(tokens) is int and 1<=tokens<=512)
        peak=max(values);exponents=[math.exp(x-peak) for x in values];total=sum(exponents)
        rows.append({'proposed_signal':'sig.corpus_contradiction.v1','claim_span':[a,b],'reference':dict(ref),'retrieval_score':candidate['score'],'direction':'reference_is_premise_claim_is_hypothesis','token_count':tokens,'logits':list(values),'normalized_model_scores':dict(zip(LABELS,[x/total for x in exponents])),'top_model_labels':[LABELS[i] for i,x in enumerate(values) if x==peak],'calibrated_probability':False})
    return {'profile':'retrieved-passage-nli-observation/1.0.0','state':'observed_model_outputs' if rows else 'no_similar_passage','retrieval_evaluation_obtained':True,'model_evaluation_obtained':bool(rows),'subject_sha256':corpus.sha(normalized.encode()),'manifest_sha256':record['manifest_sha256'],'normalization_id':NORMALIZATION_ID,'span_units':'NFC_unicode_codepoints','retrieval':{'method':retrieval['method'],'method_sha256':retrieval['method_sha256'],'threshold':threshold,'maximum_findings':maximum,'unsupported_reference_passages':retrieval['unsupported_reference_passages']},'reference_freshness':'unestablished','model_identity':identity if rows else None,'observations':rows,'absence_proves_false':False,'truth_established':False,'independent_corroboration':False,'tag_asserted':False,'release_approved':False}
