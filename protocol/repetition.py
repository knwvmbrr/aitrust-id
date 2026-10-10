"""Literal repeated n-grams, never a truth, origin or hallucination verdict."""
import hashlib
from pathlib import Path
import re
from protocol.normalization import normalize_nfc

METHOD = 'sig.duplicate_loop.v1'
MAX_LENGTH = 20000

def inspect(text, *, n=3, minimum_occurrences=3, coverage_threshold=0.2):
    if not isinstance(text,str) or len(text)>MAX_LENGTH or '\x00' in text:
        raise ValueError('Expected bounded text')
    if type(n) is not int or not 1<=n<=8 or type(minimum_occurrences) is not int or not 2<=minimum_occurrences<=20 or type(coverage_threshold) not in (int,float) or not 0<coverage_threshold<=1:
        raise ValueError('Invalid repetition configuration')
    try: text.encode('utf-8')
    except UnicodeError: raise ValueError('Invalid Unicode input') from None
    subject=normalize_nfc(text)
    tokens=list(re.finditer(r'\S+',subject))
    groups={}
    for i in range(max(0,len(tokens)-n+1)):
        # Case sensitive, whitespace-delimited, punctuation preserved.
        gram=tuple(t.group() for t in tokens[i:i+n])
        groups.setdefault(gram,[]).append(i)
    repeated=[(gram,positions) for gram,positions in groups.items() if len(positions)>=minimum_occurrences]
    covered=set()
    for _,positions in repeated:
        for i in positions:covered.update(range(i,i+n))
    coverage=len(covered)/len(tokens) if tokens else 0.0
    # Bounded return: refuse excessively fragmented output rather than truncate evidence.
    if len(repeated)>64:raise ValueError('Too many repeated groups for this method')
    matched=bool(repeated) and coverage>=coverage_threshold
    findings=[{'id':METHOD,'occurrences':len(positions),'spans':[[tokens[i].start(),tokens[i+n-1].end()] for i in positions]} for _,positions in repeated] if matched else []
    return {'schema_version':1,'record_type':'repetition_observation','signal':METHOD,
      'matched':matched,'findings':findings,'token_count':len(tokens),'repeated_token_coverage':coverage,
      'subject_sha256':hashlib.sha256(subject.encode()).hexdigest(),
      'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
      'configuration':{'n':n,'minimum_occurrences':minimum_occurrences,'coverage_threshold':coverage_threshold},
      'normalization':'pinned Unicode 15 NFC; Python scalar spans; exact whitespace tokens',
      'tags':[],'independent_accuracy_evidence':False,
      'warning':'Repetition can be intentional. This observation does not establish hallucination, truth or AI origin.'}
