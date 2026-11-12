"""Check original-text offsets and unchanged upstream evidence without loading NLP."""
import ast
from pathlib import Path
from types import SimpleNamespace

import pytest

SOURCE=Path(__file__).resolve().parents[1]/'services/anonymizer/app.py'
NODE=next(n for n in ast.parse(SOURCE.read_text()).body
          if isinstance(n,ast.ClassDef) and n.name=='OfflineEmailRecognizer')


class Upstream:
    def analyze(self,text,entities,nlp_artifacts=None):
        self.calls.append((text,entities,nlp_artifacts))
        return self.responses[len(self.calls)-1]


def recognizer(responses):
    def result(entity_type,start,end,score,**kwargs):
        return SimpleNamespace(entity_type=entity_type,start=start,end=end,score=score,**kwargs)
    scope={'EmailRecognizer':Upstream,'RecognizerResult':result,
           'tldextract':SimpleNamespace(TLDExtract=lambda **_:None)}
    exec(compile(ast.Module(body=[NODE],type_ignores=[]),str(SOURCE),'exec'),scope)
    value=scope['OfflineEmailRecognizer']();value.calls=[];value.responses=responses
    return value


def finding(start,end,entity='EMAIL_ADDRESS',score=.5):
    return SimpleNamespace(entity_type=entity,start=start,end=end,score=score,
                           analysis_explanation=object(),recognition_metadata={'source':'upstream'})


def test_no_separator_returns_same_objects_and_forwards_nlp():
    rows=[finding(0,17)];r=recognizer([rows]);marker=object()
    assert r.analyze('pilot@example.com',['EMAIL_ADDRESS'],marker) is rows
    assert r.calls==[('pilot@example.com',['EMAIL_ADDRESS'],marker)]


@pytest.mark.parametrize('separator',['\u200b','\u200c','\u200d','\ufeff'])
@pytest.mark.parametrize('prefix',['Contact ','Ω 😀 '])
def test_hidden_separator_maps_the_entire_candidate_back_to_original_text(separator,prefix):
    value='pilot@exam'+separator+'ple.com';text=prefix+value+'.'
    projected=finding(len(prefix),len(prefix)+17)
    r=recognizer([[],[projected]]);marker=object()
    result=r.analyze(text,['EMAIL_ADDRESS'],marker)
    assert len(result)==1
    actual=result[0]
    assert text[actual.start:actual.end]==value
    assert actual.score==projected.score and actual.analysis_explanation is projected.analysis_explanation
    assert actual.recognition_metadata==projected.recognition_metadata
    assert actual.recognition_metadata is not projected.recognition_metadata
    assert r.calls[0]==(text,['EMAIL_ADDRESS'],marker)
    assert r.calls[1]==(prefix+'pilot@example.com.',['EMAIL_ADDRESS'],None)
    assert (projected.start,projected.end)==(len(prefix),len(prefix)+17)


def test_separators_outside_email_do_not_add_duplicate_or_expand_span():
    text='\u200bpilot@example.com\u200b'
    original=finding(1,18);r=recognizer([[original],[finding(0,17)]])
    assert r.analyze(text,['EMAIL_ADDRESS'])==[original]


def test_whitespace_and_other_format_controls_are_not_removed():
    text='a \u200b@exam\u202eple.com';r=recognizer([[],[]])
    assert r.analyze(text,['EMAIL_ADDRESS'])==[]
    assert r.calls[1][0]=='a @exam\u202eple.com'


def test_existing_findings_remain_and_separate_candidates_keep_their_offsets():
    text='one@example.com and two@exam\u200bple.org'
    original=finding(0,15);other=finding(20,35)
    r=recognizer([[original],[finding(0,15),other]])
    results=r.analyze(text,['EMAIL_ADDRESS'])
    assert results[0] is original
    assert [(x.start,x.end) for x in results]==[(0,15),(20,36)]
    assert text[results[1].start:results[1].end]=='two@exam\u200bple.org'


def test_empty_projection_never_invokes_upstream_twice():
    r=recognizer([[]]);assert r.analyze('\u200b\ufeff',['EMAIL_ADDRESS'])==[]
    assert len(r.calls)==1


def test_unrequested_entity_does_not_trigger_projection():
    rows=[finding(0,2,'IP_ADDRESS')];r=recognizer([rows])
    assert r.analyze('x\u200by',['IP_ADDRESS']) is rows
    assert len(r.calls)==1


@pytest.mark.parametrize('bad',[finding(-1,5),finding(0,0),finding(0,100),finding(0,5,'PERSON')])
def test_invalid_projected_findings_cannot_be_added(bad):
    r=recognizer([[],[bad]])
    assert r.analyze('pilot@exam\u200bple.com',['EMAIL_ADDRESS'])==[]
