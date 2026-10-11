"""Nominal agreement over supplied labels; not accuracy or independent human evidence."""
from collections import Counter
from fractions import Fraction
import re

METHOD='krippendorff-nominal/1.0.0'
ALIAS=re.compile(r'[A-Za-z][A-Za-z0-9_-]{0,31}')
CANDIDATE_MINIMUM=Fraction(55,100)

def require(ok):
    if not ok:raise ValueError('Invalid agreement matrix')

def exact(obj,keys):
    return isinstance(obj,dict) and set(obj)==set(keys)

def nominal_agreement(data):
    require(exact(data,['schema_version','kind','target_tag','reviewers','categories','units']))
    require(type(data['schema_version']) is int and data['schema_version']==1 and data['kind']=='nominal_agreement_ratings' and data['target_tag']=='MT')
    reviewers,categories,units=data['reviewers'],data['categories'],data['units']
    for values,low,high in [(reviewers,2,32),(categories,2,16)]:
        require(isinstance(values,list) and low<=len(values)<=high)
        require(all(isinstance(v,str) and ALIAS.fullmatch(v) for v in values))
        require(len(values)==len(set(values)))
    require(isinstance(units,list) and 1<=len(units)<=2048)
    seen=set();totals=Counter();coincidences=[[Fraction(0) for _ in categories] for _ in categories]
    category_index={name:i for i,name in enumerate(categories)}
    paired_units=0;unpaired_units=0;missing=0;disputed=0;all_present=0
    for unit in units:
        require(exact(unit,['id','ratings']) and isinstance(unit['id'],str) and ALIAS.fullmatch(unit['id']))
        require(unit['id'] not in seen);seen.add(unit['id'])
        ratings=unit['ratings'];require(exact(ratings,reviewers))
        require(all(v is None or isinstance(v,str) and v in category_index for v in ratings.values()))
        counts=Counter(category_index[v] for v in ratings.values() if v is not None)
        size=sum(counts.values());missing+=len(reviewers)-size;all_present+=size
        if size<2:unpaired_units+=1;continue
        paired_units+=1;disputed+=len(counts)>1;totals.update(counts)
        for c,nc in counts.items():
            for k,nk in counts.items():
                coincidences[c][k]+=Fraction(nc*(nk-(c==k)),size-1)
    n=sum(totals.values());observed=expected=alpha=None
    if n:
        observed=sum((coincidences[c][k] for c in range(len(categories)) for k in range(len(categories)) if c!=k),Fraction(0))/n
        expected=Fraction(n*n-sum(v*v for v in totals.values()),n*(n-1))
        if expected:alpha=1-observed/expected
    reason='no_pairable_ratings' if n==0 else 'no_category_variation' if not expected else None
    def ratio(value):return None if value is None else {'value':float(value),'exact_fraction':f'{value.numerator}/{value.denominator}'}
    return {'schema_version':1,'kind':'nominal_agreement_summary','method':METHOD,'target_tag':'MT',
        'state':'AVAILABLE' if alpha is not None else 'UNAVAILABLE','reason':reason,'reviewer_count':len(reviewers),
        'unit_count':len(units),'pairable_unit_count':paired_units,'unpaired_unit_count':unpaired_units,
        'missing_rating_count':missing,'supplied_rating_count':all_present,'pairable_rating_count':n,
        'disputed_pairable_unit_count':disputed,'category_counts':[totals[i] for i in range(len(categories))],
        'observed_disagreement':ratio(observed),'expected_disagreement':ratio(expected),'alpha':ratio(alpha),
        'candidate_minimum':float(CANDIDATE_MINIMUM),'candidate_met':alpha is not None and alpha>=CANDIDATE_MINIMUM,
        'candidate_is_adopted':False,'confidence_interval':None,'independence_verified':False,
        'accuracy_evidence':False,'release_approved':False,'collection_performed':False,
        'private_input_identifiers_exported':False}
