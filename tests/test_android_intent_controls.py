"""Finite synthetic sender/driver controls; JVM stubs are not Android execution."""
import ast
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import textwrap
import unittest
from unittest import mock
import xml.etree.ElementTree as ET
import zipfile

ROOT=Path(__file__).resolve().parents[1]
def load(name,file):
    spec=importlib.util.spec_from_file_location(name,ROOT/file)
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value
m=load('synthetic_intents','scripts/android-intent-controls.py')
driver=load('synthetic_driver','scripts/verify-android-emulator.py')

class IntentPredicates(unittest.TestCase):
    def exercise(self,fault=None):
        calls=[];state=0;report={};sends=0
        def send(selection):
            nonlocal state,sends
            calls.append(selection);sends+=1
            if fault=='send':raise OSError('PRIVATE_NATIVE_CANARY /private/file')
            if fault=='drop_invalid' and selection: return
            if fault=='drop_recovery' and sends==3:return
            state=selection
        def wait(predicate):
            view=ET.Element('hierarchy')
            invalid=state!=0
            status=m.UNSUPPORTED if invalid else m.RECEIVED
            editor=m.HINT if invalid else m.MARKER
            enabled='false' if invalid else 'true'
            if fault=='retained_text' and invalid:editor=m.MARKER
            if fault=='unrelated_hint' and invalid:editor='PRIVATE_INPUT_CANARY'
            if fault=='enabled_invalid' and invalid:enabled='true'
            if fault=='missing_enabled':enabled='unknown'
            if fault=='stale_refusal' and not invalid:editor=m.HINT;status=m.UNSUPPORTED
            for rid,text in [('editor',editor),('status',status),('check','Check PS')]:
                node=ET.SubElement(view,'node',{'resource-id':m.PACKAGE+':id/'+rid,'text':text,'enabled':enabled if rid=='check' else 'true'})
                if fault=='duplicate_editor' and rid=='editor':ET.SubElement(view,'node',dict(node.attrib))
            if fault in ('result','details'):ET.SubElement(view,'node',{'resource-id':m.PACKAGE+':id/'+('tag' if fault=='result' else 'details'),'text':'PRIVATE_RESULT_CANARY'})
            if not predicate(view):raise ValueError('PRIVATE_TIMEOUT_CANARY')
            return view
        try:m.verify_cases(send,wait,report)
        except m.IntentControlRefusal as error:return report,calls,error
        return report,calls,None

    def test_all_nine_pairs_require_refusal_and_fresh_exact_recovery(self):
        report,calls,error=self.exercise();self.assertIsNone(error)
        self.assertEqual(calls,[0,*[n for i in range(1,10) for n in (i,0)]])
        self.assertEqual(report['status'],'EXECUTED');self.assertTrue(report['pass'])
        self.assertEqual(report['cases'],[{'case':n,'refused':True,'fresh_valid_recovery':True,'pass':True} for n in m.CASES])
        self.assertEqual(report['case_count'],9)
        self.assertTrue(all(type(v) is bool for v in report['last_observation'].values()))
        self.assertNotIn(m.MARKER,json.dumps(report));self.assertNotIn(m.HINT,json.dumps(report))

    def test_every_wrong_or_stale_state_refuses_without_raw_values(self):
        for fault in ['send','drop_invalid','drop_recovery','retained_text','unrelated_hint','enabled_invalid','missing_enabled','stale_refusal','duplicate_editor','result','details']:
            with self.subTest(fault=fault):
                report,calls,error=self.exercise(fault)
                self.assertIsInstance(error,m.IntentControlRefusal)
                self.assertEqual(report['status'],'FAILED');self.assertFalse(report['pass']);self.assertEqual(report['case_count'],0)
                raw=json.dumps(report)+str(error);self.assertNotIn('PRIVATE_',raw);self.assertNotIn('/private',raw);self.assertNotIn(m.MARKER,raw)

    def test_unknown_hint_missing_nodes_and_nonboolean_enabled_not_empty_proof(self):
        for raw in ['<hierarchy/>','<hierarchy><node resource-id="com.aitrustid.android:id/check" enabled="1"/></hierarchy>']:
            value=m.observe(ET.fromstring(raw));self.assertIsNone(value['check_enabled']);self.assertFalse(value['editor_empty_or_exact_hint'])

    def test_failure_after_completed_pair_preserves_exact_prefix(self):
        report={};selection=0
        def send(n):
            nonlocal selection
            selection=n
            if n==2:raise OSError('PRIVATE_NATIVE_CANARY')
        def wait(predicate):
            root=ET.Element('hierarchy')
            for rid,text,enabled in [('editor',m.MARKER if selection==0 else '',True),('status',m.RECEIVED if selection==0 else m.UNSUPPORTED,True),('check','Check',selection==0)]:
                ET.SubElement(root,'node',{'resource-id':m.PACKAGE+':id/'+rid,'text':text,'enabled':str(enabled).lower()})
            self.assertTrue(predicate(root));return root
        with self.assertRaises(m.IntentControlRefusal):m.verify_cases(send,wait,report)
        self.assertEqual(report['case_count'],1);self.assertEqual(report['cases'][0]['case'],'missing_text')

