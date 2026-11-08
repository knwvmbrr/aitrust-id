import sys as _audit_sys
import pathlib as _audit_path
_executable=_audit_path.Path(_audit_sys.executable).resolve()
def _deny_network(event,args):
 if event=='subprocess.Popen':
  argv=args[1]
  if (args[0] in ('file','/usr/bin/file') and isinstance(argv,(list,tuple))
      and len(argv)==3 and argv[:2]==['file','-b']
      and _audit_path.Path(argv[2]).resolve()==_executable):return
 if event in ('socket.connect','socket.getaddrinfo','socket.gethostbyname','socket.gethostbyaddr','subprocess.Popen','os.system'):
  raise RuntimeError('Direct development probe refuses network or unapproved child execution')
_audit_sys.addaudithook(_deny_network)
"""Read only fixed synthetic fixture input and current engine source; output observations only."""
import hashlib,json,pathlib,sys
from datetime import datetime,timezone
raw=sys.stdin.buffer.read(2000001)
if len(raw)>2000000:raise ValueError('Synthetic diagnostic input limit')
payload=json.loads(raw);cases=payload['fixtures'];expected=payload['sources']
root=pathlib.Path.cwd();names={'app':root/'app.py','model_loader':root/'model_identity.py','requirements_lock':root/'requirements.lock','identity_contract':root/'protocol/replay_identity.py','identity_builder':root/'replay_metadata.py'}
def hashes():return {k:hashlib.sha256(p.read_bytes()).hexdigest() for k,p in names.items()}
if hashes()!=expected:raise ValueError('Synthetic source identity differs')
sys.path.insert(0,str(root));import app
if app.REDACTOR_IDENTITY['configuration']['sources']!=expected:raise ValueError('Synthetic redactor identity differs')
def observe_cases(app,rows):
 output=[]
 original_operate=app.anonymizer._operate
 applied=[]
 def observe_operation(*args,**kwargs):
  nonlocal applied
  applied=[{'entity':r.entity_type,'start':r.start,'end':r.end} for r in kwargs['pii_entities']]
  return original_operate(*args,**kwargs)
 app.anonymizer._operate=observe_operation
 try:
  for row in rows:
   findings=app.analyzer.analyze(text=row['text'],language='en',score_threshold=0.0)
   # Presidio may mutate these objects while merging anonymization conflicts.
   predicted=[{'entity':r.entity_type,'start':r.start,'end':r.end} for r in findings]
   applied=[]
   redacted=app.anonymizer.anonymize(text=row['text'],analyzer_results=findings)
   output.append({'id':row['id'],'predicted':predicted,
    'applied':applied,'redaction_changed':redacted.text!=row['text'],'expected_literal_values_still_present':sum(row['text'][r['start']:r['end']] in redacted.text for r in row['expected'])})
 finally:
  app.anonymizer._operate=original_operate
 return output
output=observe_cases(app,cases['rows'])
if hashes()!=expected:raise ValueError('Synthetic source identity differs')
print(json.dumps({'captured_at':datetime.now(timezone.utc).isoformat(),'pass':True,'kind':'synthetic_english_engine_observations','rows':output,'redactor_identity':app.REDACTOR_IDENTITY,'sources':expected,'fixture_sha256':hashlib.sha256(json.dumps(cases,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest(),'source_unchanged':True,'independent_accuracy_evidence':False,'real_user_data':False,'production_services_modified':False}))
