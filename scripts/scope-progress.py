"""Verify and render the evidence-based completion ledger; no status inference."""
import argparse
import datetime
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
MILESTONES = ['bounded_contract','implemented_mechanism','executable_checks','selected_integration','final_acceptance']
def verify(data):
    scope=json.loads((ROOT/'docs/master-scope.json').read_text())
    plan=json.loads((ROOT/'docs/scope-delivery.json').read_text())
    expected={'records':{x['id'] for x in scope['records']},'packages':{x['id'] for x in plan['packages']},'subtasks':{x['id'] for p in plan['packages'] for x in p['subtasks']}}
    for collection,ids in expected.items():
        actual=[x['id'] for x in data[collection]]
        if len(actual)!=len(set(actual)) or set(actual)!=ids:raise ValueError('Missing/duplicate/orphan '+collection)
    all_rows=[x for group in ('records','packages','subtasks','enhancements') for x in data[group]]
    if len({x['id'] for x in all_rows})!=len(all_rows):raise ValueError('Duplicate global audit ID')
    for x in all_rows:
        percent=x['percent_complete']
        if type(percent) is not int or percent not in range(0,101,20):raise ValueError('Invalid milestone percentage '+x['id'])
        if x['milestones_passed']!=MILESTONES[:percent//20]:raise ValueError('Milestone mismatch '+x['id'])
        if not x['checked_by'] or not x['evidence']:raise ValueError('Missing checker/evidence '+x['id'])
        when=datetime.datetime.fromisoformat(x['audited_at'])
        if when.tzinfo is None:raise ValueError('Timestamp must include timezone '+x['id'])
        for path in x['evidence']:
            if not (ROOT/path.split('#')[0]).is_file():raise ValueError('Missing evidence '+path)
        if percent==100:
            if not x['completed_by'] or not x['implemented_by'] or not x['completed_at'] or x['next_fix'] or x['required_acceptance'] or x['queue']!='completed':raise ValueError('Unsupported 100% '+x['id'])
        elif not x['next_fix'] or not x['next_owner'] or not x['required_acceptance'] or x['completed_at'] or x['completed_by'] or x['queue']!='open':raise ValueError('Open item lacks fix/owner or claims completion '+x['id'])
    record_by={x['id']:x for x in data['records']}
    for p in plan['packages']:
        audited=next(x for x in data['packages'] if x['id']==p['id'])
        if audited['percent_complete']>min(record_by[id]['percent_complete'] for id in p['scope_ids']):raise ValueError('Package inflates child completion '+p['id'])
    return {'captured_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'pass':True,'records':len(data['records']),'packages':len(data['packages']),'subtasks':len(data['subtasks']),'enhancements':len(data['enhancements']),'completed_records':sum(x['percent_complete']==100 for x in data['records']),'open_records':sum(x['percent_complete']<100 for x in data['records']),'no_records_removed':True,'no_overall_percentage':True,'all_open_items_have_fix_and_owner':True,'independent_release_asserted_by_ledger':False}
def cell(s):return str(s).replace('|',r'\|').replace('\n',' ')
def render(data):
    done=[x for x in data['records'] if x['percent_complete']==100]
    client_date=datetime.date.fromisoformat(data['client_date'])
    text=f'''# Scope completion ledger — {client_date.isoformat()}

Audit timestamp: **{data['audited_at']}** (UTC; client date {client_date.strftime('%B')} {client_date.day}).

**{len(done)} complete requirement records; {202-len(done)} remain open.** All 202
original IDs are retained. Completed records leave the open queue, not history.
The 39 packages and 117 subtasks remain separately tracked: broad package
completion cannot be inferred from one functioning feature. Four research
opportunities are attached to existing packages, without expanding or replacing
the adopted tag taxonomy.

## How to read the percentages

0% = no milestone evidenced; 20% = bounded written contract; 40% = implemented
mechanism; 60% = executable positive/negative checks; 80% = complete selected
integration; **100% = all required acceptance for the full named item functioning
and evidenced**. These are equally weighted milestone percentages, not effort,
accuracy or a project-wide percentage. Draft scope alone earns at most 20%.
Independent accuracy, human accessibility and actual phones are credited only
when performed. Tags have their own gates. Shared capabilities and policy records
are not automatically released tags.

Completion timestamps are when this audit verifies completion, not invented
historical finish times. Prior implementation attribution comes from session/run
records; Claude's initial additions are attributed from the owner's report.
Codex performed this audit and repaired the research components. A Git account
name does not identify which agent wrote the code. Current source checks and
historical public/runtime observations remain distinguishable in evidence.

No overall average is calculated: records overlap, costs differ, grouping records
are not additional products, and 20% planning is not 20% of business delivery.
Future source/route/acceptance changes reopen affected records.

[Execution plan](scope-delivery.md) · [Machine-readable ledger](scope-progress.json)
· [Current executable checks](../runs/2026-10-09-scope-completion-checks.json)
· [Review of Claude's additions](competitive-differentiation.md)

## Completed queue

'''
    def table(rows):
        out='| ID / job | Complete | Who completed / implementation credit | Next fix and owner | Evidence |\n|---|---|---|---|---|\n'
        for x in rows:
            who='; '.join(x['completed_by'] if x['percent_complete']==100 else x['implemented_by']) or 'No implementation credited; Codex planned'
            fix=('Completed at '+x['completed_at']) if x['percent_complete']==100 else x['next_fix']+' Owner: '+x['next_owner']
            refs=', '.join('['+p.split('/')[-1]+'](../'+p+')' for p in x['evidence'])
            out+='| '+cell(x['id']+' — '+x['title'])+' | '+str(x['percent_complete'])+'% | '+cell(who)+' | '+cell(fix)+' | '+refs+' |\n'
        return out+'\n'
    text+=table(done)
    for label,rows in [('Open tag requirements',[x for x in data['records'] if x['percent_complete']<100 and x['id'].startswith('T-')]),('All other open requirements',[x for x in data['records'] if x['percent_complete']<100 and not x['id'].startswith('T-')]),('Work packages',data['packages']),('Package subtasks',data['subtasks']),('Research enhancements — no adoption or release implied',data['enhancements'])]:
        text+='## '+label+'\n\n'+table(rows)
    (ROOT/'docs/scope-progress.md').write_text(text.rstrip()+'\n')
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--render',action='store_true');parser.add_argument('--report');a=parser.parse_args()
    data=json.loads((ROOT/'docs/scope-progress.json').read_text());result=verify(data)
    if a.render:render(data)
    if a.report:(ROOT/a.report).write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))
