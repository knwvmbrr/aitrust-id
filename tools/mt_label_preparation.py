"""Candidate MT annotation preparation, never detector, human truth or release."""
import copy
import hashlib
import json
import math
from pathlib import Path
import random
from protocol.normalization import normalize_nfc, NORMALIZATION_ID
from tools.reviewer_agreement import nominal_agreement
from tools.mt_label_io import Capture, Refused, need, MAX_BYTES

ROOT=Path(__file__).absolute().parents[1]
PROFILE='mt-label-preparation/1.0.0'
INPUT_LIMIT=2*1024*1024
UNCERTAIN={'uncertain','insufficient_context'}
AXES={
 'pressure':['contextual_pressure','legitimate_urgency','ordinary_persuasion','no_relevant_pressure','uncertain','insufficient_context'],
 'choice':['binary_omits_alternative','legitimately_limited_choice','no_binary_frame','uncertain','insufficient_context'],
 'authority':['unattributed_authority_appeal','attributed_unverified','no_authority_appeal','uncertain','insufficient_context'],
 'use_context':['used','quoted_or_mentioned','mixed','no_relevant_cue','uncertain','insufficient_context']}
FLAGS={'predictions_run':False,'human_labels_verified':False,'independence_verified':False,
       'sampling_accepted':False,'protocol_adopted':False,'accuracy_assessed':False,
       'category_errors_assessed':False,'calibration_assessed':False,'release_approved':False,
       'mt_tag_issued':False,'useful_interpretation_established':False}
SOURCES=('tools/mt_label_preparation.py','tools/mt_label_io.py','scripts/mt-label-preparation.py',
         'tools/reviewer_agreement.py','protocol/normalization.py','protocol/unicode15-data.json',
         'docs/mt-annotation-guide.md','LICENSE','NOTICE')


def sha(raw):return hashlib.sha256(raw).hexdigest()


def encode(value,limit=INPUT_LIMIT):
    chunks=bytearray()
    for chunk in json.JSONEncoder(ensure_ascii=False,allow_nan=False,sort_keys=True,separators=(',',':')).iterencode(value):
        raw=chunk.encode('utf-8','strict');need(len(raw)<=limit-1-len(chunks));chunks.extend(raw)
    return bytes(chunks)+b'\n'


def decode(raw,limit=INPUT_LIMIT):
    need(type(raw) is bytes and 0<len(raw)<=limit)
    def unique(pairs):
        value={}
        for key,item in pairs:need(key not in value);value[key]=item
        return value
    try:
        value=json.loads(raw.decode('utf-8','strict'),object_pairs_hook=unique,
            parse_constant=lambda _:(_ for _ in ()).throw(Refused()))
        pending=[(value,0)];nodes=0
        while pending:
            item,depth=pending.pop();nodes+=1;need(nodes<=100000 and depth<=24)
            if type(item) in (dict,list):
                children=item.values() if type(item) is dict else item
                need(len(item)<=2048);pending.extend((x,depth+1) for x in children)
            elif type(item) is str:text(item,32000,empty=True)
            elif type(item) is float:need(math.isfinite(item))
        return value
    except (ValueError,UnicodeError,RecursionError):raise Refused() from None


def text(value,limit,empty=False):
    need(type(value) is str and len(value)<=limit and (empty or bool(value.strip()))
         and all(ord(c)>=32 or c in '\t\n\r' for c in value))
    value.encode('utf-8','strict');return value


def identity(raw):
    normal=normalize_nfc(raw);need(len(normal)<=8000)
    return normal,{'raw_sha256':sha(raw.encode()),'raw_codepoints':len(raw),
                   'normalized_sha256':sha(normal.encode()),'normalized_codepoints':len(normal),
                   'normalization':NORMALIZATION_ID}


def source_state(capture):
    return {p:sha(capture.read(ROOT/p,INPUT_LIMIT,private=False)) for p in SOURCES}


