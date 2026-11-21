"""Supplemental configuration-driver fault controls; not Android runtime evidence."""
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import textwrap
import unittest
from unittest import mock
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('configuration_driver',ROOT/'scripts/verify-android-emulator.py')
driver=importlib.util.module_from_spec(spec);spec.loader.exec_module(driver)


class ConfigurationControls(unittest.TestCase):
    def exercise(self,fault=None):
        report={};calls=[];scroll_position=0
        def shell(args,timeout=10):
            nonlocal scroll_position
            calls.append(('shell',args))
            if args[:2]==['input','swipe']:
                scroll_position=max(0,scroll_position+(1 if args[3]>args[5] else -1))
            if args[:2]==['am','task'] and fault=='refocus':raise OSError('PRIVATE_NATIVE_CANARY')
            if args==['dumpsys','activity','activities']:return b'Task{owned #42 com.aitrustid.android}\n'
            return b''
        def send(value):calls.append(('send',value))
        def click(view,rid):calls.append(('click',rid))
        def snapshot():
            stage=report['control_stage'];child=report.get('background',{}).get('control_stage')
            rotation='0';status='Cleared. Your text and result are no longer shown.';value=''
            show_editor=True;show_status=True
            if stage=='configuration_receive':status='Text received. Review it';value='owned configuration draft'
            elif stage=='configuration_edit':value='owned configuration draftX';status='Text changed. Tap Check'
            elif stage=='configuration_rotate':
                rotation='1';status='Text received. Review it';value='owned configuration draftX'
                if fault=='lost_edit':value='owned configuration draft'
                if fault in ('offscreen','no_receipt','lost_after_scroll','bad_scroll_bounds','foreign_scroll'):
                    show_status=scroll_position>0 and fault!='no_receipt';show_editor=scroll_position==0
                    if fault=='lost_after_scroll' and report.get('rotation_receipt_observed') and scroll_position==0:value='owned configuration draft'
            elif stage=='configuration_home' and child=='background_receive':
                rotation='1';status='Text received. Review it';value='synthetic private marker'
            elif stage=='configuration_home' and child=='background_cleared_view':
                if fault=='immediate_revival':value='synthetic private marker'
            elif stage=='configuration_final_rotation' and fault=='late_revival':
                rotation='1';value='synthetic private marker'
            view=ET.Element('hierarchy',{'rotation':rotation})
            if show_editor:ET.SubElement(view,'node',{'resource-id':driver.PACKAGE+':id/editor','text':value})
            if show_status:ET.SubElement(view,'node',{'resource-id':driver.PACKAGE+':id/status','text':status})
            ET.SubElement(view,'node',{'class':'android.widget.ScrollView','package':'other.invalid' if fault=='foreign_scroll' else driver.PACKAGE,
                'bounds':'PRIVATE_BOUNDS_CANARY' if fault=='bad_scroll_bounds' else '[0,0][800,400]'})
            if fault=='automatic_result' and stage=='configuration_rotate':ET.SubElement(view,'node',{'resource-id':driver.PACKAGE+':id/tag','text':'PS'})
            if fault=='missing_editor' and stage=='configuration_edit':view.remove(view[0])
            return view
        def wait(predicate):
            stage=report['control_stage'];child=report.get('background',{}).get('control_stage')
            calls.append(('wait',stage,child))
            for _ in range(8 if stage=='configuration_rotate' else 1):
                view=snapshot()
                if predicate(view):return view
            raise ValueError('Synthetic bound expired')
        try:driver.verify_configuration_controls(send,shell,wait,click,report)
        except driver.AndroidConfigurationRefusal as error:return report,calls,error
        return report,calls,None

    def test_both_distinct_supplemental_cases_and_no_wait_between_rotate_and_home(self):
        report,calls,error=self.exercise();self.assertIsNone(error)
        self.assertEqual(report['status'],'EXECUTED');self.assertTrue(report['pass']);self.assertEqual(report['case_count'],2)
        self.assertEqual([r['case'] for r in report['cases']],['configuration_preserves_current_edited_review_without_result','configuration_immediate_home_refocus_does_not_revive_text'])
        last_rotation=max(i for i,c in enumerate(calls) if c==('shell',['wm','user-rotation','lock','0']))
        self.assertEqual(calls[last_rotation+1],('shell',['input','keyevent','KEYCODE_HOME']))
        self.assertEqual(calls[last_rotation+2],('shell',['dumpsys','activity','activities']))
        self.assertEqual(calls[last_rotation+3],('shell',['am','task','focus','42']))
        self.assertFalse(any(c[0]=='send' for c in calls[last_rotation:]))
        self.assertNotIn('owned configuration draft',json.dumps(report))
        self.assertNotIn('synthetic private marker',json.dumps(report))

    def test_current_edited_text_and_absent_result_are_required(self):
        for fault in ('lost_edit','automatic_result','missing_editor'):
            report,calls,error=self.exercise(fault)
            self.assertIsNotNone(error);self.assertFalse(report['pass']);self.assertEqual(report['status'],'FAILED')
            self.assertEqual(report['case_count'],0)
            self.assertEqual(error.code,'configuration_edit_unavailable' if fault=='missing_editor' else 'configuration_rotate_unavailable')

    def test_offscreen_status_uses_bounded_owned_scroll_with_one_rotation_wait(self):
        report,calls,error=self.exercise('offscreen');self.assertIsNone(error)
        self.assertTrue(report['pass']);self.assertEqual(report['rotation_scroll_actions'],2)
        self.assertTrue(report['rotation_receipt_observed'] and report['rotation_edited_reasserted'])
        self.assertEqual(report['rotation_scroll_precondition'],{'rotation':'1','editor_observed':True,'editor_matches_edited_draft':True,
            'status_node_observed':False,'received_status_visible':False,'result_tag_visible':False})
        self.assertEqual(sum(c[0]=='wait' and c[1]=='configuration_rotate' for c in calls),1)
        self.assertTrue(report['rotation_observation']['editor_matches_edited_draft'])
        self.assertNotIn('owned configuration draft',json.dumps(report))

    def test_missing_receipt_or_edited_text_after_scroll_cannot_be_salvaged(self):
        for fault in ('no_receipt','lost_after_scroll'):
            report,calls,error=self.exercise(fault)
            self.assertEqual(error.code,'configuration_rotate_unavailable');self.assertFalse(report['pass']);self.assertEqual(report['case_count'],0)
            self.assertLessEqual(report['rotation_scroll_actions'],4)
            if fault=='no_receipt':self.assertIsNone(report['rotation_observation']['editor_matches_edited_draft'])

    def test_unknown_bounds_or_foreign_scroll_view_cannot_receive_gesture(self):
        for fault in ('bad_scroll_bounds','foreign_scroll'):
            report,calls,error=self.exercise(fault)
            self.assertIsNotNone(error);self.assertFalse(any(c[0]=='shell' and c[1][:2]==['input','swipe'] for c in calls))
            self.assertNotIn('PRIVATE',json.dumps(report)+str(error))

    def test_immediate_and_late_revival_fail_without_waiting_for_later_clear(self):
        for fault in ('immediate_revival','late_revival'):
            report,calls,error=self.exercise(fault)
            self.assertEqual(report['status'],'FAILED');self.assertFalse(report['pass']);self.assertEqual(report['case_count'],1)
            self.assertEqual(error.code,'configuration_home_unavailable' if fault=='immediate_revival' else 'configuration_final_rotation_unavailable')
            if fault=='late_revival':self.assertEqual(sum(c[0]=='wait' and c[1]=='configuration_final_rotation' for c in calls),1)

    def test_nested_background_fault_is_failed_and_does_not_echo_native_error(self):
        report,calls,error=self.exercise('refocus')
        self.assertEqual(report['status'],'FAILED');self.assertFalse(report['pass'])
        self.assertEqual(report['background']['control_stage'],'background_refocus')
        self.assertEqual(error.code,'configuration_home_unavailable')
        self.assertNotIn('PRIVATE_',json.dumps(report)+str(error))

    def test_combined_probe_and_default_configuration_request_refuses_before_sdk(self):
        with tempfile.TemporaryDirectory() as t,mock.patch.object(driver,'ROOT',Path(t)),mock.patch.object(sys,'argv',['verify','--sdk-root','PRIVATE_SDK','--apk','PRIVATE_APK','--intake-probe','--configuration-controls']),mock.patch.object(driver,'prepare_emulator',side_effect=AssertionError('No SDK access')) as prepare,mock.patch('sys.stdout',new_callable=io.StringIO) as output:
            self.assertEqual(driver.main(),1);prepare.assert_not_called()
        report=json.loads(output.getvalue());self.assertEqual(report['diagnostic_code'],'configuration_default_variant_unavailable')
        self.assertEqual(report['cases'],[]);self.assertNotIn('PRIVATE_',output.getvalue())

    def test_automatic_and_manual_configuration_mapping_use_identical_actual_shell_args(self):
        source=(ROOT/'.github/workflows/android-share.yml').read_text()
        expression="AITRUST_CONFIGURATION_CONTROLS: ${{ (github.event_name != 'workflow_dispatch' || inputs.configuration_controls) && '1' || '0' }}"
        self.assertEqual(source.count(expression),1)
        block=source.split('      - name: Verify Share on a disposable API 36 emulator when hosted prerequisites permit\n',1)[1].split('      - name: Preserve engineering evidence',1)[0]
        script=textwrap.dedent(block[block.index('          probe_args=()'):])
        results={}
        for event,probe,explicit in [('pull_request',False,False),('push',False,False),('workflow_dispatch',False,True),('workflow_dispatch',False,False),('workflow_dispatch',True,False),('workflow_dispatch',True,True)]:
            config=event!='workflow_dispatch' or explicit
            env={'PATH':os.defpath,'ANDROID_SDK_ROOT':'SYNTHETIC_SDK','AITRUST_INTAKE_PROBE':'1' if probe else '0','AITRUST_CONFIGURATION_CONTROLS':'1' if config else '0'}
            result=subprocess.run(['bash','-c',"python3() { printf '%s\\n' \"$@\"; }\n"+script],env=env,capture_output=True,timeout=5)
            self.assertEqual(result.returncode,0,result.stderr.decode());args=result.stdout.decode().splitlines()
            self.assertEqual('--configuration-controls' in args,config);self.assertEqual('--intake-probe' in args,probe)
            results[(event,probe,explicit)]=args
        self.assertEqual(results[('pull_request',False,False)],results[('workflow_dispatch',False,True)])
        self.assertEqual(results[('push',False,False)],results[('workflow_dispatch',False,True)])


if __name__=='__main__':unittest.main()
