import importlib.util,sys,copy,json
from pathlib import Path
import pytest
r=Path(__file__).resolve().parents[1];sys.path.insert(0,str(r))
from protocol import corpus
m=corpus
@pytest.fixture
def example(tmp_path):
 tmp_path.chmod(0o700);f=tmp_path/'source.txt';f.write_text('The room is empty.\nThe door was closed yesterday.\n');out=tmp_path/'corpus.json';corpus.create([('manual',f)],out);return out,corpus.load(out)
def test_existing_loader_matches_captured_parser(example):
 assert m.parse(example[0].read_bytes())==example[1]
@pytest.mark.parametrize('kind',['format','manifest','source-hash','source-text','source-id','documents-empty','numeric','duplicate-json','extra-field','surrogate','null','bad-json','oversize'])
def test_corrupted_capture_refuses(example,kind):
 value=copy.deepcopy(example[1])
 if kind=='format':value['format']='future'
 if kind=='manifest':value['manifest_sha256']='0'*64
 if kind=='source-hash':value['documents'][0]['sha256']='0'*64
 if kind=='source-text':value['documents'][0]['text']+='changed'
 if kind=='source-id':value['documents'][0]['id']='../unsafe'
 if kind=='documents-empty':value['documents']=[]
 if kind=='extra-field':value['extra']=True
 if kind=='surrogate':value['documents'][0]['text']='\ud800'
 if kind=='null':value=None
 raw=json.dumps(value).encode()
 if kind=='numeric':raw=b'{"format":1}'
 if kind=='duplicate-json':raw=b'{"format":"a","format":"a"}'
 if kind=='bad-json':raw=b'{'
 if kind=='oversize':raw=b'x'*(corpus.MAX_STORE_BYTES+1)
 with pytest.raises(corpus.CorpusError):m.parse(raw)
