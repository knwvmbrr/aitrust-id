"""Versioned literal double-quote placement; never semantic quotation judgment."""
import hashlib
from pathlib import Path
from protocol.corpus import CorpusError
from tools import authority_quotation
from tools.language_observations import subject_text

ROOT=Path(__file__).resolve().parents[1]
METHOD='mobile-double-quote-authority-observations/1.0.0'
GRAMMAR='one_style_ASCII_lexical_pairs_or_balanced_curly_double_quotes'
SOURCES=('tools/authority_mobile_quotation.py','scripts/authority-mobile-quotation.py',
         *authority_quotation.SOURCES)


def quote_style(text):
    if any(c in text for c in '\u00ab\u00bb`'):
        raise CorpusError('Supported double-quote placement is unavailable.')
    ascii_quotes='"' in text
    curly=any(c in text for c in '\u201c\u201d')
    if ascii_quotes and curly:
        raise CorpusError('Supported double-quote placement is unavailable.')
    if not curly:
        # The existing scanner enforces lexical ASCII pairing and limits.
        authority_quotation.quoted_ranges(text)
        return 'ASCII' if ascii_quotes else 'NONE'
    opened=False;count=0
    for i,c in enumerate(text):
        if c not in '\u201c\u201d':continue
        if i and text[i-1]=='\\':
            raise CorpusError('Supported double-quote placement is unavailable.')
        if c=='\u201c':
            if opened:raise CorpusError('Supported double-quote placement is unavailable.')
            opened=True
        else:
            if not opened:raise CorpusError('Supported double-quote placement is unavailable.')
            opened=False;count+=1
            if count>authority_quotation.MAX_QUOTES:raise CorpusError('Supported double-quote placement is unavailable.')
    if opened:raise CorpusError('Supported double-quote placement is unavailable.')
    return 'CURLY'


def observe(original,language):
    text=subject_text(original,language)
    if len(text.encode('utf-8','strict'))>32000:raise CorpusError('Supported double-quote placement is unavailable.')
    style=quote_style(text)
    projected=text.translate({0x201c:'"',0x201d:'"'})
    brief,details=authority_quotation.observe(projected,language)
    brief={**brief,'format':'mobile-authority-quotation-observation/v1','method':METHOD}
    details={**details,**brief,'subject_sha256':hashlib.sha256(text.encode()).hexdigest(),
             'source_sha256':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES},
             'parameters':{**details['parameters'],'quote_grammar':GRAMMAR,'quote_style':style,
                           'ascii_nesting_inferred':False,'single_quotes_interpreted':False}}
    return brief,details
