"""Resolve preserved legacy group IDs without issuing tags or completing children."""
from pathlib import Path
from protocol.evidence import read_evidence
ROOT=Path(__file__).resolve().parents[1]
EXPECTED={'F-019':['F-019a','F-019b','F-019c'],'F-020':['F-020a','F-020b'],
          'F-021':['T-FA','T-PA'],'F-022':['T-IV'],'F-029':['F-029a','F-029b','F-029c']}


def indexed(rows):
    if type(rows) is not list or len(rows)!=202:raise ValueError('Scope grouping requires all 202 records')
    result={}
    for row in rows:
        if type(row) is not dict or type(row.get('id')) is not str or row['id'] in result:raise ValueError('Invalid scope identity')
        result[row['id']]=row
    return result


def project(mapping,scope,progress):
    if type(mapping) is not dict or set(mapping)!={'profile','groups'} or mapping['profile']!='legacy-scope-groupings/v1':raise ValueError('Unsupported scope grouping profile')
    groups=mapping['groups']
    if type(groups) is not list or len(groups)!=len(EXPECTED):raise ValueError('Incomplete grouping mapping')
    original=indexed(scope);current=indexed(progress)
    if set(original)!=set(current):raise ValueError('Scope/ledger identities differ')
    result=[];seen=set()
    for group in groups:
        if type(group) is not dict or set(group)!={'id','members'} or type(group['id']) is not str:raise ValueError('Invalid group fields')
        gid=group['id']
        if gid in seen or gid not in EXPECTED or group['members']!=EXPECTED[gid]:raise ValueError('Grouping membership changed')
        seen.add(gid)
        if gid not in original or original[gid]['title']!='Legacy grouping for '+', '.join(EXPECTED[gid]):raise ValueError('Legacy group identity changed')
        members=[]
        for mid in group['members']:
            if mid not in original or mid in EXPECTED:raise ValueError('Unknown or cyclic group member')
            item=current[mid];percent=item['percent_complete']
            if type(percent) is not int or percent not in range(0,101,20) or item['queue']!=('completed' if percent==100 else 'open'):raise ValueError('Invalid member status')
            members.append({'id':mid,'title':original[mid].get('display_title',original[mid]['title']),
                            'percent_complete':percent,'queue':item['queue'],'next_fix':item['next_fix']})
        result.append({'id':gid,'kind':'legacy_grouping','members':members,'independent_detector':False,
                       'parent_completion_completes_members':False,'grouping_is_tag_release':False})
    return result


def read(root=ROOT):
    root=Path(root).resolve()
    return project(read_evidence(root/'docs/scope-groups.json',16384),
                   read_evidence(root/'docs/master-scope.json')['records'],
                   read_evidence(root/'docs/scope-progress.json')['records'])
