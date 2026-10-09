import json
import httpx
import pytest
from fastapi.testclient import TestClient
from test_gateway_integration import g


@pytest.mark.parametrize('changes', [
    {'entities': ['alice@example.com']},
    {'entities': ['UNKNOWN_CATEGORY']},
    {'entities': ['PERSON', 'PERSON'], 'entity_count': 2},
    {'entities': ['PERSON'], 'entity_count': 0},
    {'entities': [], 'entity_count': 1},
    {'entities': ['PERSON', 'EMAIL_ADDRESS'], 'entity_count': 1},
    {'entity_count': 200_001},
    {'text': 'private source'},
])
def test_invalid_redactor_never_reaches_evaluator_or_assertion(monkeypatch, changes):
    calls = []
    def handle(request):
        calls.append(request.url.path)
        return httpx.Response(200, json={'text': '<PERSON>', 'entities': ['PERSON'],
                                      'entity_count': 1, **changes})
    original = httpx.AsyncClient
    monkeypatch.setattr(g.httpx, 'AsyncClient', lambda **kw: original(transport=httpx.MockTransport(handle), **kw))
    with TestClient(g.app) as client:
        result = client.post('/v1/evaluate', headers={'authorization': 'Bearer ' + g.TOKEN},
                             json={'text': 'private source'})
    assert result.status_code == 502
    assert calls == ['/redact']
    assert 'private source' not in result.text and 'alice@example.com' not in result.text


def test_only_category_metadata_and_changed_subject_are_asserted(monkeypatch):
    def handle(request):
        if request.url.path == '/redact':
            return httpx.Response(200, json={'text': 'Email <EMAIL_ADDRESS>',
                'entities': ['EMAIL_ADDRESS'], 'entity_count': 1})
        assert json.loads(request.content)['text'] == 'Email <EMAIL_ADDRESS>'
        return httpx.Response(200, json={'candidates': [], 'models': [], 'calibration_id': 'test-only'})
    original = httpx.AsyncClient
    monkeypatch.setattr(g.httpx, 'AsyncClient', lambda **kw: original(transport=httpx.MockTransport(handle), **kw))
    with TestClient(g.app) as client:
        result = client.post('/v1/evaluate', headers={'authorization': 'Bearer ' + g.TOKEN},
                             json={'text': 'Email alice@example.com'})
    assert result.status_code == 200
    assert 'alice@example.com' not in result.text
    tag = result.json()['tags'][0]
    assert tag['code'] == 'PII_REDACTED'
    assert tag['signals'][0]['detail'] == {'entities': ['EMAIL_ADDRESS'], 'count': 1}
