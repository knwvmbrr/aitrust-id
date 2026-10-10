"""A live process or a 200 page is insufficient; only bounded explicit readiness passes."""
import importlib.util
from pathlib import Path
from unittest.mock import Mock
import pytest
ROOT=Path(__file__).resolve().parents[1]
s=importlib.util.spec_from_file_location('probe',ROOT/'services/gateway/healthcheck.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
@pytest.mark.parametrize('body,status,expected',[(b'{"ok":true}',200,True),(b'{"ok":false}',200,False),(b'{"ok":"true"}',200,False),(b'{"live":true}',200,False),(b'not-json',200,False),(b'[]',200,False),(b'{}',503,False),(b'a'*4097,200,False)])
def test_readiness_requires_valid_bounded_json(monkeypatch,body,status,expected):
    response=Mock();response.status=status;response.read.return_value=body
    response.__enter__=Mock(return_value=response);response.__exit__=Mock(return_value=False)
    opener=Mock();opener.open.return_value=response
    monkeypatch.setattr(m.urllib.request,'build_opener',lambda *args:opener)
    assert m.ready() is expected
    assert opener.open.call_args.kwargs['timeout']==2

def test_outage_returns_false_without_traceback(monkeypatch):
    opener=Mock();opener.open.side_effect=OSError('synthetic private detail')
    monkeypatch.setattr(m.urllib.request,'build_opener',lambda *args:opener)
    assert m.ready() is False
