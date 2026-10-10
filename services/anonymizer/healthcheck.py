"""Silent, bounded readiness probe for this container's existing loopback endpoint."""
import json
import urllib.request

def ready():
    try:
        opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open('http://127.0.0.1:8000/healthz',timeout=2) as response:
            body=response.read(4097)
            return response.status==200 and len(body)<=4096 and json.loads(body).get('ok') is True
    except (OSError,ValueError,TypeError,AttributeError):
        return False

if __name__=='__main__':raise SystemExit(0 if ready() else 1)
