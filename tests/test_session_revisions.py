import copy
import json
import pytest
from protocol import corpus
from protocol.normalization import normalize_nfc
from tools import session_revisions as tool


def context(text):
    d = {"id": "private-context", "text": text, "sha256": corpus.sha(text.encode())}
    payload = {"format": corpus.VERSION, "documents": [d]}
    return corpus.encoded(dict(payload, manifest_sha256=corpus.sha(corpus.encoded(payload))))


def selected(previous, current, captured, spans):
    return {"profile": tool.PROFILE, "previous_sha256": tool.digest(normalize_nfc(previous)),
        "current_sha256": tool.digest(normalize_nfc(current)),
        "context_manifest_sha256": corpus.parse(captured)["manifest_sha256"], "spans": spans}


@pytest.mark.parametrize('old,new,capture,span,previous,located', [
    ('A budget.', 'Budget 25.', 'The budget is 25.', [7,9], False, True),
    ('Budget 25.', 'Budget 25.', 'Ordinary context.', [7,9], True, False),
    ('A budget.', 'Budget 25.', 'Ordinary context.', [7,9], False, False),
    ('The answer.', 'The answer is 4.', '2 + 2', [14,15], False, False),
    ('A greeting.', 'Hello.', 'A greeting in another phrasing.', [0,5], False, False),
    ('Previous.', 'Café', 'Cafe\u0301', [0,4], False, True),
    ('Previous.', 'HELLO', 'hello', [0,5], False, False),
])
def test_exact_presence_with_no_origin_or_derivation_claim(old,new,capture,span,previous,located):
    raw = context(capture)
    result = tool.compare(old,new,raw,selected(old,new,raw,[span]))
    row = result['selected_spans'][0]
    assert row['present_in_previous_revision'] is previous
    assert bool(row['captured_context_matches']) is located
    assert row['new_literal_not_located_in_captured_context'] is (not previous and not located)
    for key in ['source_completeness_verified','context_origin_authenticated','semantic_derivation_assessed',
        'human_authorship_established','ai_authorship_established','outside_knowledge_established','tag_asserted']:
        assert result[key] is False
    summary = tool.summary(result)
    assert summary['selected_spans'] == 1
    assert sum(summary[k] for k in ['literals_already_in_previous_revision','new_literals_located_in_captured_context',
            'new_literals_not_located_in_captured_context']) == 1
    assert not any(v in json.dumps(summary) for v in ['private-context', result['current_sha256']])


@pytest.mark.parametrize('spans', [[], [[True,2]], [[-1,2]], [[0,99]], [[2,2]],
    [[0,4],[2,5]], [[2,4],[0,2]], [[0,2],[0,2]], [['0',2]], [[0,2,3]]])
def test_invalid_selections_refuse(spans):
    raw = context('The context.')
    with pytest.raises(tool.ContextError):
        tool.compare('Old text.', 'New text.', raw, selected('Old text.','New text.',raw,spans))


@pytest.mark.parametrize('field,value', [('previous_sha256','0'*64), ('current_sha256','0'*64),
    ('context_manifest_sha256','0'*64), ('profile','unknown'), ('private_text','PRIVATE_CANARY')])
def test_stale_or_private_extra_selection_fields_refuse(field,value):
    raw=context('The context.'); data=selected('Old text.','New text.',raw,[[0,3]])
    data[field]=value
    with pytest.raises(tool.ContextError):
        tool.compare('Old text.','New text.',raw,data)


@pytest.mark.parametrize('raw', [b'{}', b'{"a":1,"a":2}', b'{"a":NaN}', b'{"a":1.5}', b'\xff', b''])
def test_strict_selected_json_refuses_invalid_input(raw):
    if raw == b'{}':
        assert tool.decode(raw) == {}
    else:
        with pytest.raises(tool.ContextError):tool.decode(raw)


def test_input_not_mutated_and_summary_has_no_selected_private_wording():
    raw=context('PRIVATE_CONTEXT'); data=selected('Before.','PRIVATE_SUBJECT',raw,[[0,15]])
    before=copy.deepcopy(data); result=tool.compare('Before.','PRIVATE_SUBJECT',raw,data)
    assert data==before
    text=json.dumps(tool.summary(result))
    assert 'PRIVATE_' not in text and 'sha256' not in text and 'document_id' not in text


def test_explicit_empty_prior_draft_does_not_become_an_origin_claim():
    raw=context('New.');data=selected('', 'New.', raw, [[0,4]])
    result=tool.compare('', 'New.', raw, data)
    assert not result['selected_spans'][0]['present_in_previous_revision']
    assert result['selected_spans'][0]['captured_context_matches']
    assert not result['outside_knowledge_established'] and not result['ai_authorship_established']


def test_preparation_binds_normalized_drafts_without_mutating_spans():
    raw=context('Cafe\u0301'); spans=[[0,4]]
    selection=tool.prepare('', 'Cafe\u0301', raw, spans)
    assert selection==selected('', 'Café', raw, [[0,4]])
    selection['spans'][0][0]=1
    assert spans==[[0,4]]


@pytest.mark.parametrize('spans', [None, {'spans': [[0,4]]}, [[True,4]], [[0,40]], [[0,4],[2,4]]])
def test_preparation_refuses_unusable_or_ambiguous_span_contract(spans):
    with pytest.raises(tool.ContextError):
        tool.prepare('', 'New.', context('New.'), spans)