def prepared(raw,sources):
    source=decode(raw);need(type(source) is dict and set(source)=={'profile','language','items'}
                           and source['profile']=='mt-label-items/v1' and source['language']=='en')
    need(type(source['items']) is list and 1<=len(source['items'])<=256)
    items=[];seen=set()
    for index,row in enumerate(source['items']):
        need(type(row) is dict and set(row)=={'id','text','context'})
        identifier=text(row['id'],100);need(identifier not in seen);seen.add(identifier)
        subject,subject_identity=identity(text(row['text'],8000))
        context,context_identity=identity(text(row['context'],8000,empty=True))
        items.append({'id':'Unit'+str(index+1).zfill(4),'text':subject,'context':context,
                      'text_identity':subject_identity,'context_identity':context_identity})
    rubric={'profile':PROFILE,'status':'candidate_unadopted','axes':copy.deepcopy(AXES),
            'span_units':'NFC_Unicode_codepoints','context':'caller_selected_unverified',**FLAGS}
    content=encode(items)
    manifest={'profile':PROFILE,'language':'en','item_count':len(items),'input_sha256':sha(raw),
              'items_sha256':sha(content),'rubric_sha256':sha(encode(rubric)),
              'sources':sources,'context_truth_verified':False,**FLAGS}
    return items,rubric,manifest


def blank(items,manifest,slot):
    order=copy.deepcopy(items);random.SystemRandom().shuffle(order)
    return {'profile':PROFILE,'slot':slot,'manifest_sha256':sha(encode(manifest)),
            'items':[dict(item,annotations={axis:{'label':None,'reason':'','text_spans':[],'context_spans':[]}
                                          for axis in AXES}) for item in order]}


def packet_files(items,rubric,manifest,guide):
    return {'items.json':encode(items),'rubric.json':encode(rubric),'manifest.json':encode(manifest),
            'reviewer-A.json':encode(blank(items,manifest,'A')),
            'reviewer-B.json':encode(blank(items,manifest,'B')),'guide.md':guide}


def freeze(source,destination):
    with Capture() as capture:
        sources=source_state(capture);raw=capture.read(source,INPUT_LIMIT)
        items,rubric,manifest=prepared(raw,sources)
        guide=capture.read(ROOT/'docs/mt-annotation-guide.md',100000,private=False)
        files=packet_files(items,rubric,manifest,guide)
        need(sum(map(len,files.values()))<=MAX_BYTES)
        capture.check();capture.create(destination,files);capture.check()
        result={'state':'PREPARED','item_count':len(items),'reviewer_forms':2,**FLAGS}
    return result


def load_packet(capture,source,packet):
    sources=source_state(capture);raw=capture.read(source,INPUT_LIMIT)
    capture.packet_members(packet,{'items.json','rubric.json','manifest.json','guide.md','reviewer-A.json','reviewer-B.json'})
    items,rubric,manifest=prepared(raw,sources)
    for name,expected in [('items.json',items),('rubric.json',rubric),('manifest.json',manifest)]:
        actual=capture.read(Path(packet)/name,INPUT_LIMIT)
        need(actual==encode(expected))
    need(capture.read(Path(packet)/'guide.md',100000)==capture.read(ROOT/'docs/mt-annotation-guide.md',100000,private=False))
    return items,manifest


def spans(value,size):
    need(type(value) is list and len(value)<=8)
    previous=-1
    for span in value:
        need(type(span) is list and len(span)==2 and all(type(x) is int for x in span)
             and 0<=span[0]<span[1]<=size and span[0]>=previous)
        previous=span[1]
    return value


