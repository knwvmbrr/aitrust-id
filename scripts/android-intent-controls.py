#!/usr/bin/env python3
"""Finite synthetic cross-UID Share ingress controls; never part of the checker APK."""
import hashlib
import io
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import time
import zipfile
import zlib

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from protocol.corpus import read_regular
from scripts.worker_process import run_worker

PACKAGE='com.aitrustid.android'
SENDER='com.aitrustid.synthetic'
SENDER_COMPONENT=SENDER+'/.SenderActivity'
MARKER='owned synthetic ingress marker'
HINT='Share text from another app, or paste it here.'
UNSUPPORTED='Share one plain-text item, up to 20,000 characters. Files and multiple items are not supported.'
RECEIVED='Text received. Review it, then tap Check.'
FIXTURES=('tests/android/intent-sender/AndroidManifest.xml','tests/android/intent-sender/SenderActivity.java')
CASES=('missing_text','wrong_typed_text','send_multiple','stream_extra','data_uri','clip_uri','multiple_clip_items','over_limit_text','unpaired_utf16')
SENDER_DEX=b'Lcom/aitrustid/synthetic/SenderActivity;'

class IntentControlRefusal(ValueError):
    STAGES=frozenset({'source','default_apk','build','install','uid','portrait','prime','send','refusal','recovery','cleanup'})
    def __init__(self,stage):
        if stage not in self.STAGES:raise ValueError('Invalid synthetic intent boundary')
        self.code='intent_'+stage+'_unavailable'
        super().__init__(self.code)


def dex_bytes(apk):
    raw=read_regular(Path(apk),64*1024*1024)
    if len(raw)<22:raise ValueError('Unsupported synthetic APK')
    tail=raw[-65557:];i=tail.rfind(b'PK\x05\x06')
    if i<0 or len(tail)-i<22:raise ValueError('Unsupported synthetic APK')
    _,disk,central,entries,count,size,offset,comment=struct.unpack('<4s4H2LH',tail[i:i+22])
    if not(disk==central==0 and entries==count and 1<=count<=64 and len(tail)-i==22+comment and offset+size==len(raw)-22-comment):raise ValueError('Unsupported synthetic APK')
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        rows=z.infolist();names=[r.filename for r in rows]
        if len(rows)!=count or len(set(names))!=count or any(r.orig_filename!=r.filename for r in rows) or sum(r.file_size for r in rows)>64*1024*1024:raise ValueError('Unsupported synthetic APK')
        members=[r for r in rows if '/' not in r.filename and r.filename.lower().endswith('.dex')]
        if not(1<=len(members)<=4 and sorted(r.filename for r in members)==['classes.dex','classes2.dex','classes3.dex','classes4.dex'][:len(members)] and sum(r.file_size for r in members)<=16*1024*1024):raise ValueError('Unsupported synthetic APK')
        return b''.join(z.read(r) for r in members)


def source_identity():
    return {name:hashlib.sha256(read_regular(ROOT/name,65536)).hexdigest() for name in (*FIXTURES,'scripts/android-intent-controls.py','scripts/verify-android-emulator.py','scripts/worker_process.py','protocol/corpus.py')}


def installed_uid(raw,package):
    if type(raw) is not bytes or len(raw)>4096:raise ValueError('Owned synthetic UID unavailable')
    lines=raw.decode('ascii').splitlines()
    matches=[re.fullmatch(r'package:'+re.escape(package)+r' uid:([0-9]{5,10})',line) for line in lines]
    if len(matches)!=1 or matches[0] is None:raise ValueError('Owned synthetic UID unavailable')
    value=int(matches[0].group(1))
    if not 10000<=value<=2147483647:raise ValueError('Owned synthetic UID unavailable')
    return value


