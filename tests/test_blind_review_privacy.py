import csv,importlib.util,json,os,stat,sys
from pathlib import Path
from unittest.mock import patch
import pytest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tools import blind_review_io as io
spec=importlib.util.spec_from_file_location('blind',ROOT/'scripts/prepare-ps-review.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

def source(tmp_path,text='Synthetic ordinary text'):
 tmp_path.chmod(0o700);p=tmp_path/'source.jsonl';p.write_text(json.dumps({'id':'one','text':text,'source':'synthetic only','category':'display'})+'\n');p.chmod(0o600);return p

def packet(tmp_path):
 p=source(tmp_path);d=tmp_path/'packet';m.freeze(p,d)
 for i in (1,2):
  f=d/f'reviewer-{i}.json';v=json.loads(f.read_text());v['items'][0].update(label='positive',reason='Synthetic control only');f.write_text(json.dumps(v))
  f=d/f'reviewer-{i}.csv';rows=list(csv.DictReader(f.open()));rows[0].update(label='positive',reason='Synthetic control only')
  with f.open('w',newline='') as stream:w=csv.DictWriter(stream,fieldnames=m.FIELDS);w.writeheader();w.writerows(rows)
 return d

@pytest.mark.parametrize('fmt',['csv','json'])
def test_roundtrip_private(tmp_path,fmt):
 d=packet(tmp_path);r=m.compare(d,fmt);assert r['agreement_count']==1 and not r['release_assessed'];assert d.stat().st_mode&0o777==0o700;assert all(f.stat().st_mode&0o777==0o600 for f in d.iterdir())

@pytest.mark.parametrize('mode',[0o644,0o664,0o666])
def test_public_input_refused(tmp_path,mode):
 p=source(tmp_path);p.chmod(mode)
 with pytest.raises(ValueError):m.freeze(p,tmp_path/'packet')
 assert not (tmp_path/'packet').exists()

@pytest.mark.parametrize('mode',[0o755,0o750,0o777])
def test_public_parent_refused(tmp_path,mode):
 p=source(tmp_path);tmp_path.chmod(mode)
 with pytest.raises(ValueError):m.freeze(p,tmp_path/'packet')
 assert not (tmp_path/'packet').exists()

@pytest.mark.parametrize('kind',['symlink','hardlink','directory','fifo'])
def test_nonprivate_source_kind_refused(tmp_path,kind):
 p=source(tmp_path);target=tmp_path/'original';p.rename(target)
 if kind=='symlink':p.symlink_to(target)
 elif kind=='hardlink':os.link(target,p)
 elif kind=='directory':p.mkdir(mode=0o700)
 else:os.mkfifo(p,0o600)
 with pytest.raises(ValueError):m.freeze(p,tmp_path/'packet')
 assert not (tmp_path/'packet').exists()

@pytest.mark.parametrize('name',['manifest.json','items.jsonl','reviewer-1.json','reviewer-2.json'])
def test_imported_symlink_refused(tmp_path,name):
 d=packet(tmp_path);f=d/name;f.unlink();f.symlink_to(tmp_path/'source.jsonl')
 with pytest.raises(ValueError):m.compare(d,'json')

@pytest.mark.parametrize('raw',['{"a":1,"a":2}','{"a":NaN}','{"a":1e999}','"\\ud800"','['*70+'0'+']'*70])
def test_json_contract_rejects(raw):
 with pytest.raises((ValueError,TypeError)):m.strict_json(raw.encode())

@pytest.mark.parametrize('flag',['independence_verified','sampling_accepted','predictions_run','release_assessed'])
@pytest.mark.parametrize('bad',[True,0])
def test_forged_validation_flag_refused(tmp_path,flag,bad):
 d=packet(tmp_path);f=d/'manifest.json';v=json.loads(f.read_text());v[flag]=bad;f.write_text(json.dumps(v))
 with pytest.raises(ValueError):m.compare(d,'json')

@pytest.mark.parametrize('field,value',[('item_count',True),('item_count',2),('input_sha256','x'),('format','future'),('extra','claim')])
def test_bad_manifest_refused(tmp_path,field,value):
 d=packet(tmp_path);f=d/'manifest.json';v=json.loads(f.read_text());v[field]=value;f.write_text(json.dumps(v))
 with pytest.raises(ValueError):m.compare(d,'json')

@pytest.mark.parametrize('fmt',['csv','json'])
def test_large_reason_refused(tmp_path,fmt):
 d=packet(tmp_path);f=d/f'reviewer-1.{fmt}'
 if fmt=='json':v=json.loads(f.read_text());v['items'][0]['reason']='x'*2001;f.write_text(json.dumps(v))
 else:
  rows=list(csv.DictReader(f.open()));rows[0]['reason']='x'*2001
  with f.open('w',newline='') as stream:w=csv.DictWriter(stream,fieldnames=m.FIELDS);w.writeheader();w.writerows(rows)
 with pytest.raises(ValueError):m.compare(d,fmt)

@pytest.mark.parametrize('mutate',['duplicate_header','extra_header','extra_value','missing_value'])
def test_csv_shape_refused(tmp_path,mutate):
 d=packet(tmp_path);f=d/'reviewer-1.csv';text=f.read_text();lines=text.splitlines()
 if mutate=='duplicate_header':lines[0]=lines[0].replace('source','text')
 elif mutate=='extra_header':lines[0]+=',prediction'
 elif mutate=='extra_value':lines[1]+=',PS'
 else:lines[1]=','.join(lines[1].split(',')[:-1])
 f.write_text('\n'.join(lines)+'\n')
 with pytest.raises(ValueError):m.compare(d)

@pytest.mark.parametrize('text',['=formula',' +formula','\t@formula','\n-formula','ordinary'])
def test_spreadsheet_boundary(tmp_path,text):
 p=source(tmp_path,text);d=tmp_path/'packet';m.freeze(p,d);rows=list(csv.DictReader((d/'reviewer-1.csv').open()));assert rows[0]['text']==m.spreadsheet(text)


def test_size_refused_before_read(tmp_path):
 p=source(tmp_path)
 with p.open('r+b') as f:f.truncate(m.INPUT_LIMIT+1)
 with pytest.raises(ValueError,match='byte limit'):m.freeze(p,tmp_path/'packet')
 assert not (tmp_path/'packet').exists()


def test_output_limit_has_no_partial_folder(tmp_path):
 p=source(tmp_path)
 with patch.object(m,'MEMBER_LIMIT',8),pytest.raises(ValueError,match='output byte'):m.freeze(p,tmp_path/'packet')
 assert not (tmp_path/'packet').exists()


def test_write_failure_cleans_only_new_members(tmp_path):
 p=source(tmp_path);real=os.fsync;calls=0
 def fail(fd):
  nonlocal calls
  calls+=1
  if calls==2:raise OSError('synthetic write failure')
  return real(fd)
 with patch.object(io.os,'fsync',side_effect=fail),pytest.raises(OSError):m.freeze(p,tmp_path/'packet')
 assert not (tmp_path/'packet').exists() and p.exists()


def test_existing_folder_untouched(tmp_path):
 p=source(tmp_path);d=tmp_path/'packet';d.mkdir(mode=0o700);f=d/'mine';f.write_text('retained')
 with pytest.raises(FileExistsError):m.freeze(p,d)
 assert f.read_text()=='retained'

def test_cleanup_preserves_foreign_entry(tmp_path):
 p=source(tmp_path);real=os.fsync
 def fail(fd):
  foreign=tmp_path/'packet'/'foreign';foreign.write_text('retained')
  raise OSError('synthetic foreign entry')
 with patch.object(io.os,'fsync',side_effect=fail),pytest.raises(OSError):m.freeze(p,tmp_path/'packet')
 assert (tmp_path/'packet'/'foreign').read_text()=='retained';assert not (tmp_path/'packet'/'items.jsonl').exists()


def test_cleanup_preserves_replaced_file_inode(tmp_path):
 p=source(tmp_path)
 def fail(fd):
  target=tmp_path/'packet'/'items.jsonl';target.unlink();target.write_text('replacement')
  raise OSError('synthetic replaced member')
 with patch.object(io.os,'fsync',side_effect=fail),pytest.raises(OSError):m.freeze(p,tmp_path/'packet')
 assert (tmp_path/'packet'/'items.jsonl').read_text()=='replacement'


def test_read_descriptor_stays_in_original_directory(tmp_path):
 d=packet(tmp_path);expected=(d/'items.jsonl').read_bytes()
 with io.directory(d,ROOT) as fd:
  d.rename(tmp_path/'original');d.mkdir(mode=0o700);fake=d/'items.jsonl';fake.write_text('different directory');fake.chmod(0o600)
  assert io.member(fd,'items.jsonl',m.MEMBER_LIMIT)==expected


def test_renamed_output_parent_is_not_reported_success(tmp_path):
 p=source(tmp_path);real=os.fsync;moved=False
 def move(fd):
  nonlocal moved
  if not moved:
   moved=True;(tmp_path/'packet').rename(tmp_path/'moved');(tmp_path/'packet').mkdir(mode=0o700);(tmp_path/'packet'/'foreign').write_text('retained')
  return real(fd)
 with patch.object(io.os,'fsync',side_effect=move),pytest.raises(ValueError,match='directory changed'):m.freeze(p,tmp_path/'packet')
 assert (tmp_path/'packet'/'foreign').read_text()=='retained' and not list((tmp_path/'moved').iterdir())


def test_spreadsheet_id_collision_refused_before_creation(tmp_path):
 p=source(tmp_path);rows=[{'id':i,'text':'sample','source':'synthetic','category':'display'} for i in ['=one',"'=one"]];p.write_text('\n'.join(json.dumps(r) for r in rows)+'\n')
 with pytest.raises(ValueError,match='identifiers collide'):m.freeze(p,tmp_path/'packet')
 assert not (tmp_path/'packet').exists()


@pytest.mark.parametrize('args', [['PRIVATE_ARG_CANARY'], ['compare','--unknown','PRIVATE_ARG_CANARY']])
def test_argument_errors_do_not_echo_private_values(args):
 import subprocess
 result=subprocess.run([sys.executable,str(ROOT/'scripts/prepare-ps-review.py'),*args],capture_output=True,timeout=5)
 assert result.returncode==2 and b'PRIVATE_ARG_CANARY' not in result.stdout+result.stderr
 assert b'No validation accepted' in result.stderr
