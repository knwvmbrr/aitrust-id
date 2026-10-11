"""Bounded literal quantitative observations, independent of tag verdicts."""
import hashlib
import json
import os
from pathlib import Path
import re
import stat
from protocol.corpus import CorpusError
from protocol.normalization import NORMALIZATION_ID
from tools.language_observations import subject_text, units, overlap, SOURCE_MARKER

ROOT=Path(__file__).resolve().parents[1]
METHOD='literal-quantitative-observations/1.0.0'
MAX_DETAILS=256
MAX_REPORT_BYTES=131072
# Recognize entire date-shaped or grouped/decimal tokens. Word-attached and
# identifier fragments are excluded; calendar validity is not inferred.
TOKEN=re.compile(r'(?<![\w#.,/:+-])(?:[0-9]{4}-[0-9]{2}-[0-9]{2}|[+-]?(?:[0-9]{1,3}(?:,[0-9]{3})+|[0-9]+)(?:\.[0-9]+)?%?)(?![\w/:+-]|[.,][0-9])',re.ASCII)


def digest(text):return hashlib.sha256(text.encode('utf-8')).hexdigest()


def observe(original,language):
    subject=subject_text(original,language)
    markers=[[m.start(),m.end()] for m in SOURCE_MARKER.finditer(subject)]
    sentence_units=units(subject)
    details=[];skipped=0
    for token in TOKEN.finditer(subject):
        span=[token.start(),token.end()]
        if overlap(span,markers):continue
        # Avoid host-version Unicode word-category decisions. This method
        # supports ASCII token boundaries; adjacent non-ASCII code points
        # are counted as unsupported rather than clipped into a finding.
        if ((span[0]>0 and ord(subject[span[0]-1])>127) or
            (span[1]<len(subject) and ord(subject[span[1]])>127)):
            skipped+=1;continue
        if len(token.group())>48:
            skipped+=1;continue
        containing=next(([start,end] for start,end in sentence_units
                         if start<=span[0] and span[1]<=end),None)
        if containing is None:
            skipped+=1;continue
        if len(details)>=MAX_DETAILS:raise CorpusError('Too many supported quantitative details.')
        source_spans=overlap(containing,markers)
        details.append({'id':None if source_spans else 'sig.unsourced_specificity.v1',
            'signal_candidate':not bool(source_spans),'span':span,
            'unit_span':containing,'source_marker_spans':source_spans,
            'kind':'date_shaped' if re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}',token.group()) else 'numeric_literal',
            'meaning':'literal_detail_with_same_unit_marker' if source_spans else 'literal_detail_without_same_unit_marker'})
    missing=sum(not d['source_marker_spans'] for d in details)
    common={'format':'quantitative-observation/v1','method':METHOD,
        'state':'OBSERVATIONS' if missing else 'NO_SUPPORTED_PATTERN',
        'supported_detail_count':len(details),'without_same_unit_marker':missing,
        'with_same_unit_marker':len(details)-missing,'skipped_detail_count':skipped,
        'source_lookup_performed':False,'source_support_established':False,
        'calendar_validity_checked':False,'truth_established':False,
        'uncertainty_inferred':False,'score_is_probability':False,
        'independent_accuracy_evidence':False,'network_used':False,'tags':[]}
    brief=dict(common)
    detail={**common,'subject_sha256':digest(subject),
        'normalization_id':NORMALIZATION_ID,'offset_unit':'NFC_unicode_codepoint',
        'method_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'source_file_sha256':{name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest()
            for name in ('tools/quantitative_observations.py','tools/language_observations.py',
                         'protocol/normalization.py','protocol/unicode15-data.json','protocol/corpus.py')},
        'parameters':{'declared_language':'en','source_context':'same_literal_sentence_unit',
                      'token_boundary':'ASCII_only','max_detail_characters':48,'max_details':MAX_DETAILS},
        'details':details,'subject_text_included':False,
        'privacy':'Hashes and spans may reveal or link information. Share deliberately.'}
    return brief,detail


def save_private(record,output):
    path=Path(output).expanduser().absolute()
    if path.resolve().is_relative_to(ROOT) or any(p.is_symlink() for p in (path.parent,*path.parent.parents)):
        raise CorpusError('Keep private reports outside this checkout without symlink ancestors.')
    info=path.parent.stat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid!=os.getuid() or stat.S_IMODE(info.st_mode)!=0o700:
        raise CorpusError('Use an existing owner-private 0700 directory.')
    raw=json.dumps(record,ensure_ascii=True,allow_nan=False,indent=2).encode()
    if len(raw)>MAX_REPORT_BYTES:raise CorpusError('Private observation report exceeds its limit.')
    try:fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    except OSError:raise CorpusError('Choose a new private report file.') from None
    try:
        with os.fdopen(fd,'wb') as stream:
            stream.write(raw);stream.flush();os.fsync(stream.fileno())
    except BaseException:
        path.unlink(missing_ok=True);raise
