"""Cancellation must release admission and cancel upstream work without bypassing redaction."""
import asyncio
from fastapi import HTTPException
import httpx
import pytest
from test_gateway_integration import g

class Request:
    def __init__(self):self.disconnected=asyncio.Event()
    async def receive(self):
        await self.disconnected.wait();return {'type':'http.disconnect'}

def test_client_disconnect_cancels_pending_http_and_releases_slot(monkeypatch):
    async def scenario():
        started=asyncio.Event();cancelled=asyncio.Event()
        async def handle(req):
            if req.url.path=='/redact':return httpx.Response(200,json={'text':'synthetic','entities':[],'entity_count':0})
            started.set()
            try:await asyncio.Event().wait()
            except asyncio.CancelledError:cancelled.set();raise
        original=httpx.AsyncClient
        monkeypatch.setattr(g.httpx,'AsyncClient',lambda **kw:original(transport=httpx.MockTransport(handle),**kw))
        monkeypatch.setattr(g,'LIMIT',asyncio.Semaphore(4))
        request=Request();task=asyncio.create_task(g.evaluate(g.EvalRequest(text='synthetic'),request,'Bearer '+g.TOKEN,''))
        await asyncio.wait_for(started.wait(),1);request.disconnected.set()
        with pytest.raises(HTTPException) as error:await asyncio.wait_for(task,1)
        assert error.value.status_code==408 and cancelled.is_set() and g.LIMIT._value==4
    asyncio.run(scenario())

def test_caller_cancellation_joins_upstream_and_releases_slot(monkeypatch):
    async def scenario():
        started=asyncio.Event();cancelled=asyncio.Event()
        async def handle(req):
            if req.url.path=='/redact':return httpx.Response(200,json={'text':'synthetic','entities':[],'entity_count':0})
            started.set()
            try:await asyncio.Event().wait()
            except asyncio.CancelledError:cancelled.set();raise
        original=httpx.AsyncClient
        monkeypatch.setattr(g.httpx,'AsyncClient',lambda **kw:original(transport=httpx.MockTransport(handle),**kw))
        monkeypatch.setattr(g,'LIMIT',asyncio.Semaphore(4))
        task=asyncio.create_task(g.evaluate(g.EvalRequest(text='synthetic'),Request(),'Bearer '+g.TOKEN,''))
        await asyncio.wait_for(started.wait(),1);task.cancel()
        with pytest.raises(asyncio.CancelledError):await asyncio.wait_for(task,1)
        assert cancelled.is_set() and g.LIMIT._value==4
    asyncio.run(scenario())

def test_fifth_request_rejected_without_entering_upstream_then_slots_recover(monkeypatch):
    async def scenario():
        admitted=0;four_started=asyncio.Event();release=asyncio.Event()
        async def handle(req):
            nonlocal admitted
            if req.url.path=='/redact':return httpx.Response(200,json={'text':'synthetic','entities':[],'entity_count':0})
            admitted+=1
            if admitted==4:four_started.set()
            await release.wait();return httpx.Response(200,json={'candidates':[],'models':[],'calibration_id':'synthetic'})
        original=httpx.AsyncClient
        monkeypatch.setattr(g.httpx,'AsyncClient',lambda **kw:original(transport=httpx.MockTransport(handle),**kw))
        monkeypatch.setattr(g,'LIMIT',asyncio.Semaphore(4))
        tasks=[asyncio.create_task(g.evaluate(g.EvalRequest(text='synthetic'),Request(),'Bearer '+g.TOKEN,'')) for _ in range(4)]
        await asyncio.wait_for(four_started.wait(),1)
        with pytest.raises(HTTPException) as error:await g.evaluate(g.EvalRequest(text='synthetic'),Request(),'Bearer '+g.TOKEN,'')
        assert error.value.status_code==503 and admitted==4
        release.set();results=await asyncio.wait_for(asyncio.gather(*tasks),1)
        assert all(r['tags']==[] for r in results) and g.LIMIT._value==4
    asyncio.run(scenario())
