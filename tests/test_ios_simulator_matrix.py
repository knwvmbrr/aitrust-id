"""Inert identity/ownership controls only; never SDK or Simulator execution."""
import json
import io
import contextlib
import runpy
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tools import ios_simulator_matrix as m

class MatrixControls(unittest.TestCase):
    def test_profiles_and_exact_runtime(self):
        for profile in m.PROFILES:
            value={'runtimes':[{'identifier':m.RUNTIME,'isAvailable':True,'version':'26.2','buildversion':'23C54','supportedDeviceTypes':[{'identifier':m.profile_type(profile),'productFamily':'iPhone'}]}]}
            self.assertEqual(m.runtime_profile(json.dumps(value).encode(),profile),m.profile_type(profile))
            for field,val in [('isAvailable',False),('version','27.2'),('buildversion','unknown')]:
                changed=json.loads(json.dumps(value));changed['runtimes'][0][field]=val
                with self.assertRaises(m.Unavailable):m.runtime_profile(json.dumps(changed).encode(),profile)
        with self.assertRaises(m.Unavailable):m.profile_type('booted')
    def test_exact_accepted_toolchain(self):
        self.assertEqual(m.toolchain_identity(b'Xcode 27.2\nBuild version 27B52',b'27.2')['xcode_build'],'27B52')
        for version,sdk in [(b'Xcode 28',b'27.2'),(b'Xcode 27.2\nBuild version 27B52',b'28')]:
            with self.assertRaises(m.Unavailable):m.toolchain_identity(version,sdk)
    def test_duplicate_missing_device_refuse(self):
        row={'identifier':m.RUNTIME,'isAvailable':True,'version':'26.2','buildversion':'23C54','supportedDeviceTypes':[]}
        for runtime in [[row],[row,row]]:
            with self.assertRaises(m.Unavailable):m.runtime_profile(json.dumps({'runtimes':runtime}).encode(),'small')
    def test_derived_payload_exact_one_delta(self):
        old=m.read_fixed(m.ROOT/'mobile/ios/Tests/UIFlows.swift',262144);fixture=m.read_fixed(m.ROOT/'mobile/ios/Tests/SizeLayoutFlows.swift',65536)
        original={'Tests/UIFlows.swift':old,**{f'x{i}':str(i).encode()for i in range(45)}}
        derived,proof=m.derive_payload(original,fixture);self.assertEqual(proof['changed_members'],['Tests/UIFlows.swift']);self.assertEqual(len([n for n in original if derived[n]==original[n]]),45);self.assertEqual(original['Tests/UIFlows.swift'],old)
        with self.assertRaises(m.Unavailable):m.derive_payload(original,fixture+b' ')
        with self.assertRaises(m.Unavailable):m.derive_payload({**original,'Tests/UIFlows.swift':b'changed'},fixture)
        with self.assertRaises(m.Unavailable):m.derive_payload({**original,'extra':b'X'},fixture)
    def test_budget_downward_and_original_cleanup(self):
        clock=[100.0];b=m.Budget(lambda:clock[0]);self.assertEqual(b.seconds(600),600);clock[0]=b.work_end-8;self.assertEqual(b.seconds(600),3)
        with self.assertRaises(m.Unavailable):clock[0]=b.work_end;b.seconds(1)
        self.assertEqual(b.seconds(90,cleanup=True),90);clock[0]=b.end-4
        with self.assertRaises(m.Unavailable):b.seconds(90,cleanup=True)
    def test_ui_aggregate_not_reset(self):
        clock=[0.0];b=m.Budget(lambda:clock[0]);b.begin_ui();clock[0]=775
        with self.assertRaises(m.Unavailable):b.seconds(300,ui=True)
    def test_exact_one_named_test(self):
        owned='11111111-2222-4333-8444-555555555555';device={'deviceId':owned,'modelName':'iPhone SE (3rd generation)','osVersion':'26.2','osBuildNumber':m.BUILD,'platform':'iOS Simulator','architecture':'arm64'}
        summary={'result':'Passed','totalTestCount':1,'passedTests':1,'failedTests':0,'skippedTests':0,'devicesAndConfigurations':[{'device':device}]};tree={'devices':[device],'testNodes':[{'nodeType':'Test Case','nodeIdentifier':m.TEST_ID,'result':'Passed'}]};accepted=lambda a,b:m.accepted(a,b,owned=owned,profile='small');self.assertTrue(accepted(summary,tree))
        for k,v in [('totalTestCount',0),('skippedTests',1),('passedTests',True)]:self.assertFalse(accepted({**summary,k:v},tree))
        self.assertFalse(accepted(summary,{**tree,'testNodes':[]}));self.assertFalse(accepted(summary,{**tree,'testNodes':tree['testNodes']*2}));self.assertFalse(accepted(summary,{**tree,'testNodes':[{'nodeType':'Test Case','nodeIdentifier':'UIFlows/testOther()','result':'Passed'}]}))
        self.assertFalse(m.accepted(summary,tree,owned='other',profile='small'));self.assertFalse(m.accepted(summary,tree,owned=owned,profile='max'));self.assertFalse(accepted(summary,{**tree,'devices':[]}))
    def test_cleanup_attempts_absence_after_delete_failure(self):
        calls=[]
        def command(argv,cap,stage,cleanup):
            calls.append((argv,cap,stage,cleanup))
            if stage=='delete':raise m.Unavailable()
            return {'stdout':b'{}'}
        result=m.cleanup_owned('owned',command,lambda raw,owned:True);self.assertFalse(result['removed']);self.assertTrue(result['inventory_absent']);self.assertEqual([x[2]for x in calls],['delete','absence']);self.assertTrue(all(x[3]for x in calls))
    def test_cleanup_exact_owned_id(self):
        calls=[]
        def command(argv,cap,stage,cleanup):calls.append(argv);return {'stdout':b'{}'}
        result=m.cleanup_owned('OWNED',command,lambda raw,owned:owned=='OWNED');self.assertTrue(result['removed']);self.assertEqual(calls[0],['/usr/bin/xcrun','simctl','delete','OWNED']);self.assertIn('OWNED',calls[1]);self.assertNotIn('booted',str(calls))
    def test_metrics_closed_and_finite(self):
        raw=b'LAYOUT_METRICS w=375.0 h=667.0 titleh=20.3 inputh=180.0\n';self.assertEqual(m.layout_metrics(raw)['width'],375)
        for bad in [raw*2,raw.replace(b'375.0',b'nan'),raw.replace(b'375.0',b'5000')]:
            with self.assertRaises(m.Unavailable):m.layout_metrics(bad)
    def test_no_follow_no_overwrite(self):
        with tempfile.TemporaryDirectory()as td:
            p=Path(td).resolve()/'value';m.write_private(p,b'first');self.assertEqual(p.stat().st_mode&0o777,0o600)
            with self.assertRaises(FileExistsError):m.write_private(p,b'second')
            link=Path(td)/'link';link.symlink_to(p)
            with self.assertRaises(OSError):m.read_fixed(link,10)
            self.assertEqual(p.read_bytes(),b'first')
    def test_actual_owned_stdlib_process_normal(self):
        with tempfile.TemporaryDirectory()as td:
            r=m.process([sys.executable,'-I','-S','-B','-c','print("fixed")'],output=Path(td),stage='normal',timeout=2,metadata=True);self.assertEqual(r['stdout'],b'fixed\n');self.assertEqual(r['returncode'],0)
    def test_actual_owned_selector_fault_reaped(self):
        children=[];real=subprocess.Popen
        def spawn(*a,**kw):c=real(*a,**kw);children.append(c);return c
        with tempfile.TemporaryDirectory()as td,patch.object(m.subprocess,'Popen',side_effect=spawn),patch.object(m.selectors,'DefaultSelector',side_effect=OSError('inert')):
            with self.assertRaises(m.Unavailable):m.process([sys.executable,'-I','-S','-B','-c','import time;time.sleep(5)'],output=Path(td),stage='fault',timeout=2)
        self.assertEqual(len(children),1);self.assertIsNotNone(children[0].returncode)
    def test_clock_fault_no_spawn(self):
        with tempfile.TemporaryDirectory()as td,patch.object(m.time,'monotonic',side_effect=OSError('inert')),patch.object(m.subprocess,'Popen')as p:
            with self.assertRaises(m.Unavailable)as error:m.process([sys.executable],output=Path(td),stage='clock',timeout=2)
            self.assertEqual(error.exception.reason,'clock_unavailable')
            p.assert_not_called();self.assertEqual(list(Path(td).iterdir()),[])
    def test_shared_clock_sticky_and_absolute_admission(self):
        for bad in [90.0,float('nan'),float('inf'),True,'100',OSError('inert')]:
            with self.subTest(bad_type=type(bad).__name__):
                values=iter([100.0,bad,200.0])
                def raw():
                    value=next(values)
                    if isinstance(value,Exception):raise value
                    return value
                budget=m.Budget(raw)
                with self.assertRaises(m.Unavailable)as error:budget.seconds(600)
                self.assertEqual(error.exception.reason,'clock_unavailable')
                with self.assertRaises(m.Unavailable):budget.seconds(90,cleanup=True)
                with self.assertRaises(m.Unavailable):budget.check()
        now=[100.0];clock=m.Clock(lambda:now[0]);real_open=m.os.open
        def delayed_open(*args,**kwargs):
            fd=real_open(*args,**kwargs);now[0]=103.0;return fd
        with tempfile.TemporaryDirectory()as td,patch.object(m.os,'open',side_effect=delayed_open),patch.object(m.subprocess,'Popen')as spawn:
            with self.assertRaises(m.Unavailable)as error:m.process([sys.executable],output=Path(td),stage='late',timeout=600,stop_at=102.0,clock=clock)
            self.assertEqual(error.exception.reason,'deadline');spawn.assert_not_called();self.assertFalse(error.exception.child_started)
        with tempfile.TemporaryDirectory()as td,patch.object(m.subprocess,'Popen')as spawn:
            with self.assertRaises(m.Unavailable):m.process([sys.executable],output=Path(td),stage='already',timeout=600,stop_at=102.0,clock=clock)
            spawn.assert_not_called();self.assertEqual(list(Path(td).iterdir()),[])
    def test_actual_finalization_clock_refuses_after_reap(self):
        for when in ['wait','fsync','close','cancel']:
            with self.subTest(when=when):
                now=[100.0];children=[];real_spawn=subprocess.Popen;real_sync=m.os.fsync;real_close=m.os.close;real_open=m.os.open;logfd=[None];cancel=[False]
                def clock():
                    if cancel[0]:raise KeyboardInterrupt()
                    return now[0]
                def spawn(*args,**kwargs):
                    child=real_spawn(*args,**kwargs);children.append(child);wait=child.wait
                    def after_wait(*args,**kwargs):
                        result=wait(*args,**kwargs)
                        if when=='wait':now[0]=104.0
                        return result
                    child.wait=after_wait;return child
                def opened(*args,**kwargs):
                    fd=real_open(*args,**kwargs)
                    if str(args[0]).endswith('final.log'):logfd[0]=fd
                    return fd
                def synced(fd):
                    real_sync(fd)
                    if when=='fsync':now[0]=104.0
                def closed(fd):
                    real_close(fd)
                    if fd==logfd[0]:
                        if when=='close':now[0]=104.0
                        if when=='cancel':cancel[0]=True
                with tempfile.TemporaryDirectory()as td,patch.object(m.subprocess,'Popen',side_effect=spawn),patch.object(m.os,'open',side_effect=opened),patch.object(m.os,'fsync',side_effect=synced),patch.object(m.os,'close',side_effect=closed),patch.object(m.os,'killpg')as signal:
                    with self.assertRaises(m.Unavailable)as error:m.process([sys.executable,'-I','-S','-B','-c','print("11111111-2222-4333-8444-555555555555")'],output=Path(td),stage='final',timeout=2,metadata=True,clock=clock)
                    self.assertEqual(error.exception.reason,'command_cancelled'if when=='cancel'else'deadline');self.assertEqual(error.exception.private_stdout,b'11111111-2222-4333-8444-555555555555\n');self.assertEqual(error.exception.child_returncode,0);signal.assert_not_called()
                self.assertEqual(len(children),1);self.assertEqual(children[0].returncode,0);self.assertTrue(children[0].stdout.closed)
    def test_actual_log_and_metadata_caps(self):
        with tempfile.TemporaryDirectory()as td,patch.object(m,'MAX_LOG',16):
            with self.assertRaises(m.Unavailable):m.process([sys.executable,'-I','-S','-B','-c','print("x"*100)'],output=Path(td),stage='noisy',timeout=2)
            self.assertLessEqual((Path(td)/'noisy.log').stat().st_size,16)
        with tempfile.TemporaryDirectory()as td,patch.object(m,'MAX_META',4):
            with self.assertRaises(m.Unavailable):m.process([sys.executable,'-I','-S','-B','-c','print("12345")'],output=Path(td),stage='meta',timeout=2,metadata=True)
    def test_completed_device_cannot_skip_cleanup_or_configs(self):
        row={'pass':True,'sources_unchanged':True,'cleanup':{'removed':True,'diagnostics_retained':True},'configurations':[{'configuration':n,'actual_test_count':1,'passed':1,'failed':0,'skipped':0}for n,_,_ in m.CONFIGS]}
        self.assertTrue(m.complete_device(row))
        for key,value in [('cleanup',{'removed':False}),('sources_unchanged',False),('configurations',row['configurations'][:2])]:self.assertFalse(m.complete_device({**row,key:value}))
    def test_actual_deadline_owned_child_reaped(self):
        children=[];real=subprocess.Popen
        def spawn(*a,**kw):c=real(*a,**kw);children.append(c);return c
        with tempfile.TemporaryDirectory()as td,patch.object(m.subprocess,'Popen',side_effect=spawn):
            with self.assertRaises(m.Unavailable):m.process([sys.executable,'-I','-S','-B','-c','import time;time.sleep(5)'],output=Path(td),stage='timeout',timeout=.05)
        self.assertIsNotNone(children[0].returncode)
    def test_postreap_wait_error_never_signals_released_id(self):
        children=[];real=subprocess.Popen
        def spawn(*a,**kw):
            c=real(*a,**kw);children.append(c);wait=c.wait
            def afterwait(*a,**kw):wait(*a,**kw);raise OSError('after actual reap')
            c.wait=afterwait;return c
        with tempfile.TemporaryDirectory()as td,patch.object(m.subprocess,'Popen',side_effect=spawn),patch.object(m.os,'killpg')as signal:
            with self.assertRaises(m.Unavailable)as error:m.process([sys.executable,'-I','-S','-B','-c','print("11111111-2222-4333-8444-555555555555")'],output=Path(td),stage='reaped',timeout=2,metadata=True)
            self.assertEqual(error.exception.private_stdout,b'11111111-2222-4333-8444-555555555555\n');self.assertEqual(error.exception.child_returncode,0)
            signal.assert_not_called()
        self.assertEqual(children[0].returncode,0)
    def test_selector_close_error_still_closes_pipe(self):
        children=[];real=subprocess.Popen;select=m.selectors.DefaultSelector
        def spawn(*a,**kw):c=real(*a,**kw);children.append(c);return c
        def selector():
            s=select();close=s.close
            def afterclose():close();raise OSError('after actual close')
            s.close=afterclose;return s
        with tempfile.TemporaryDirectory()as td,patch.object(m.subprocess,'Popen',side_effect=spawn),patch.object(m.selectors,'DefaultSelector',side_effect=selector):
            with self.assertRaises(m.Unavailable):m.process([sys.executable,'-I','-S','-B','-c','pass'],output=Path(td),stage='closed',timeout=2)
        self.assertEqual(children[0].returncode,0);self.assertTrue(children[0].stdout.closed)
    def test_full_parent_walk_refuses_intermediate_link(self):
        with tempfile.TemporaryDirectory()as td:
            root=Path(td).resolve();(root/'owned').mkdir();(root/'owned/file').write_bytes(b'fixed');(root/'link').symlink_to(root/'owned',target_is_directory=True)
            with self.assertRaises(OSError):m.read_fixed(root/'link/file',16)
            self.assertEqual(m.read_fixed(root/'owned/file',16),b'fixed')
    def test_selected_screenshot_roles_and_bounds(self):
        class Capture:
            def directory(self,p):pass
            def check(self):pass
        class Budget:
            def check(self,**kw):pass
        with tempfile.TemporaryDirectory()as td:
            root=Path(td).resolve();target=root/'light-attachments';target.mkdir();items=[]
            for index,role in enumerate(['size-layout-app','size-layout-notices','size-layout-evidence']):
                name=str(index)+'.png';raw=b'\x89PNG\r\n\x1a\n'+(13).to_bytes(4,'big')+b'IHDR'+(750).to_bytes(4,'big')+(1334).to_bytes(4,'big');(target/name).write_bytes(raw);items.append({'suggestedHumanReadableName':role+'_0.png','exportedFileName':name})
            manifest=target/'manifest.json';manifest.write_text(json.dumps([{'attachments':items}]))
            result=m.export_images(root/'inert.xcresult',root,'light',lambda *a,**k:None,Budget(),Capture());self.assertEqual(len(result),3);self.assertEqual(result[0]['pixel_width'],750)
            manifest.write_text(json.dumps([{'attachments':items*2}]))
            with self.assertRaises(m.Unavailable):m.export_images(root/'inert',root,'light',lambda *a,**k:None,Budget(),Capture())
            manifest.write_text(json.dumps([{'attachments':[{**items[0],'exportedFileName':'../outside.png'},*items[1:]]}]))
            with self.assertRaises(m.Unavailable):m.export_images(root/'inert',root,'light',lambda *a,**k:None,Budget(),Capture())
    def test_matrix_failure_stops_before_next_device(self):
        evidence=m.pinned_module('tools/artifact_evidence_io.py')
        from tools.blind_review_io import create
        fake={'destination':lambda p:p,'create':create};seen=[]
        def modules(name):return evidence if 'artifact_evidence' in name else fake
        def one(profile,output,*args):seen.append(profile);return {'profile':profile,'pass':False,'sources_before':{'fixed':'x'},'sources_after':{'fixed':'x'}}
        with tempfile.TemporaryDirectory()as td,patch.object(m.sys,'platform','darwin'),patch.object(m.os,'uname',return_value=type('Host',(),{'machine':'arm64'})()),patch.object(m,'pinned_module',side_effect=modules),patch.object(m,'one_device',side_effect=one),patch.object(m,'source_map',return_value={'fixed':'x'}):
            parent=Path(td).resolve();parent.chmod(0o700);out=parent/'matrix';value=m.run(out,['small','regular']);self.assertFalse(value['pass']);self.assertEqual(seen,['small']);self.assertFalse((out/'regular').exists());self.assertEqual((out/'matrix.json').stat().st_mode&0o777,0o600)
    def test_cli_reports_typed_publication_uncertainty(self):
        g=runpy.run_path(str(m.ROOT/'scripts/verify-ios-size-matrix.py'))
        def uncertain(*a):raise m.OutputUncertain('inert')
        output=io.StringIO()
        with patch.dict(g['main'].__globals__,run=uncertain),patch.object(sys,'argv',['verify','--output','/private/inert','--profiles','small']),contextlib.redirect_stdout(output):self.assertEqual(g['main'](),3)
        self.assertEqual(json.loads(output.getvalue())['state'],'OUTPUT_UNCERTAIN')
    def test_cleanup_bypasses_lowfree_and_failed_log_open(self):
        with tempfile.TemporaryDirectory()as td,patch.object(m.shutil,'disk_usage',return_value=type('Disk',(),{'free':0})()):
            result=m.process([sys.executable,'-I','-S','-B','-c','print("fixed")'],output=Path(td)/'absent',stage='cleanup',timeout=2,metadata=True,cleanup=True)
            self.assertEqual(result['stdout'],b'fixed\n');self.assertEqual(result['returncode'],0);self.assertFalse(result['logging_ok'])
    def test_create_postcheck_drift_still_deletes_exact_owned_identity(self):
        legacy=m.pinned_module('scripts/verify-ios-share.py');state={'created':False,'calls':[]};owned='11111111-2222-4333-8444-555555555555'
        class Capture:
            def __init__(self,fd):self.fd=fd
            def directory(self,p):return self.fd
            def check(self):
                if state['created']:raise ValueError('inert post-create boundary change')
            def save(self,*a,**kw):pass
        def process(argv,**kw):
            state['calls'].append(argv);raw=b''
            if argv[0].endswith('sysctl'):raw=b'8589934592 8'
            elif argv[0].endswith('xcodebuild'):raw=b'Xcode 27.2\nBuild version 27B52'
            elif '--show-sdk-version'in argv:raw=b'27.2'
            elif argv[2:4]==['list','runtimes']:raw=json.dumps({'runtimes':[{'identifier':m.RUNTIME,'isAvailable':True,'version':'26.2','buildversion':m.BUILD,'supportedDeviceTypes':[{'identifier':m.profile_type('small'),'productFamily':'iPhone'}]}]}).encode()
            elif argv[2]=='create':state['created']=True;raw=owned.encode()
            elif argv[2:4]==['list','devices']:raw=b'{"devices":{}}'
            return {'stdout':raw,'bytes':len(raw),'sha256':m.sha(raw),'returncode':0,'logging_ok':not kw.get('no_log')}
        payload={'Tests/UIFlows.swift':m.read_fixed(m.ROOT/'mobile/ios/Tests/UIFlows.swift',262144),**{f'x{i}':b'fixed'for i in range(45)}}
        with tempfile.TemporaryDirectory()as td,patch.object(m,'process',side_effect=process),patch.object(m,'source_map',return_value={'fixed':'x'}):
            root=Path(td).resolve();root.chmod(0o700);fd=os.open(root,os.O_RDONLY|os.O_DIRECTORY)
            try:row=m.one_device('small',root,legacy,{'files':lambda:payload},Capture(fd))
            finally:os.close(fd)
        self.assertFalse(row['pass']);self.assertEqual(row['owned_id'],owned);self.assertTrue(row['cleanup']['removed']);self.assertFalse(row['cleanup']['diagnostics_retained'])
        self.assertEqual([a for a in state['calls']if len(a)>2 and a[2]=='delete'],[['/usr/bin/xcrun','simctl','delete',owned]])
    def test_inert_source_pin_refuses_before_exec(self):
        with patch.object(m,'read_fixed',return_value=b'raise RuntimeError("must not execute")'):
            with self.assertRaises(m.Unavailable):m.pinned_module('scripts/verify-ios-share.py')

if __name__=='__main__':unittest.main()
