"""Refuse unsafe prerequisites without accepting SDK terms or booting a device."""
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
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


if __name__=='__main__':unittest.main()
