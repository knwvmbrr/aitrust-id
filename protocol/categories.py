"""Declared lexical development strata, independent of detector predictions/labels.

These are engineering input-form groups, not representative population categories.
"""
import re
CATEGORY_VERSION='development-input-form/v1'
def category_for_text(text):
    if not isinstance(text,str):raise ValueError('Category input must be text')
    if re.search(r'\b(?:base64|b64decode|unhexlify|fromhex|hex)\b',text,re.I):return 'encoded_content_forms'
    if re.search(r'\b(?:curl|wget)\b',text):
        if re.search(r'(?:\s-[oO](?:\s|[^\s])|\s>|--output(?:\s|=))',text):return 'file_download_forms'
        if re.search(r'\b(?:never|avoid|warning)\b|do not|don.t|[\'`]',text,re.I):return 'quoted_or_discussed_download_forms'
        return 'other_download_forms'
    if re.search(r'\b(?:bash|sh|python\d?|echo|eval|exec|sudo|env)\b',text):return 'other_code_forms'
    return 'ordinary_text_forms'
