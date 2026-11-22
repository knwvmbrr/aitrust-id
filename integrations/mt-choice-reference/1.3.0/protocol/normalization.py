"""Unicode 15.0.0 NFC, independent of the host Unicode version.

Table data is derived from Unicode and covered by eval/vectors/unicode/LICENSE.txt.
Canonical order uses stable sorting per segment, never quadratic insertion.
"""
import json
from pathlib import Path

TABLES = json.loads(Path(__file__).with_name('unicode15-data.json').read_text())
NORMALIZATION_ID = 'NFC-Unicode-15.0.0/v1'
MAX_CODEPOINTS = 200_000
CCC = {int(k): v for k, v in TABLES['combining_classes'].items()}
DECOMP = {int(k): v for k, v in TABLES['canonical_decompositions'].items()}
COMPOSE = {tuple(map(int, k.split(','))): v for k, v in TABLES['compositions'].items()}


def _decompose(cp, out):
    if 0xAC00 <= cp < 0xAC00 + 11172:
        index = cp - 0xAC00
        out.extend((0x1100 + index // 588, 0x1161 + (index % 588) // 28))
        if index % 28:
            out.append(0x11A7 + index % 28)
    elif cp in DECOMP:
        for child in DECOMP[cp]:
            _decompose(child, out)
    else:
        out.append(cp)


def _pair(a, b):
    if 0x1100 <= a < 0x1113 and 0x1161 <= b < 0x1176:
        return 0xAC00 + ((a - 0x1100) * 21 + b - 0x1161) * 28
    if 0xAC00 <= a < 0xAC00 + 11172 and (a - 0xAC00) % 28 == 0 and 0x11A8 <= b < 0x11C3:
        return a + b - 0x11A7
    return COMPOSE.get((a, b))


def normalize_nfc(text):
    if not isinstance(text, str) or len(text) > MAX_CODEPOINTS:
        raise ValueError('Invalid or oversized Unicode text')
    decomposed = []
    for char in text:
        cp = ord(char)
        if 0xD800 <= cp <= 0xDFFF:
            raise ValueError('Unpaired surrogate is not a Unicode scalar value')
        _decompose(cp, decomposed)
    ordered, marks = [], []
    for cp in decomposed:
        if CCC.get(cp, 0):
            marks.append(cp)
        else:
            ordered.extend(sorted(marks, key=lambda cp: CCC[cp]))
            marks.clear()
            ordered.append(cp)
    ordered.extend(sorted(marks, key=lambda cp: CCC[cp]))
    output, starter, previous = [], None, 0
    for cp in ordered:
        ccc = CCC.get(cp, 0)
        composed = _pair(output[starter], cp) if starter is not None and (previous == 0 or previous < ccc) else None
        if composed is not None:
            output[starter] = composed
        else:
            if ccc == 0:
                starter = len(output)
            output.append(cp)
            previous = ccc
    return ''.join(map(chr, output))