def response(raw,items,manifest,slot):
    value=decode(raw);need(type(value) is dict and set(value)=={'profile','slot','manifest_sha256','items'}
        and value['profile']==PROFILE and value['slot']==slot and value['manifest_sha256']==sha(encode(manifest))
        and type(value['items']) is list and len(value['items'])==len(items))
    originals={item['id']:item for item in items};ratings={}
    for row in value['items']:
        need(type(row) is dict and set(row)=={*items[0],'annotations'} and type(row.get('id')) is str
             and row['id'] in originals and row['id'] not in ratings)
        original=originals[row['id']]
        need(encode({k:row[k] for k in original})==encode(original))
        annotations=row['annotations'];need(type(annotations) is dict and set(annotations)==set(AXES))
        for axis,record in annotations.items():
            need(type(record) is dict and set(record)=={'label','reason','text_spans','context_spans'}
                 and type(record['label']) is str and record['label'] in AXES[axis])
            text(record['reason'],1000)
            subject=spans(record['text_spans'],len(original['text']))
            context=spans(record['context_spans'],len(original['context']))
            negative={'no_relevant_pressure','no_binary_frame','no_authority_appeal','no_relevant_cue'}
            if record['label'] not in UNCERTAIN|negative:need(bool(subject))
            if record['label']=='binary_omits_alternative':need(bool(context))
        ratings[row['id']]=copy.deepcopy(annotations)
    need(set(ratings)==set(originals));return ratings


def validate(source,packet,returned,slot):
    need(type(slot) is str and slot in ('A','B'))
    with Capture() as capture:
        items,manifest=load_packet(capture,source,packet)
        response(capture.read(returned,INPUT_LIMIT),items,manifest,slot);capture.check()
        result={'state':'RESPONSE_COMPLETE','item_count':len(items),'axis_count':len(AXES),**FLAGS}
    return result


def agreement(items,first,second):
    matrices={};summaries={};queue=[]
    for axis,categories in AXES.items():
        matrix={'schema_version':1,'kind':'nominal_agreement_ratings','target_tag':'MT',
            'reviewers':['RaterA','RaterB'],'categories':copy.deepcopy(categories),
            'units':[{'id':row['id'],'ratings':{'RaterA':first[row['id']][axis]['label'],
                    'RaterB':second[row['id']][axis]['label']}} for row in items]}
        summary=nominal_agreement(matrix)
        supplied=[v for unit in matrix['units'] for v in unit['ratings'].values()]
        decisive=sum(v not in UNCERTAIN for v in supplied)
        both=sum(all(v not in UNCERTAIN for v in u['ratings'].values()) for u in matrix['units'])
        summary['coverage']={'uncertain_rating_count':supplied.count('uncertain'),
            'insufficient_context_rating_count':supplied.count('insufficient_context'),
            'decisive_rating_count':decisive,'supplied_rating_count':len(supplied),
            'decisive_rating_fraction':{'numerator':decisive,'denominator':len(supplied)},
            'joint_decisive_unit_count':both,'unit_count':len(items)}
        summary['candidate_comparison']='UNADOPTED_CANDIDATE_ONLY'
        matrices[axis]=matrix;summaries[axis]=summary
    for item in items:
        unit=item['id']
        axes=[axis for axis in AXES if first[unit][axis]['label']!=second[unit][axis]['label']
              or first[unit][axis]['label'] in UNCERTAIN or second[unit][axis]['label'] in UNCERTAIN]
        if axes:queue.append({'item':item,'axes_requiring_review':axes,'supplied_A':first[unit], 'supplied_B':second[unit],
                             'adjudicated_label':None,'human_adjudication_verified':False})
    return summaries,matrices,queue


def compare(source,packet,first_path,second_path,destination):
    with Capture() as capture:
        items,manifest=load_packet(capture,source,packet)
        first=response(capture.read(first_path,INPUT_LIMIT),items,manifest,'A')
        second=response(capture.read(second_path,INPUT_LIMIT),items,manifest,'B')
        summaries,matrices,queue=agreement(items,first,second)
        result={'profile':PROFILE,'state':'COMPLETE','item_count':len(items),'supplied_rater_slots':2,
                'axes':summaries,'private_review_queue_count':len(queue),
                'meaning':'Completed supplied-label processing, not MT agreement/accuracy/release acceptance.',**FLAGS}
        files={'agreement.json':encode(result),'matrices.json':encode(matrices),
               'review-queue.json':encode({'profile':PROFILE,'source_manifest_sha256':sha(encode(manifest)),
                                          'items':queue,**FLAGS},MAX_BYTES)}
        need(sum(map(len,files.values()))<=MAX_BYTES)
        capture.check();capture.create(destination,files);capture.check()
    return result
