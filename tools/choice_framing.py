"""Caller-bound binary framing observations; additional options are not verified."""
import hashlib,re,platform,unicodedata
from pathlib import Path
from protocol import corpus
from protocol.normalization import normalize_nfc,NORMALIZATION_ID
from tools.language_observations import subject_text,digest

class FrameError(ValueError):pass

def require(value):
    if not value:raise FrameError('Choice framing input or context refused')

def span(value,text,limit):
    require(isinstance(value,list) and len(value)==2 and all(type(n) is int for n in value))
    start,end=value;require(0<=start<end<=len(text) and end-start<=limit and text[start:end].strip())
    return start,end

def observe(original,record,context):
    subject=subject_text(original,'en');record=corpus.parse(corpus.encoded(record))
    require(isinstance(context,dict) and set(context)=={'format','language','subject_sha256','manifest_sha256','frames'})
    require(context['format']=='choice-frame-context/v1' and context['language']=='en' and context['subject_sha256']==digest(subject) and context['manifest_sha256']==record['manifest_sha256'])
    frames=context['frames'];require(isinstance(frames,list) and 1<=len(frames)<=16)
    documents={d['id']:d for d in record['documents']};prepared=[];previous=-1
    for frame in frames:
        require(isinstance(frame,dict) and set(frame)=={'span','choices','additional_reference'})
        left,right=span(frame['span'],subject,2000);require(left>=previous);previous=right
        choices=frame['choices'];require(isinstance(choices,list) and len(choices)==2)
        first,second=[span(s,subject,256) for s in choices]
        require(left<=first[0]<first[1]<=second[0]<second[1]<=right)
        words=[subject[a:b].strip().casefold() for a,b in [first,second]];require(words[0]!=words[1])
        ref=frame['additional_reference'];require(isinstance(ref,dict) and set(ref)=={'document_id','document_sha256','source_span'})
        require(isinstance(ref['document_id'],str) and ref['document_id'] in documents)
        doc=documents[ref['document_id']];require(doc['sha256']==ref['document_sha256'])
        source=normalize_nfc(doc['text']);a,b=span(ref['source_span'],source,2000)
        require(source[a:b].strip().casefold() not in words)
        prepared.append((left,right,first,second,dict(ref),digest(source)))
    rows=[];unmatched=[]
    for left,right,first,second,ref,source_hash in prepared:
        # These positions are an explicit caller selection, not an automatic
        # parse, quotation classification or proof that other options work.
        prefix=subject[left:first[0]];gap=subject[first[1]:second[0]]
        leading=re.search(r'\b(either|only|neither)\s*$',prefix,re.I)
        if leading and leading.group(1).casefold() not in ('either','only','neither'):
            leading=None
        expected='nor' if leading and leading.group(1).casefold()=='neither' else 'or'
        connector=re.fullmatch(r'[\s,]*'+expected+r'[\s,:]*',gap,re.I)
        if leading is None or connector is None:
            unmatched.append([left,right]);continue
        trailing=re.search(r'\b'+expected+r'\b',gap,re.I)
        construction=leading.group(1).casefold()+'_'+expected
        markers=[[left+leading.start(),left+leading.end(1)],
                 [first[1]+trailing.start(),first[1]+trailing.end()]]
        negation=[[left+m.start(),left+m.end()] for m in
                  re.finditer(r'\b(?:not|neither|nor)\b',subject[left:right],re.I)
                  if m.group().casefold() in ('not','neither','nor')]
        rows.append({'proposed_signal':None if negation else 'sig.false_dilemma.v1','frame_span':[left,right],
            'choice_spans':[list(first),list(second)],'binary_marker_spans':markers,
            'construction':construction,'negation_marker_spans':negation,
            'negation_scope_resolved':False,
            'additional_reference':{**ref,'normalized_source_sha256':source_hash},
            'meaning':'caller_selected_two_mentioned_choices_with_caller_nominated_additional_passage',
            'additional_option_verified':False,'exhaustiveness_established':False,
            'quoted_or_recommended_resolved':False,'manipulation_established':False})
    return {'profile':'caller-bound-choice-framing-observation/1.1.0',
        'state':'OBSERVATIONS' if rows else 'NO_SUPPORTED_PATTERN','language':'en',
        'subject_sha256':digest(subject),'manifest_sha256':record['manifest_sha256'],
        'method_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'runtime':{'implementation':platform.python_implementation(),'python_version':platform.python_version(),'unicode_runtime':unicodedata.unidata_version},
        'normalization_id':NORMALIZATION_ID,'span_units':'NFC_unicode_codepoints',
        'selection':'caller_selected_two_choices_and_additional_reference',
        'observations':rows,'unmatched_selected_frames':unmatched,
        'source_freshness':'unestablished','truth_established':False,
        'independent_corroboration':False,'tag_asserted':False,'release_approved':False}
