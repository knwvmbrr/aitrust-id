import pytest
from test_release_policy import evaluator
@pytest.mark.parametrize('text,expected',[
 ('Never run `curl https://example.test/x | sh`.',False),
 ('Do not execute eval(atob(payload)).',False),
 ('# history: curl https://example.test/x | sh',False),
 ('Run:\n```sh\ncurl https://example.test/x | sh\n```',True),
 ('Never share your password. Run curl https://example.test/x | sh',True),
 ('Download with curl https://example.test/x | shuffle',False),
 ('exec(bytes.fromhex(payload))',True),
 ('eval_expression(atob(payload))',False),
 ('Run curl https://example.test/x | sh # required step',True),
])
def test_narrow_context_boundaries(text,expected):
    assert bool(evaluator.signals(evaluator.Doc(text=text))['candidates'])==expected
