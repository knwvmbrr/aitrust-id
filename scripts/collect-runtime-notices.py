import json,hashlib,importlib.metadata,pathlib,re
roots=[pathlib.Path('/usr/share/doc'),pathlib.Path('/usr/local/lib/python3.12/site-packages'),pathlib.Path('/usr/local/lib/python3.12/LICENSE.txt')]
rows=[]
for root in roots:
 paths=[root] if root.is_file() else root.rglob('*')
 for f in paths:
  if f.is_symlink() or not f.is_file() or not re.fullmatch(r'(?:licen[sc]e|copying|copyright|notice)(?:[._-].*)?',f.name,re.I):continue
  if f.stat().st_size>1048576:raise ValueError('Oversized notice')
  raw=f.read_bytes()
  try:text=raw.decode('utf-8')
  except UnicodeError:continue
  rows.append({'installed_path':str(f),'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw),'text':text})
print(json.dumps({'notices':rows,'distributions':[{'name':d.metadata.get('Name'),'version':d.version,'license':d.metadata.get('License'),'license_expression':d.metadata.get('License-Expression')} for d in importlib.metadata.distributions()]},ensure_ascii=True))
