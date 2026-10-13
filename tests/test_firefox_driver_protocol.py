"""Local-driver framing refuses mismatched, oversized and incomplete replies."""
import importlib.util
import io
import json
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('firefox_driver',ROOT/'scripts/verify-firefox-extension.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)


def framed(value):
 raw=json.dumps(value).encode();return str(len(raw)).encode()+b':'+raw


def driver(raw):
 obj=object.__new__(m.Driver);obj.stream=io.BytesIO(raw);obj.identifier=0
 class Socket:
  def sendall(self,data):self.sent=data
 obj.socket=Socket();return obj


@pytest.mark.parametrize('raw',[b'',b'a:',b'0000000000:',b'0:',b'2000001:',b'4:{}'])
def test_invalid_length_or_truncation_refused(raw):
 with pytest.raises(ValueError):driver(raw).read()


def test_exact_response_identity():
 obj=driver(framed([1,1,None,{'value':'fixture'}]))
 assert obj.command('WebDriver:Fixture')=={'value':'fixture'}
 size,raw=obj.socket.sent.split(b':',1)
 assert int(size)==len(raw) and json.loads(raw)==[0,1,'WebDriver:Fixture',{}]


@pytest.mark.parametrize('reply',[[1,2,None,{}],[0,1,None,{}],[1,1,{'error':'unknown'},None],[1,1,None],{'value':'wrong'}])
def test_wrong_command_or_error_refused(reply):
 with pytest.raises(ValueError):driver(framed(reply)).command('WebDriver:Fixture')


def prepared(tmp_path):
 import shutil
 for role,files in m.SERVICE_FILES.items():
  for filename in files:
   source=ROOT/filename if filename.startswith('protocol/') else ROOT/'services'/role/filename
   target=tmp_path/role/'app'/filename;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
 return tmp_path


def test_bind_all_actual_service_helpers(tmp_path):
 bound=m.bind_service_sources(prepared(tmp_path))
 assert 'protocol/transport_signing.py' in bound and 'services/anonymizer/replay_metadata.py' in bound
 assert len(bound)==16


@pytest.mark.parametrize('role,filename',[('gateway','protocol/transport_signing.py'),('anonymizer','replay_metadata.py'),('evaluator','app.py'),('gateway','requirements.lock')])
def test_changed_actual_sources_never_start(tmp_path,role,filename):
 root=prepared(tmp_path);(root/role/'app'/filename).write_bytes(b'changed')
 with pytest.raises(ValueError):m.bind_service_sources(root)


def test_linked_actual_sources_never_start(tmp_path):
 root=prepared(tmp_path/'roles');path=root/'gateway/app/protocol/transport_signing.py'
 raw=path.read_bytes();path.unlink();outside=tmp_path/'other';outside.write_bytes(raw);path.symlink_to(outside)
 with pytest.raises(ValueError):m.bind_service_sources(root)