def compile_sender(sdk,stage):
    """No downloads or caller-supplied code; bounded existing SDK/JDK commands."""
    sdk=Path(sdk);stage=Path(stage)
    java=Path(os.environ.get('JAVA_HOME_17_X64') or os.environ.get('JAVA_HOME','/nonexistent-jdk'))
    tools=sdk/'build-tools/36.0.0';platform=sdk/'platforms/android-36/android.jar'
    required=[java/'bin/java',java/'bin/javac',java/'bin/keytool',platform,*[tools/n for n in ('aapt2','d8','zipalign','apksigner')]]
    if not all(p.is_file() and not p.is_symlink() for p in required):raise ValueError('Installed synthetic build tools unavailable')
    sources=source_identity();deadline=time.monotonic()+120
    def command(args):
        left=deadline-time.monotonic()
        if left<=0:raise ValueError('Synthetic build deadline')
        result=run_worker(['/usr/bin/env','JAVA_HOME='+str(java),'PATH='+str(java/'bin')+os.pathsep+os.environ.get('PATH',''),*[str(a) for a in args]],input=b'',timeout=min(60,left),output_limit=262144)
        if result.returncode:raise ValueError('Synthetic build unavailable')
        return result.stdout
    classes=stage/'classes';dex=stage/'dex';classes.mkdir();dex.mkdir()
    base=stage/'resources.apk'
    command([tools/'aapt2','link','-o',base,'-I',platform,'--manifest',ROOT/FIXTURES[0]])
    command([java/'bin/javac','-encoding','UTF-8','--release','8','-classpath',platform,'-d',classes,ROOT/FIXTURES[1]])
    command([tools/'d8','--release','--min-api','29','--lib',platform,'--output',dex,*sorted(classes.rglob('*.class'))])
    apk=stage/'sender-unsigned.apk';shutil.copyfile(base,apk)
    with zipfile.ZipFile(apk,'a',compression=zipfile.ZIP_DEFLATED) as archive:
        for p in sorted(dex.glob('*.dex')):archive.write(p,p.name)
    aligned=stage/'sender-aligned.apk';signed=stage/'sender-ci-test.apk';key=stage/'sender-ci.p12'
    command([tools/'zipalign','-f','-P','16','4',apk,aligned])
    command([java/'bin/keytool','-genkeypair','-noprompt','-storetype','PKCS12','-keystore',key,'-alias','synthetic','-storepass','android','-keypass','android','-dname','CN=Owned Synthetic Share Test','-keyalg','RSA','-keysize','2048','-validity','1'])
    command([tools/'apksigner','sign','--ks',key,'--ks-key-alias','synthetic','--ks-pass','pass:android','--out',signed,aligned])
    command([tools/'apksigner','verify',signed]);key.unlink()
    permissions=command([tools/'aapt2','dump','permissions',signed]).decode('utf-8')
    if 'uses-permission:' in permissions or 'uses-permission-sdk-' in permissions:raise ValueError('Synthetic permission refused')
    if SENDER_DEX not in dex_bytes(signed):raise ValueError('Synthetic sender identity unavailable')
    if source_identity()!=sources:raise ValueError('Synthetic source changed')
    raw=read_regular(signed,1024*1024)
    return signed,{'variant':'synthetic-sender-only/v1','apk_sha256':hashlib.sha256(raw).hexdigest(),'apk_bytes':len(raw),'permission_count':0,'production_checker_modified':False,'sources':sources}


def observe(view):
    def own(rid):
        rows=[n for n in view.iter('node') if n.attrib.get('resource-id')==PACKAGE+':id/'+rid]
        if len(rows)>1:raise ValueError('Ambiguous owned synthetic UI')
        return rows[0] if rows else None
    editor,status,check=own('editor'),own('status'),own('check')
    value=None if editor is None else editor.attrib.get('text','')
    text=None if status is None else status.attrib.get('text','')
    return {'owned_editor_present':editor is not None,'owned_status_present':status is not None,
        'owned_check_present':check is not None,'editor_empty_or_exact_hint':value in ('',HINT),
        'editor_exact_synthetic_marker':value==MARKER,'received_status':text==RECEIVED,'unsupported_status':text==UNSUPPORTED,
        'check_enabled':None if check is None or check.attrib.get('enabled') not in ('true','false') else check.attrib['enabled']=='true',
        'result_tag_present':own('tag') is not None,'result_details_present':own('details') is not None}


