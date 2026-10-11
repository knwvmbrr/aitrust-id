"""Bounded English self-pair observations; never emit a tag or calibrated confidence."""
import hashlib
import math
import re
LABELS=('contradiction','entailment','neutral')
MAX_TEXT=20_000
MAX_PAIRS=16
ID=re.compile(r'[a-z0-9][a-z0-9_-]{0,63}')
class PairError(ValueError):
    pass

def require(ok):
    if not ok:raise PairError('Sentence-pair input or method output refused')

def scalar(value):
    return isinstance(value,str) and '\x00' not in value and all(not 0xd800<=ord(x)<=0xdfff for x in value)

def validate(request):
    require(isinstance(request,dict) and set(request)=={'schema_version','language','text','pairs'})
    require(type(request['schema_version']) is int and request['schema_version']==1 and request['language']=='en')
    text=request['text'];require(scalar(text) and 1<=len(text)<=MAX_TEXT and text.strip())
    pairs=request['pairs'];require(isinstance(pairs,list) and 1<=len(pairs)<=MAX_PAIRS)
    seen=set();selected=[]
    for pair in pairs:
        require(isinstance(pair,dict) and set(pair)=={'id','first','second'})
        identity=pair['id'];require(isinstance(identity,str) and ID.fullmatch(identity) and identity not in seen);seen.add(identity)
        spans=[]
        for role in ['first','second']:
            value=pair[role];require(isinstance(value,list) and len(value)==2 and all(type(x) is int for x in value))
            start,end=value;require(0<=start<end<=len(text) and end-start<=2000 and text[start:end].strip());spans.append((start,end))
        first,second=spans;require(first[1]<=second[0] or second[1]<=first[0])
        selected.append((identity,first,second,text[first[0]:first[1]],text[second[0]:second[1]]))
    return text,selected

def analyze(request,backend,model_identity):
    text,pairs=validate(request)
    # Validate all input before any model sees it; a method failure produces no partial job.
    rows=[]
    for identity,first,second,a,b in pairs:
        values,tokens=backend(a,b)
        require(isinstance(values,(tuple,list)) and len(values)==3 and all(type(x) in (int,float) and math.isfinite(x) and abs(x)<=1e6 for x in values))
        require(type(tokens) is int and 1<=tokens<=512)
        peak=max(values);exponents=[math.exp(x-peak) for x in values];total=sum(exponents);scores=[x/total for x in exponents]
        # Stable ties retain the declared model label order; the tie remains explicit.
        winners=[i for i,v in enumerate(values) if v==peak]
        rows.append({'pair_id':identity,'first_span':list(first),'second_span':list(second),'pair_direction':'first_is_premise_second_is_hypothesis','token_count':tokens,'logits':list(values),'normalized_model_scores':dict(zip(LABELS,scores)),'top_model_labels':[LABELS[i] for i in winners],'calibrated_probability':False})
    return {'profile':'self-pair-nli-observation/1.0.0','status':'observed_model_outputs','language':'en','subject_sha256':hashlib.sha256(text.encode()).hexdigest(),'span_units':'original_unicode_codepoints','preprocessing':'none; exact caller-selected text','selection':'caller_selected_nonoverlapping_spans; not automatic sentence segmentation','model_identity':model_identity,'pairs':rows,'independent_corroboration':False,'truth_established':False,'intent_established':False,'tag_asserted':False,'release_approved':False}
