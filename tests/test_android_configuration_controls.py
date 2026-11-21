"""Supplemental configuration-driver fault controls; not Android runtime evidence."""
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('configuration_driver',ROOT/'scripts/verify-android-emulator.py')
driver=importlib.util.module_from_spec(spec);spec.loader.exec_module(driver)


class ConfigurationControls(unittest.TestCase):
    def exercise(self,fault=None):
        report={};calls=[]
        def shell(args):
            calls.append(('shell',args))
            if args[:2]==['am','task'] and fault=='refocus':raise OSError('PRIVATE_NATIVE_CANARY')
            if args==['dumpsys','activity','activities']:return b'Task{owned #42 com.aitrustid.android}\n'
            return b''
        def send(value):calls.append(('send',value))
        def click(view,rid):calls.append(('click',rid))
        def wait(predicate):
            stage=report['control_stage'];child=report.get('background',{}).get('control_stage')
            calls.append(('wait',stage,child))
            rotation='0';status='Cleared. Your text and result are no longer shown.';value=''
            if stage=='configuration_receive':status='Text received. Review it';value='owned configuration draft'
            elif stage=='configuration_edit':value='owned configuration draftX';status='Text changed. Tap Check'
            elif stage=='configuration_rotate':
                rotation='1';status='Text received. Review it';value='owned configuration draftX'
                if fault=='lost_edit':value='owned configuration draft'
            elif stage=='configuration_home' and child=='background_receive':
                rotation='1';status='Text received. Review it';value='synthetic private marker'
            elif stage=='configuration_home' and child=='background_cleared_view':
                if fault=='immediate_revival':value='synthetic private marker'
            elif stage=='configuration_final_rotation' and fault=='late_revival':
                rotation='1';value='synthetic private marker'
            view=ET.Element('hierarchy',{'rotation':rotation})
            ET.SubElement(view,'node',{'resource-id':driver.PACKAGE+':id/editor','text':value})
            ET.SubElement(view,'node',{'resource-id':driver.PACKAGE+':id/status','text':status})
            if fault=='automatic_result' and stage=='configuration_rotate':ET.SubElement(view,'node',{'resource-id':driver.PACKAGE+':id/tag','text':'PS'})
            if fault=='missing_editor' and stage=='configuration_edit':view.remove(view[0])
            if not predicate(view):raise ValueError('Synthetic bound expired')
            return view
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
            self.assertEqual(error.code,'configuration_edit_unavailable' if fault=='missing_editor' else 'configuration_restore_unavailable')

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


if __name__=='__main__':unittest.main()
