"""The real diagnostic must snapshot mutable findings and isolate each case."""
import ast
from pathlib import Path
from types import SimpleNamespace
import pytest
ROOT=Path(__file__).resolve().parents[1]
tree=ast.parse((ROOT/'scripts/redaction-development-worker.py').read_text())
node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='observe_cases')
namespace={};exec(compile(ast.Module(body=[node],type_ignores=[]),'<actual-worker-observer>','exec'),namespace)
observe=namespace['observe_cases']

def fixture(fail=False):
    original=lambda **kwargs: SimpleNamespace(text='[MASK]')
    def analyze(**kwargs):
        return [SimpleNamespace(entity_type='IP_ADDRESS',start=0,end=2)] if kwargs['text']=='one' else []
    anonymizer=SimpleNamespace(_operate=original)
    def anonymize(text,analyzer_results):
        if fail:raise RuntimeError('synthetic failure')
        if not analyzer_results:return SimpleNamespace(text=text)
        analyzer_results[0].end=3
        return anonymizer._operate(text=text,pii_entities=analyzer_results)
    anonymizer.anonymize=anonymize
    return SimpleNamespace(analyzer=SimpleNamespace(analyze=analyze),anonymizer=anonymizer),original

ROWS=[{'id':'first','text':'one','expected':[{'start':0,'end':2}]},{'id':'second','text':'two','expected':[]}]

def test_snapshot_precedes_consumer_mutation():
    app,original=fixture();out=observe(app,ROWS[:1])
    assert out[0]['predicted']==[{'entity':'IP_ADDRESS','start':0,'end':2}]
    assert out[0]['applied']==[{'entity':'IP_ADDRESS','start':0,'end':3}]
    assert app.anonymizer._operate is original

def test_no_operation_case_cannot_inherit_prior_masking():
    app,_=fixture();out=observe(app,ROWS)
    assert out[1]['applied']==[] and out[1]['predicted']==[]
    assert out[1]['redaction_changed'] is False

def test_instrumentation_is_restored_after_consumer_failure():
    app,original=fixture(fail=True)
    with pytest.raises(RuntimeError,match='synthetic failure'):observe(app,ROWS)
    assert app.anonymizer._operate is original
