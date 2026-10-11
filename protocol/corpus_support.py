"""Local lexical support observation; resemblance is not truth or entailment."""
from collections import Counter
import hashlib
import math
from pathlib import Path
import re
from protocol import corpus
from protocol.normalization import normalize_nfc, NORMALIZATION_ID

METHOD = 'corpus-support-ascii-cosine/1.0.0'
SIGNAL = 'sig.corpus_support.v1'
MAX_CLAIMS = 32
MAX_PASSAGES = 4096
MAX_TOKENS = 512
TOKEN = re.compile(r'[A-Za-z0-9]+')


def lines(value):
    result=[];offset=0
    for line in value.splitlines(keepends=True):
        body=line.rstrip('\r\n');left=len(body)-len(body.lstrip());right=len(body.rstrip())
        if right>left: result.append((offset+left,offset+right,body[left:right]))
        offset+=len(line)
    return result


def vector(value):
    if not value.isascii(): raise corpus.CorpusError('This retrieval method supports ASCII passages only.')
    tokens=TOKEN.findall(value)
    if not tokens or len(tokens)>MAX_TOKENS: raise corpus.CorpusError('Passage has no supported words or exceeds the token limit.')
    return Counter(t.lower() for t in tokens)


def cosine(a,b):
    return sum(v*b.get(k,0) for k,v in a.items()) / math.sqrt(sum(v*v for v in a.values())*sum(v*v for v in b.values()))


def observe(record,subject,threshold=.75,maximum=10):
    if type(threshold) not in (int,float) or not math.isfinite(threshold) or not 0<threshold<=1 or type(maximum) is not int or not 1<=maximum<=10:
        raise corpus.CorpusError('Invalid retrieval parameters.')
    if not isinstance(subject,str) or not subject.strip() or len(subject)>2000 or '\x00' in subject:
        raise corpus.CorpusError('Supply one to 2,000 subject characters.')
    try:subject.encode('utf-8',errors='strict')
    except UnicodeError:raise corpus.CorpusError('Subject must use valid Unicode.') from None
    normalized=normalize_nfc(subject);claims=lines(normalized)
    if not 1<=len(claims)<=MAX_CLAIMS:raise corpus.CorpusError('Claim-unit count exceeds the limit.')
    query=[(*unit,vector(unit[2])) for unit in claims]
    passages=[];unsupported=0;total=0
    for doc in record['documents']:
        source=normalize_nfc(doc['text'])
        normalized_hash=corpus.sha(source.encode('utf-8'))
        for start,end,phrase in lines(source):
            total+=1
            if total>MAX_PASSAGES:raise corpus.CorpusError('Reference passage count exceeds the limit.')
            try:v=vector(phrase)
            except corpus.CorpusError:unsupported+=1;continue
            passages.append((doc,start,end,v,normalized_hash))
    if not passages:raise corpus.CorpusError('No supported reference passages available.')
    findings=[]
    for start,end,phrase,v in query:
        matched=[]
        for doc,left,right,w,normalized_hash in passages:
            score=min(1.,cosine(v,w))
            if score>=threshold:
                matched.append({'id':SIGNAL,'score':round(score,12),'spans':[[start,end]],
                    'reference':{'document_id':doc['id'],'document_sha256':doc['sha256'],
                    'normalized_source_sha256':normalized_hash,'source_span':[left,right]},
                    'meaning':'lexical_similarity_only'})
        matched.sort(key=lambda m:(-m['score'],m['reference']['document_id'],m['reference']['source_span'][0]))
        findings.extend(matched[:maximum])
    # Bound final output independently of input/reference volume.
    findings.sort(key=lambda m:(-m['score'],m['spans'][0][0],m['reference']['document_id'],m['reference']['source_span'][0]))
    return {'format':'local-corpus-support-observation/1.0.0','method':METHOD,
        'method_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'subject_sha256':corpus.sha(normalized.encode('utf-8')),'subject_characters':len(normalized),
        'manifest_sha256':record['manifest_sha256'],'normalization_id':NORMALIZATION_ID,
        'offset_unit':'NFC_unicode_codepoint','claim_unit':'nonempty_trimmed_input_line',
        'reference_unit':'nonempty_trimmed_source_line','threshold':threshold,'maximum_findings':maximum,
        'claim_units':len(claims),'reference_passages':len(passages),'unsupported_reference_passages':unsupported,
        'reference_freshness':'unestablished','findings':findings[:maximum],
        'state':'SIMILAR_PASSAGE' if findings else 'NO_SIMILAR_PASSAGE',
        'score_is_probability':False,'truth_established':False,'entailment_checked':False,
        'network_used':False,'tags':[],'independent_accuracy_evidence':False}
