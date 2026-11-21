import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import pytest
from protocol import corpus, corpus_support
from tools import nf_device as nf


def result(claim,passage,check='literal'):
    return json.loads(nf.inspect_nf_device(claim,passage,check))


@pytest.mark.parametrize('claim,passage,check',[
 ('Water is safe.','Water is safe.','literal'),('Water is safe.','Water is not safe.','literal'),
 ('Water is safe.','Water is not safe.','cosine'),('red green\nblue','red green\nblue','cosine'),
 ('e\u0301😀','é😀 é😀','literal'),('🙂','🙂','literal'),('Water is safe.','é\nWater is safe.','cosine'),
 ('A','A '*20,'literal'),('a','A','literal'),('x','y','cosine'),
 ('a\v b','a\v b','cosine'),('a\x1c b','a\x1c b','cosine'),
 ('\tred \r\n blue\n','red\nblue\n','cosine')])
def test_canonical(claim,passage,check):
    out=result(claim,passage,check)
    content={'format':corpus.VERSION,'documents':[{'id':'selected','sha256':corpus.sha(passage.encode()),'text':passage}]}
    record=dict(content,manifest_sha256=corpus.sha(corpus.encoded(content)))
    expected=corpus.query(record,claim) if check=='literal' else corpus_support.observe(record,claim)
    assert out['original']==expected
    assert out['claim']['raw_sha256']==corpus.sha(claim.encode())
    assert out['passage']['raw_sha256']==corpus.sha(passage.encode())
    assert out['tags']==[] and out['truth_established'] is False


def test_negation_is_similarity_not_support():
    out=result('Water is safe.','Water is not safe.','cosine')
    assert out['original']['findings'][0]['score']==0.866025403784
    assert out['original']['truth_established'] is False
    assert out['original']['entailment_checked'] is False


@pytest.mark.parametrize('a,b,c',[
 ('','a','literal'),('a','','literal'),('a\0','a','literal'),('a','b\0','cosine'),
 ('a'*2001,'a','literal'),('a','b'*2001,'literal'),('a\ud800','a','literal'),
 ('é','é','cosine'),('a','é','cosine'),('a','b','unknown'),('a','b',[]),
 (None,'a','literal'),('a',[], 'literal'),('a','b',True)])
def test_refusals(a,b,c):
    with pytest.raises((ValueError,UnicodeError)):
        nf.inspect_nf_device(a,b,c)


def test_optional_method_missing_leaves_literal(monkeypatch):
    monkeypatch.setitem(sys.modules,'protocol.corpus_support',None)
    # import-from can retain a cached attribute, so remove only during this control.
    monkeypatch.delattr('protocol.corpus_support',raising=False)
    with pytest.raises(ImportError): result('a','a','cosine')
    assert result('a','a','literal')['original']['state']=='REFERENCE_MATCH'


def builder():
    spec=importlib.util.spec_from_file_location('nf_build',Path('scripts/build-nf-device.py'))
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod


def build_root(tmp_path):
    mod=builder()
    for name in mod.ALL_FILES:
        dst=tmp_path/name;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(name,dst)
    return mod,tmp_path


def test_builder_separate_exact_bundles(tmp_path):
    mod,root=build_root(tmp_path);m=mod.build(root)
    assert m==mod.build(root)
    for check in ['literal','cosine']:
        entry=m['checks'][check];raw=(root/('site/public'+entry['path'])).read_bytes()
        assert hashlib.sha256(raw).hexdigest()==entry['bundle_sha256']
        files=json.loads(raw)['files'];assert ('protocol/corpus_support.py' in files)==(check=='cosine')
        assert all(corpus.sha(v.encode())==entry['sources'][p] for p,v in files.items())


def test_builder_mutation_refuses_without_replacing(tmp_path,monkeypatch):
    mod,root=build_root(tmp_path);mod.build(root)
    old=(root/'site/src/nf-device-manifest.json').read_bytes();original=mod.publish
    def changed(cap,outputs):
        (root/'tools/nf_device.py').write_text('changed')
        return original(cap,outputs)
    monkeypatch.setattr(mod,'publish',changed)
    with pytest.raises(mod.NFBuildError):mod.build(root)
    assert (root/'site/src/nf-device-manifest.json').read_bytes()==old


def test_builder_symlink_refusal(tmp_path):
    mod,root=build_root(tmp_path);p=root/'tools/nf_device.py';p.unlink();p.symlink_to(Path('tools/nf_device.py').resolve())
    with pytest.raises((OSError,ValueError)):mod.build(root)
