"""Canary checks exercise real parsing, errors and middleware, not error mocks."""
import asyncio
import importlib.util
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from pydantic import BaseModel, ConfigDict
import pytest
from starlette.middleware.body_limit import RequestBodyLimitMiddleware
from protocol.http_privacy import install, PrivateResponses
from test_gateway_integration import ROOT, upstream

CANARY = 'synthetic-private-error-canary'


@pytest.fixture
def private_gateway(monkeypatch):
    spec = importlib.util.spec_from_file_location('private_gateway', ROOT/'services/gateway/app.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    install(module.app)
    return module


@pytest.mark.parametrize('payload', [
    {'text': CANARY, 'unexpected': CANARY},
    {CANARY: CANARY}, {'text': [CANARY]},
    {'text': CANARY, 'origin_host': 'a'*254},
    {'text': CANARY, 'modality': CANARY},
    {'text': CANARY*8000},
])
def test_gateway_validation_does_not_reflect_input(private_gateway, payload, caplog):
    with TestClient(private_gateway.app) as client:
        response = client.post('/v1/evaluate', json=payload)
    assert response.status_code == 422
    assert response.json() == {'detail': 'Request does not match the supported input contract'}
    assert CANARY not in response.text and CANARY not in caplog.text
    assert response.headers['cache-control'] == 'no-store'
    assert response.headers['x-content-type-options'] == 'nosniff'


@pytest.mark.parametrize('body', ['{"'+CANARY+'":', '{"text":"'+CANARY+'",}', b'\xff'])
def test_malformed_json_has_no_input_detail(private_gateway, body):
    with TestClient(private_gateway.app) as client:
        response = client.post('/v1/evaluate', content=body,
                               headers={'content-type': 'application/json'})
    assert response.status_code in (400, 422)
    assert CANARY not in response.text
    assert response.headers['cache-control'] == 'no-store'


@pytest.mark.parametrize('path,status', [('/v1/evaluate', 401), ('/not-present', 404)])
def test_nonvalidation_errors_are_not_cached(private_gateway, path, status):
    with TestClient(private_gateway.app) as client:
        response = client.post(path, json={'text': CANARY})
    assert response.status_code == status
    assert CANARY not in response.text
    assert response.headers['cache-control'] == 'no-store'


def test_body_limit_still_covers_stream_and_headers(private_gateway):
    with TestClient(private_gateway.app) as client:
        response = client.post('/v1/evaluate', content=CANARY*100_000,
                               headers={'content-type': 'application/json'})
    assert response.status_code == 413
    assert response.headers['cache-control'] == 'no-store'
    assert CANARY not in response.text


def test_internal_exception_is_fixed_and_not_logged(caplog):
    app = FastAPI()
    @app.get('/failure')
    def failure():
        raise ValueError(CANARY)
    install(app)
    with TestClient(app) as client:
        response = client.get('/failure')
    assert response.status_code == 500
    assert response.json() == {'detail': 'The service could not complete the request'}
    assert response.headers['cache-control'] == 'no-store'
    assert CANARY not in caplog.text


def test_partial_response_is_not_replaced():
    async def broken(scope, receive, send):
        await send({'type': 'http.response.start', 'status': 200, 'headers': []})
        raise RuntimeError('synthetic stream interruption')
    sent = []
    async def send(message): sent.append(message)
    async def receive(): return {'type': 'http.disconnect'}
    with pytest.raises(RuntimeError, match='stream interruption'):
        asyncio.run(PrivateResponses(broken)({'type': 'http'}, receive, send))
    assert len(sent) == 1
    assert sent[0]['headers'] == [(b'cache-control', b'no-store'), (b'x-content-type-options', b'nosniff')]


def test_cancellation_is_never_transformed_into_500():
    async def cancelled(scope, receive, send): raise asyncio.CancelledError()
    async def send(message): pytest.fail('Cancellation generated a response')
    async def receive(): return {'type': 'http.disconnect'}
    with pytest.raises(asyncio.CancelledError):
        asyncio.run(PrivateResponses(cancelled)({'type': 'http'}, receive, send))


def test_all_selected_images_use_shared_factory_and_no_access_logs():
    for name in ('gateway', 'anonymizer', 'evaluator'):
        dockerfile = (ROOT/'services'/name/'Dockerfile').read_text()
        assert '"protocol.http_privacy:application", "--factory"' in dockerfile
        assert '"--no-access-log"' in dockerfile
        assert 'protocol/http_privacy.py' in dockerfile


def test_success_remains_a_valid_assertion(private_gateway, monkeypatch):
    import httpx
    from protocol.assertions import validator
    original = httpx.AsyncClient
    def handle(request):
        if request.url.path == '/redact':
            return httpx.Response(200, json={'text': '<PERSON>', 'entities': ['PERSON'], 'entity_count': 1})
        return httpx.Response(200, json={'candidates': [], 'models': [], 'calibration_id': 'synthetic'})
    monkeypatch.setattr(private_gateway.httpx, 'AsyncClient',
                        lambda **kw: original(transport=httpx.MockTransport(handle), **kw))
    with TestClient(private_gateway.app) as client:
        response = client.post('/v1/evaluate', json={'text': CANARY},
                               headers={'authorization': 'Bearer '+private_gateway.TOKEN})
    assert response.status_code == 200
    validator().validate(response.json())
    assert CANARY not in response.text
    assert response.headers['cache-control'] == 'no-store'