class SafeSenderBoundary(unittest.TestCase):
    def test_exact_uid_parse_refuses_ambiguity_related_packages_and_private_errors(self):
        self.assertEqual(m.installed_uid(b'package:com.aitrustid.synthetic uid:10042\n',m.SENDER),10042)
        for raw in [b'',b'package:com.aitrustid.synthetic.other uid:10042',b'package:com.aitrustid.synthetic uid:999',b'package:com.aitrustid.synthetic uid:10042\n'*2,b'\xff',b'x'*4097]:
            with self.assertRaises((ValueError,UnicodeError)):m.installed_uid(raw,m.SENDER)

    def test_fixture_manifest_is_separate_zero_permission_no_provider_no_network(self):
        value=ET.parse(ROOT/m.FIXTURES[0]).getroot();ns='{http://schemas.android.com/apk/res/android}'
        self.assertEqual(value.attrib['package'],m.SENDER);self.assertEqual(value.findall('uses-permission'),[])
        app=value.find('application');self.assertEqual(app.attrib[ns+'allowBackup'],'false');self.assertEqual(app.attrib[ns+'debuggable'],'false')
        self.assertEqual(app.findall('provider'),[]);self.assertEqual(app.findall('service'),[])
        self.assertEqual([x.attrib[ns+'name'] for x in app.findall('activity')],['.SenderActivity'])
        production=(ROOT/'mobile/android/AndroidManifest.xml').read_text();self.assertNotIn(m.SENDER,production)
        builder=load('synthetic_default_builder','scripts/android-share-build.py')
        with tempfile.TemporaryDirectory() as p:
            paths,_=builder.activity_sources(Path(p));self.assertFalse(any('intent-sender' in str(x) for x in paths))

    def test_dex_boundary_refuses_unexpected_and_duplicate_members_before_marker_check(self):
        with tempfile.TemporaryDirectory() as p:
            apk=Path(p)/'fixture.apk'
            for names in [['classes10.dex'],['classes.dex','classes3.dex'],['other.dex']]:
                with zipfile.ZipFile(apk,'w') as z:
                    for n in names:z.writestr(n,m.SENDER_DEX)
                with self.assertRaises(ValueError):m.dex_bytes(apk)
            with zipfile.ZipFile(apk,'w') as z:
                for i in range(65):z.writestr(str(i),b'')
            with mock.patch.object(m.zipfile,'ZipFile',side_effect=AssertionError('Must preflight count')):
                with self.assertRaises(ValueError):m.dex_bytes(apk)

    def test_same_uid_or_nonportrait_refuses_before_any_send_and_no_private_diagnostics(self):
        for fault in ['same_uid','nonportrait','default_leak','build']:
            with tempfile.TemporaryDirectory() as p:
                report={};shell=mock.Mock();install=mock.Mock();wait=mock.Mock()
                def reply(args,timeout=10):
                    if args[0]=='pm':return ('package:'+args[-1]+' uid:'+('10042' if fault=='same_uid' or args[-1]==m.SENDER else '10041')+'\n').encode()
                    if args==['wm','user-rotation']:return b'free\n' if fault=='nonportrait' else b'lock 0\n'
                    raise AssertionError('Must not send')
                compile_mock=mock.Mock(side_effect=OSError('PRIVATE_BUILD_CANARY')) if fault=='build' else mock.Mock(return_value=(Path(p)/'sender.apk',{'permission_count':0}))
                with mock.patch.dict(os.environ,{'RUNNER_TEMP':p}),mock.patch.object(m,'source_identity',return_value={'source':'frozen'}),mock.patch.object(m,'dex_bytes',return_value=m.SENDER_DEX if fault=='default_leak' else b'ordinary'),mock.patch.object(m,'compile_sender',compile_mock):
                    with self.assertRaises(m.IntentControlRefusal) as error:m.run_controls(Path(p),Path(p)/'default.apk',install,reply,wait,report)
                self.assertEqual(report['status'],'FAILED');self.assertFalse(report['pass']);wait.assert_not_called()
                self.assertNotIn('PRIVATE_',json.dumps(report)+str(error.exception))
                self.assertEqual(list(Path(p).iterdir()),[])

    def test_lazy_child_import_failure_fixed_unavailable_keeps_existing_cases(self):
        report={}
        with mock.patch.object(driver.importlib.util,'spec_from_file_location',side_effect=ImportError('PRIVATE_IMPORT_CANARY')):
            with self.assertRaises(driver.AndroidIntentRefusal) as error:driver.verify_intent_controls(None,None,None,None,None,report)
        self.assertEqual(error.exception.code,'intent_workflow_unavailable');self.assertEqual(report,{'status':'FAILED','pass':False})
        self.assertNotIn('PRIVATE_',str(error.exception))

