"""Verify optional research source/asset/dependency/notice identities without installing a model."""
import hashlib,json,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from research.nli.backend import EXPECTED,MODEL_REVISION,VERSIONS

def verify(root=ROOT):
 p=root/'research/nli';assets=json.loads((p/'assets.json').read_text())
 if assets['profile']!='pinned-nli-assets/1.0.0' or assets['revision']!=MODEL_REVISION or assets['independently_audited'] is not False:raise ValueError('Model profile drift')
 names=[r['name'] for r in assets['files']]
 if names!=['model.onnx','tokenizer.json','config.json','README.md']:raise ValueError('Model member drift')
 for row in assets['files']:
  suffix='onnx/model.onnx' if row['name']=='model.onnx' else row['name']
  if row['url']!='https://huggingface.co/cross-encoder/nli-deberta-v3-xsmall/resolve/'+MODEL_REVISION+'/'+suffix:raise ValueError('Model origin drift')
  if row['name'] in EXPECTED and (row['sha256'],row['bytes'])!=EXPECTED[row['name']]:raise ValueError('Model execution identity drift')
  if type(row['bytes']) is not int or not 0<row['bytes']<=300_000_000 or not re.fullmatch('[a-f0-9]{64}',row['sha256']):raise ValueError('Model size or hash drift')
 for platform in ['mac','linux']:
  rows=json.loads((p/f'wheel-provenance-{platform}.json').read_text())
  if {r['name']:r['version'] for r in rows}!=VERSIONS or len(rows)!=len(VERSIONS):raise ValueError('Runtime version drift')
  expected=''.join(f"{r['name']}=={r['version']} --hash=sha256:{r['sha256']}\n" for r in rows)
  if (p/f'requirements-{platform}.lock').read_text()!=expected:raise ValueError('Runtime lock drift')
  for row in rows:
   if not row['pypi_url'].startswith('https://files.pythonhosted.org/packages/') or not re.fullmatch('[a-f0-9]{64}',row['sha256']):raise ValueError('Wheel identity drift')
 notices=json.loads((p/'notices.json').read_text())
 if notices['permission_cleared'] is not False:raise ValueError('Notice retention is not clearance')
 for row in notices['notices']:
  if row['notice_file']!='research/nli/notices/'+row['sha256']+'.txt' or hashlib.sha256((root/row['notice_file']).read_bytes()).hexdigest()!=row['sha256']:raise ValueError('Notice changed')
 return {'pass':True,'pinned_model_assets':len(names),'locked_packages_per_platform':len(VERSIONS),'preserved_notice_members':len(notices['notices']),'installs_or_downloads_executed':False,'permission_cleared':False,'independent_accuracy':False}
if __name__=='__main__':print(json.dumps(verify()))
