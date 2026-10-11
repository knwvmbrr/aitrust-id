"""Exact entity/span development counts, never a privacy clearance or population estimate."""
from collections import Counter
import re

ENTITY=re.compile(r'[A-Z][A-Z_]{1,39}')
def spans(values,length):
    if not isinstance(values,list) or len(values)>256:raise ValueError('Invalid recognition observations')
    result=set()
    for row in values:
        if not isinstance(row,dict) or set(row)!={'entity','start','end'}:raise ValueError('Invalid recognition observations')
        if not isinstance(row['entity'],str) or not ENTITY.fullmatch(row['entity']):raise ValueError('Invalid recognition observations')
        if type(row['start']) is not int or type(row['end']) is not int or not 0<=row['start']<row['end']<=length:raise ValueError('Invalid recognition observations')
        result.add((row['entity'],row['start'],row['end']))
    return result

def compare(expected,predicted,length):
    if type(length) is not int or not 0<=length<=2000:raise ValueError('Invalid recognition observations')
    truth=spans(expected,length);found=spans(predicted,length)
    if len(truth)!=len(expected):raise ValueError('Invalid recognition observations')
    categories=sorted({v[0] for v in truth|found});rows=[]
    for category in categories:
        t={v for v in truth if v[0]==category};f={v for v in found if v[0]==category};tp=len(t&f)
        rows.append({'entity':category,'tp':tp,'fp':len(f-t),'fn':len(t-f),'expected':len(t),'predicted':len(f),
            'partial_overlap_predictions':sum(any(max(a,c)<min(b,d) for _,c,d in t) for _,a,b in f-t)})
    return {'categories':rows,'tp':len(truth&found),'fp':len(found-truth),'fn':len(truth-found),
        'expected':len(truth),'predicted':len(found),'duplicate_predictions_removed':len(predicted)-len(found),
        'all_expected_exact':truth<=found,'no_unexpected_predictions':found<=truth}

def aggregate(cases):
    if not isinstance(cases,list) or not 1<=len(cases)<=256:raise ValueError('Invalid recognition observations')
    rows={};case_ids=set();slices={k:Counter() for k in ['en','out_of_coverage']}
    for case in cases:
        if not isinstance(case,dict) or set(case)!={'id','coverage','counts'} or case['coverage'] not in slices or not isinstance(case['id'],str) or not re.fullmatch('[a-z][a-z0-9_]{0,63}',case['id']) or case['id'] in case_ids:raise ValueError('Invalid recognition observations')
        case_ids.add(case['id']);c=case['counts'];expected={'categories','tp','fp','fn','expected','predicted','duplicate_predictions_removed','all_expected_exact','no_unexpected_predictions'}
        if not isinstance(c,dict) or set(c)!=expected or not isinstance(c['categories'],list):raise ValueError('Invalid recognition observations')
        totals=Counter();seen=set()
        for row in c['categories']:
            if not isinstance(row,dict) or set(row)!={'entity','tp','fp','fn','expected','predicted','partial_overlap_predictions'} or not isinstance(row['entity'],str) or not ENTITY.fullmatch(row['entity']) or row['entity'] in seen:raise ValueError('Invalid recognition observations')
            seen.add(row['entity'])
            if any(type(row[k]) is not int or not 0<=row[k]<=256 for k in ['tp','fp','fn','expected','predicted','partial_overlap_predictions']) or row['expected']!=row['tp']+row['fn'] or row['predicted']!=row['tp']+row['fp'] or row['partial_overlap_predictions']>row['fp']:raise ValueError('Invalid recognition observations')
            for k in ['tp','fp','fn','expected','predicted']:totals[k]+=row[k]
            key=(case['coverage'],row['entity']);r=rows.setdefault(key,Counter())
            for k in ['tp','fp','fn','expected','predicted','partial_overlap_predictions']:r[k]+=row[k]
        if any(type(c[k]) is not int or c[k]!=totals[k] for k in ['tp','fp','fn','expected','predicted']) or type(c['duplicate_predictions_removed']) is not int or not 0<=c['duplicate_predictions_removed']<=256 or type(c['all_expected_exact']) is not bool or c['all_expected_exact']!=(c['fn']==0) or type(c['no_unexpected_predictions']) is not bool or c['no_unexpected_predictions']!=(c['fp']==0):raise ValueError('Invalid recognition observations')
        section=slices[case['coverage']];section['cases']+=1;section['cases_with_misses']+=c['fn']>0;section['cases_with_unexpected_predictions']+=c['fp']>0
        for k in ['tp','fp','fn','expected','predicted','duplicate_predictions_removed']:section[k]+=c[k]
    return {'slices':{k:dict(v) for k,v in slices.items()},'categories':[{'coverage':k[0],'entity':k[1],**dict(v)} for k,v in sorted(rows.items())],
        'strict_entity_span_matching':True,'independent_accuracy_evidence':False,'representative_sample':False,'privacy_clearance':False}


def coverage(expected,applied,length):
    if type(length) is not int or not 0<=length<=2000:raise ValueError('Invalid recognition observations')
    truth=spans(expected,length);actual=spans(applied,length)
    if len(truth)!=len(expected):raise ValueError('Invalid recognition observations')
    wanted={i for _,start,end in truth for i in range(start,end)}
    masked={i for _,start,end in actual for i in range(start,end)}
    whole=sum(set(range(start,end))<=masked for _,start,end in truth)
    partial=sum(bool(set(range(start,end))&masked) and not set(range(start,end))<=masked for _,start,end in truth)
    return {'expected_spans':len(truth),'fully_masked_expected_spans':whole,'partially_masked_expected_spans':partial,
        'untouched_expected_spans':len(truth)-whole-partial,'expected_characters':len(wanted),
        'unmasked_expected_characters':len(wanted-masked),'masked_outside_expected_characters':len(masked-wanted),
        'masking_is_not_privacy_clearance':True}
