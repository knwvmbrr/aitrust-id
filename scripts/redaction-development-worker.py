"""Read only fixed synthetic fixture input and current engine source; output observations only."""
import hashlib,json,pathlib,sys
from datetime import datetime,timezone
raw=sys.stdin.buffer.read(2000001)
if len(raw)>2000000:raise ValueError('Synthetic diagnostic input limit')
payload=json.loads(raw);cases=payload['fixtures'];expected=payload['sources']
root=pathlib.Path('/app');names={'app':root/'app.py','model_loader':root/'model_identity.py','requirements_lock':root/'requirements.lock','identity_contract':root/'protocol/replay_identity.py','identity_builder':root/'replay_metadata.py'}
def hashes():return {k:hashlib.sha256(p.read_bytes()).hexdigest() for k,p in names.items()}
if hashes()!=expected:raise ValueError('Synthetic source identity differs')
sys.path.insert(0,'/app');import app
if app.REDACTOR_IDENTITY['configuration']['sources']!=expected:raise ValueError('Synthetic redactor identity differs')
output=[]
original_operate=app.anonymizer._operate
applied=[]
def observe_operation(*args,**kwargs):
 global applied
 applied=[{'entity':r.entity_type,'start':r.start,'end':r.end} for r in kwargs['pii_entities']]
 return original_operate(*args,**kwargs)
app.anonymizer._operate=observe_operation
for row in cases['rows']:
 findings=app.analyzer.analyze(text=row['text'],language='en',score_threshold=0.0)
 redacted=app.anonymizer.anonymize(text=row['text'],analyzer_results=findings)
 output.append({'id':row['id'],'predicted':[{'entity':r.entity_type,'start':r.start,'end':r.end} for r in findings],
  'applied':applied,'redaction_changed':redacted.text!=row['text'],'expected_literal_values_still_present':sum(row['text'][r['start']:r['end']] in redacted.text for r in row['expected'])})
if hashes()!=expected:raise ValueError('Synthetic source identity differs')
print(json.dumps({'captured_at':datetime.now(timezone.utc).isoformat(),'pass':True,'kind':'synthetic_english_engine_observations','rows':output,'redactor_identity':app.REDACTOR_IDENTITY,'sources':expected,'fixture_sha256':hashlib.sha256(json.dumps(cases,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest(),'source_unchanged':True,'independent_accuracy_evidence':False,'real_user_data':False,'production_services_modified':False}))
