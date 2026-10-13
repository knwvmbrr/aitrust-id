"""Legacy links complete independently; children retain their own release gates."""
from copy import deepcopy
import json
from pathlib import Path
import pytest
from protocol import scope_groups as g
ROOT=Path(__file__).resolve().parents[1]
@pytest.fixture
def data():
    return [json.loads((ROOT/n).read_text()) for n in ['docs/scope-groups.json','docs/master-scope.json','docs/scope-progress.json']]

def test_all_five_groups_preserve_jobs_and_do_not_complete_members(data):
    mapping,scope,ledger=data;before=deepcopy(ledger)
    out=g.project(mapping,scope['records'],ledger['records'])
    assert {r['id'] for r in out}==set(g.EXPECTED) and ledger==before
    for group in out:
        assert [r['id'] for r in group['members']]==g.EXPECTED[group['id']]
        assert not group['independent_detector'] and not group['parent_completion_completes_members'] and not group['grouping_is_tag_release']
        for member in group['members']:
            actual=next(r for r in ledger['records'] if r['id']==member['id'])
            assert member['percent_complete']==actual['percent_complete'] and member['next_fix']==actual['next_fix']

@pytest.mark.parametrize('kind',['profile','extra','missing_group','duplicate_group','unknown_group','unknown_child','cycle',
    'duplicate_child','reordered_members','scope_missing','ledger_missing','scope_duplicate','ledger_duplicate',
    'changed_original_title','invalid_percent','boolean_percent','wrong_queue','different_ids'])
def test_invalid_mapping_and_progress_refused(data,kind):
    m,s,l=data;first=m['groups'][0]
    if kind=='profile':m['profile']='future'
    elif kind=='extra':first['text']='PRIVATE_CANARY'
    elif kind=='missing_group':m['groups'].pop()
    elif kind=='duplicate_group':m['groups'][-1]=deepcopy(first)
    elif kind=='unknown_group':first['id']='F-999'
    elif kind=='unknown_child':first['members'][0]='F-999'
    elif kind=='cycle':first['members'][0]='F-019'
    elif kind=='duplicate_child':first['members'][1]=first['members'][0]
    elif kind=='reordered_members':first['members'].reverse()
    elif kind=='scope_missing':s['records'].pop()
    elif kind=='ledger_missing':l['records'].pop()
    elif kind=='scope_duplicate':s['records'][-1]=deepcopy(s['records'][0])
    elif kind=='ledger_duplicate':l['records'][-1]=deepcopy(l['records'][0])
    elif kind=='changed_original_title':next(r for r in s['records'] if r['id']=='F-019')['title']='Detector released'
    elif kind in ['invalid_percent','boolean_percent','wrong_queue']:
        row=next(r for r in l['records'] if r['id']=='F-019a')
        if kind=='invalid_percent':row['percent_complete']=99
        elif kind=='boolean_percent':row['percent_complete']=True
        else:row['queue']='completed'
    elif kind=='different_ids':l['records'][-1]['id']='F-999'
    with pytest.raises(ValueError):g.project(m,s['records'],l['records'])


def test_group_completion_can_never_raise_unfinished_tag_children(data):
    mapping,scope,ledger=data
    for row in ledger['records']:
        if row['id'] in g.EXPECTED:row['percent_complete']=100;row['queue']='completed'
    out=g.project(mapping,scope['records'],ledger['records'])
    for gid in ['F-021','F-022']:
        assert all(r['percent_complete']==20 and r['queue']=='open' for r in next(r for r in out if r['id']==gid)['members'])