class SenderBuild(unittest.TestCase):
    def test_actual_build_command_contract_with_inert_sdk_and_failures(self):
        for fault in [None,'command','permission','source_drift']:
            with self.subTest(fault=fault),tempfile.TemporaryDirectory() as p:
                base=Path(p);sdk=base/'sdk';java=base/'java';stage=base/'stage';stage.mkdir()
                for n in ['java','javac','keytool']:
                    q=java/'bin'/n;q.parent.mkdir(parents=True,exist_ok=True);q.touch()
                for n in ['aapt2','d8','zipalign','apksigner']:
                    q=sdk/'build-tools/36.0.0'/n;q.parent.mkdir(parents=True,exist_ok=True);q.touch()
                q=sdk/'platforms/android-36/android.jar';q.parent.mkdir(parents=True);q.touch();calls=[]
                def run(argv,**kwargs):
                    calls.append(argv);self.assertEqual(argv[0],'/usr/bin/env');self.assertEqual(kwargs['input'],b'');self.assertLessEqual(kwargs['timeout'],60);self.assertEqual(kwargs['output_limit'],262144)
                    args=argv[3:];tool=Path(args[0]).name
                    if fault=='command':return subprocess.CompletedProcess(argv,1,b'PRIVATE_TOOL_CANARY')
                    if tool=='aapt2' and args[1]=='link':
                        with zipfile.ZipFile(Path(args[args.index('-o')+1]),'w') as z:z.writestr('AndroidManifest.xml',b'inert')
                    if tool=='d8':(Path(args[args.index('--output')+1])/'classes.dex').write_bytes(m.SENDER_DEX)
                    if tool=='zipalign':shutil.copyfile(args[-2],args[-1])
                    if tool=='keytool':Path(args[args.index('-keystore')+1]).touch()
                    if tool=='apksigner' and args[1]=='sign':shutil.copyfile(args[-1],args[args.index('--out')+1])
                    raw=b'uses-permission: PRIVATE_PERMISSION_CANARY' if fault=='permission' and tool=='aapt2' and args[1]=='dump' else b''
                    return subprocess.CompletedProcess(argv,0,raw)
                identity=mock.Mock(side_effect=[{'f':'a'},{'f':'b'}]) if fault=='source_drift' else mock.Mock(return_value={'f':'a'})
                with mock.patch.dict(os.environ,{'JAVA_HOME_17_X64':str(java)}),mock.patch.object(m,'run_worker',side_effect=run),mock.patch.object(m,'source_identity',identity):
                    if fault:
                        with self.assertRaises(ValueError) as error:m.compile_sender(sdk,stage)
                        self.assertNotIn('PRIVATE_',str(error.exception))
                    else:
                        apk,result=m.compile_sender(sdk,stage);self.assertEqual(result['permission_count'],0);self.assertFalse(result['production_checker_modified']);self.assertIn(m.SENDER_DEX,m.dex_bytes(apk));self.assertFalse((stage/'sender-ci.p12').exists())
                self.assertFalse(any('sdkmanager' in part or 'licenses' in part for argv in calls for part in argv))