def verify_cases(send,wait,report):
    """Finite invalid/recovery pairs; only fixed boolean observations are retained."""
    cases=[];report.update(status='RUNNING',**{'pass':False},cases=cases)
    def observed(view):
        value=observe(view);report['last_observation']=value
        # Refuse any exposed result immediately, even if later snapshots clear it.
        if value['result_tag_present'] or value['result_details_present']:raise ValueError('Unexpected synthetic result')
        return value
    def valid(view):
        value=observed(view)
        return value['owned_editor_present'] and value['owned_status_present'] and value['owned_check_present'] and value['editor_exact_synthetic_marker'] and value['received_status'] and value['check_enabled'] is True
    def refused(view):
        value=observed(view)
        return value['owned_editor_present'] and value['owned_status_present'] and value['owned_check_present'] and value['editor_empty_or_exact_hint'] and value['unsupported_status'] and value['check_enabled'] is False
    try:
        report['control_stage']='prime';send(0);wait(valid)
        for selection,name in enumerate(CASES,1):
            report['case']=name;report['control_stage']='send';send(selection)
            report['control_stage']='refusal';wait(refused)
            # Each invalid state must precede a fresh exact accepted Share.
            report['control_stage']='recovery';send(0);wait(valid)
            cases.append({'case':name,'refused':True,'fresh_valid_recovery':True,'pass':True})
        report.update(status='EXECUTED',**{'pass':True},case_count=len(cases))
    except (OSError,ValueError,KeyError,TypeError,AttributeError,AssertionError,StopIteration,subprocess.SubprocessError,RuntimeError,zipfile.BadZipFile,zlib.error,EOFError):
        report.update(status='FAILED',case_count=len(cases))
        raise IntentControlRefusal(report['control_stage']) from None


def run_controls(sdk,checker_apk,install,shell,wait,report):
    report.update(status='RUNNING',**{'pass':False},cases=[])
    stage='source'
    try:
        sources=source_identity();stage='default_apk'
        if SENDER_DEX in dex_bytes(checker_apk):raise ValueError('Sender leaked into checker')
        report['default_checker_excludes_sender']=True
        stage='build'
        with tempfile.TemporaryDirectory(prefix='aitrust-synthetic-sender-',dir=os.environ['RUNNER_TEMP']) as temporary:
            os.chmod(temporary,0o700)
            apk,build=compile_sender(sdk,Path(temporary));report['sender_build']=build
            stage='install';install(apk)
            stage='uid'
            original=installed_uid(shell(['pm','list','packages','-U',PACKAGE]),PACKAGE)
            sender=installed_uid(shell(['pm','list','packages','-U',SENDER]),SENDER)
            if original==sender:raise ValueError('Sender UID isolation unavailable')
            report['different_application_uid']=True
            stage='portrait'
            if shell(['wm','user-rotation']).strip()!=b'lock 0':raise ValueError('Owned portrait precondition unavailable')
            def send(selection):
                if type(selection) is not int or not 0<=selection<=9:raise ValueError('Invalid synthetic selection')
                shell(['am','start','-W','-n',SENDER_COMPONENT,'--ei','selection',str(selection)],20)
            verify_cases(send,wait,report)
            stage='source'
            if source_identity()!=sources:raise ValueError('Synthetic source changed')
            report['source_stable']=True
            stage='cleanup'
        return report
    except IntentControlRefusal:raise
    except (OSError,ValueError,KeyError,TypeError,AttributeError,AssertionError,StopIteration,subprocess.SubprocessError,RuntimeError,zipfile.BadZipFile,zlib.error,EOFError):
        report.update(status='FAILED',**{'pass':False})
        raise IntentControlRefusal(stage) from None
