"""Check scope coverage, dependency isolation, ownership and local references."""
import argparse,datetime,hashlib,json,re,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def require(condition,message):
 if not condition:raise ValueError(message)
def verify():
 scope=json.loads((ROOT/'docs/master-scope.json').read_text());plan=json.loads((ROOT/'docs/scope-delivery.json').read_text())
 original=scope['records'];records=plan['records'];packages=plan['packages']
 ids={r['id'] for r in original};indexed={r['scope_id'] for r in records};by_package={p['id']:p for p in packages}
 require(len(original)==len(ids)==202,'Missing/duplicate master record')
 require(len(records)==len(indexed)==202 and ids==indexed,'Execution crosswalk drops/adds source IDs')
 require(len(packages)==len(by_package)==39,'Missing/duplicate package')
 subtasks=[s['id'] for p in packages for s in p['subtasks']]
 require(len(subtasks)==len(set(subtasks))==117,'Missing/duplicate package subtask')
 task_ids=[r['task_id'] for r in records];require(len(task_ids)==len(set(task_ids))==202,'Missing/duplicate record task')
 covered=set();visiting=set();visited=set()
 def visit(id):
  require(id not in visiting,'Dependency cycle: '+id)
  if id in visited:return
  visiting.add(id)
  for dep in by_package[id]['dependencies']:visit(dep)
  visiting.remove(id);visited.add(id)
 for p in packages:
  require(p['job'] and p['outcome'] and p['acceptance'] and p['subtasks'],'Empty job/outcome/gate '+p['id'])
  require(set(p['scope_ids'])<=ids,'Invented scope record '+p['id']);covered.update(p['scope_ids'])
  require(all(dep in by_package for dep in p['dependencies']),'Unknown prerequisite '+p['id'])
  require(not any(dep.startswith('TAG-') for dep in p['dependencies']),'A package depends on another tag’s conclusion/completion')
  for role in ['implementation_owner','claim_reviewer','acceptance_owner','independent_review_owner']:require(p[role],'Missing owner '+p['id'])
  require((ROOT/p['contract'].split('#')[0]).exists(),'Missing contract '+p['id'])
  for path in p['references']:require((ROOT/path).exists(),'Missing evidence/source '+path)
  if p['id'].startswith('TAG-'):require(p['inputs'] and p['outputs'] and p['claim_boundaries'],'Tag I/O/limits absent')
  if p['id'] in ['TAG-UC','TAG-SC','TAG-BT']:require(p['decision'],'Proposal silently adopted')
  visit(p['id'])
 require(covered==ids,'Unmapped scope records')
 for row in original:
  mapping=[p['id'] for p in packages if row['id'] in p['scope_ids']]
  matching=next(r for r in records if r['scope_id']==row['id'])
  require(mapping==row['delivery']['work_packages']==matching['work_packages'],'Crosswalk drift '+row['id'])
  expected_deps=sorted(set(dep for p in packages if p['id'] in mapping for dep in p['dependencies']))
  require(row['dependencies']==expected_deps,'Prerequisite drift '+row['id'])
  require(not any('PS-01' in dep for dep in row['dependencies']),'Generic PS dependency remains '+row['id'])
  require(row['delivery']['task_id']==matching['task_id'],'Task ID drift '+row['id'])
 doc=(ROOT/'docs/scope-delivery.md').read_text();index=(ROOT/'docs/scope-task-index.md').read_text()
 for p in packages:require('### '+p['id']+'\n' in doc,'Package anchor absent '+p['id'])
 for r in records:require('| '+r['task_id']+' |' in index,'Record absent from reader index')
 for file in ['docs/scope-delivery.md','docs/scope-task-index.md']+[p['contract'] for p in packages if p['id'].startswith('TAG-')]:
  path=ROOT/file
  for target in re.findall(r'\]\(([^)]+)\)',path.read_text()):
   if target.startswith(('https:','http:','mailto:','#')):continue
   require((path.parent/target.split('#')[0]).resolve().exists(),'Broken local link '+file+' '+target)
 return {'captured_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'pass':True,'scope_records':202,'work_packages':39,'tag_packages':14,'package_subtasks':117,'record_tasks':202,'no_unmapped_records':True,'no_duplicate_ids':True,'dependency_graph_acyclic':True,'no_cross_tag_completion_dependencies':True,'proposal_decisions_retained':True,'local_links_exist':True,'runtime_verified_by_this_check':False,'independent_accuracy_verified_by_this_check':False}
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--report');parser.add_argument('--baseline-ref');args=parser.parse_args();result=verify()
 if args.baseline_ref:
  old=json.loads(subprocess.check_output(['git','show',args.baseline_ref+':docs/master-scope.json'],cwd=ROOT))
  new=json.loads((ROOT/'docs/master-scope.json').read_text())
  before={r['id']:(r['title'],r['layer'],r['disposition'],r['status']) for r in old['records']}
  after={r['id']:(r['title'],r['layer'],r['disposition'],r['status']) for r in new['records']}
  require(before==after,'Source IDs/title/layer/disposition/status changed')
  result['source_identity_and_disposition_preserved']=True;result['baseline_ref']=args.baseline_ref
 if args.report:(ROOT/args.report).write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps(result))
