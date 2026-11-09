"""Exercise the actual adapter without loading model assets or starting a service."""
import ast
from pathlib import Path
import re
from types import SimpleNamespace

import pytest

SOURCE = Path(__file__).resolve().parents[1] / 'services/anonymizer/app.py'
node = next(n for n in ast.parse(SOURCE.read_text()).body if isinstance(n, ast.ClassDef) and n.name == 'ContainedPanRecognizer')


class Upstream:
    def analyze(self, text, entities, nlp_artifacts=None):
        self.called = (text, entities, nlp_artifacts)
        return self.results


scope = {'re': re, 'InPanRecognizer': Upstream}
exec(compile(ast.Module(body=[node], type_ignores=[]), str(SOURCE), 'exec'), scope)


@pytest.mark.parametrize('text,end', [('ip_address:2001:db8::27', 10), ('1234567890 letters', 10),
                                     ('abcdefghij 1234', 10), ('abcdefghij1234', 10),
                                     ('1234567890Z', 10), ('abcd12345Z', 4)])
def test_pan_cannot_borrow_evidence_outside_its_candidate(text, end):
    r = scope['ContainedPanRecognizer'](); item = SimpleNamespace(entity_type='IN_PAN', start=0, end=end, score=.05)
    r.results = [item]
    assert r.analyze(text, ['IN_PAN']) == []


@pytest.mark.parametrize('value,score', [('ABCPA1234Z', .85), ('ABCKA1234Z', .6),
                                       ('ab@p?1234c', .05), ('1234abcdeZ', .05)])
def test_local_high_medium_and_low_pattern_evidence_keeps_identity_and_score(value, score):
    text = 'prefix ' + value + ' suffix'
    r = scope['ContainedPanRecognizer'](); item = SimpleNamespace(entity_type='IN_PAN', start=7, end=7+len(value), score=score)
    r.results = [item]; marker = object()
    assert r.analyze(text, ['IN_PAN'], marker) == [item]
    assert item.score == score and r.called == (text, ['IN_PAN'], marker)


def test_non_pan_and_separate_valid_candidates_are_untouched():
    text = 'ip_address:2001:db8::27 ABCPA1234Z'
    false = SimpleNamespace(entity_type='IN_PAN', start=0, end=10, score=.05)
    ip = SimpleNamespace(entity_type='IP_ADDRESS', start=11, end=23, score=.6)
    pan = SimpleNamespace(entity_type='IN_PAN', start=24, end=34, score=.85)
    r = scope['ContainedPanRecognizer'](); r.results = [false, ip, pan]
    # Use exact supplied offsets for the separate real-shape token.
    pan.start = text.index('ABCPA'); pan.end = len(text)
    assert r.analyze(text, ['IN_PAN', 'IP_ADDRESS']) == [ip, pan]