class PreservedOriginalControls(unittest.TestCase):
    def test_original_seven_configuration_two_and_wait_exact_source_unchanged(self):
        expected={'verify_share_controls':'ae33c0b4175732b8eab516123e104ea2cfc93dc4d19984cf2eb58517c7227ab7',
            'verify_background_clear':'0d25c47bdabe7b57b2aa937792ba72e34323d035d06167ece20332ae439220aa',
            'verify_configuration_controls':'4b5ed8cd7631d013b078614abfa49cf63918dc1e037bccb4fe30a6face128ba8',
            'wait':'ca25559a2aa7f3aeb49e5210744dc93b6a079562da3310ec113025ae37c96141'}
        source=(ROOT/'scripts/verify-android-emulator.py').read_text()
        tree=ast.parse(source)
        for name,wanted in expected.items():
            nodes=[n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name==name]
            self.assertEqual(len(nodes),1);self.assertEqual(hashlib.sha256(ast.get_source_segment(source,nodes[0]).encode()).hexdigest(),wanted)


class ActualSenderJVM(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        home=Path(os.environ.get('JAVA_HOME','/opt/homebrew/opt/openjdk@21'))
        cls.javac=home/'bin/javac';cls.java=home/'bin/java'
        if not cls.javac.is_file() or not cls.java.is_file():raise unittest.SkipTest('Existing real JDK unavailable; no JVM execution claimed')

    def test_actual_java_constructs_exact_ten_fixed_intents_no_subject_execution(self):
        stubs={
        'android/os/Bundle.java':'package android.os; public class Bundle {}',
        'android/net/Uri.java':'package android.net; public class Uri { public final String value; private Uri(String s){value=s;} public static Uri parse(String s){return new Uri(s);} }',
        'android/content/ComponentName.java':'package android.content; public class ComponentName {public final String p,c;public ComponentName(String a,String b){p=a;c=b;}}',
        'android/app/Activity.java':'package android.app; import android.content.Intent; import android.os.Bundle; public class Activity {public void onCreate(Bundle b){} public Intent getIntent(){return new Intent("stub");}public void startActivity(Intent i){}public void finish(){}}',
        'android/content/ClipData.java':'''package android.content; import android.net.Uri; import java.util.*; public class ClipData {public static class Item {public final Object value;public Item(Uri u){value=u;}public Item(CharSequence s){value=s;}} public final ArrayList<Item> items=new ArrayList<>();public ClipData(String l,String[] t,Item i){items.add(i);}public static ClipData newPlainText(String l,CharSequence s){return new ClipData(l,new String[]{"text/plain"},new Item(s));}public void addItem(Item i){items.add(i);}}''',
        'android/content/Intent.java':'''package android.content; import android.net.Uri; import java.util.*; public class Intent {public static final String ACTION_SEND="SEND",ACTION_SEND_MULTIPLE="MULTIPLE",EXTRA_TEXT="TEXT",EXTRA_STREAM="STREAM"; public String action,type;public ComponentName component;public Uri data;public ClipData clip;public final HashMap<String,Object> extras=new HashMap<>();public Intent(String s){action=s;}public Intent setComponent(ComponentName c){component=c;return this;}public Intent setType(String s){type=s;return this;}public Intent setAction(String s){action=s;return this;}public Intent setDataAndType(Uri u,String s){data=u;type=s;return this;}public Intent putExtra(String s,Object v){extras.put(s,v);return this;}public void removeExtra(String s){extras.remove(s);}public void setClipData(ClipData c){clip=c;}public int getIntExtra(String s,int d){Object v=extras.get(s);return v instanceof Integer?(Integer)v:d;}}''',
        'com/aitrustid/synthetic/Harness.java':'''package com.aitrustid.synthetic; import android.content.*; public class Harness {static void ok(boolean b){if(!b)throw new AssertionError("fixed fixture mismatch");}public static void main(String[] a){for(int k=0;k<=9;k++){Intent i=SenderActivity.selected(k);ok(i.component.p.equals("com.aitrustid.android")&&i.component.c.equals("com.aitrustid.android.CheckActivity"));ok(i.type.equals("text/plain"));if(k==0)ok(i.extras.get(Intent.EXTRA_TEXT).equals(SenderActivity.MARKER));if(k==1)ok(!i.extras.containsKey(Intent.EXTRA_TEXT));if(k==2)ok(i.extras.get(Intent.EXTRA_TEXT) instanceof Integer);if(k==3)ok(i.action.equals(Intent.ACTION_SEND_MULTIPLE));if(k==4)ok(i.extras.get(Intent.EXTRA_STREAM) instanceof android.net.Uri);if(k==5)ok(i.data.value.equals("content://synthetic.invalid/item"));if(k==6)ok(i.clip.items.size()==1&&i.clip.items.get(0).value instanceof android.net.Uri);if(k==7)ok(i.clip.items.size()==2);if(k==8)ok(((String)i.extras.get(Intent.EXTRA_TEXT)).codePointCount(0,20001)==20001);if(k==9)ok(Character.isHighSurrogate(((String)i.extras.get(Intent.EXTRA_TEXT)).charAt(1)));}for(int k:new int[]{-1,10}){try{SenderActivity.selected(k);throw new AssertionError();}catch(IllegalArgumentException expected){}}System.out.println("SYNTHETIC_INTENTS:10");}}'''}
        with tempfile.TemporaryDirectory() as p:
            stage=Path(p);files=[]
            for n,raw in stubs.items():
                q=stage/n;q.parent.mkdir(parents=True,exist_ok=True);q.write_text(raw);files.append(q)
            source=stage/'com/aitrustid/synthetic/SenderActivity.java';source.write_bytes((ROOT/m.FIXTURES[1]).read_bytes());files.append(source)
            result=subprocess.run([str(self.javac),'--release','8','-d',str(stage),*[str(x) for x in files]],capture_output=True,timeout=20)
            self.assertEqual(result.returncode,0,'Actual existing JDK failed fixed fixture compilation')
            result=subprocess.run([str(self.java),'-cp',str(stage),'com.aitrustid.synthetic.Harness'],capture_output=True,timeout=10)
            self.assertEqual(result.returncode,0);self.assertEqual(result.stdout,b'SYNTHETIC_INTENTS:10\n')

if __name__=='__main__':unittest.main()
