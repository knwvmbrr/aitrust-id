"""Finite CI-only intake provenance; no SDK/emulator/download or runtime claims."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest import mock
import warnings
import zipfile

ROOT=Path(__file__).resolve().parents[1]
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,ROOT/path)
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value
build=module('android_intake_build','scripts/android-share-build.py')
driver=module('android_intake_driver','scripts/verify-android-emulator.py')


class ProbeSelection(unittest.TestCase):
    def test_default_sources_never_read_copy_or_compile_probe(self):
        with tempfile.TemporaryDirectory() as temporary,mock.patch.object(build,'read_regular',side_effect=AssertionError('Probe source must not be read')):
            sources,report=build.activity_sources(Path(temporary))
            self.assertIsNone(report)
            self.assertIn(ROOT/'mobile/android/src/com/aitrustid/android/CheckActivity.java',sources)
            self.assertEqual(sources,sorted((ROOT/'mobile/android/src').rglob('*.java')))
            self.assertEqual(list(Path(temporary).iterdir()),[])

    def test_probe_changes_only_exact_class_declaration_and_labels_separate_variant(self):
        original=(ROOT/'mobile/android/src/com/aitrustid/android/CheckActivity.java').read_bytes()
        with tempfile.TemporaryDirectory() as temporary:
            sources,report=build.activity_sources(Path(temporary),True)
            staged={p.name:p for p in sources if Path(temporary) in p.parents}
            self.assertEqual(set(staged),{'IntakeActivityBase.java','CheckActivity.java'})
            self.assertEqual(staged['IntakeActivityBase.java'].read_bytes().replace(b'class IntakeActivityBase extends Activity {',b'public final class CheckActivity extends Activity {',1),original)
            self.assertEqual(staged['CheckActivity.java'].read_bytes(),(ROOT/'tests/android/CheckActivity.java').read_bytes())
            self.assertNotIn(ROOT/'mobile/android/src/com/aitrustid/android/CheckActivity.java',sources)
            self.assertEqual(report['production_activity_sha256'],hashlib.sha256(original).hexdigest())
            self.assertFalse(report['production_equivalent_apk'])

    def test_multiple_or_ambiguous_declarations_refuse(self):
        original=(ROOT/'mobile/android/src/com/aitrustid/android/CheckActivity.java').read_bytes()
        for raw in (original+original,original+b'// CheckActivity\n',original.replace(b'public final class',b'public class')):
            with self.subTest(raw_length=len(raw)),tempfile.TemporaryDirectory() as temporary,mock.patch.object(build,'read_regular',return_value=raw):
                with self.assertRaises(ValueError):build.activity_sources(Path(temporary),True)
                self.assertEqual(list(Path(temporary).iterdir()),[])

    def test_compiled_dex_marker_mismatch_refuses_both_variants(self):
        with tempfile.TemporaryDirectory() as temporary:
            apk=Path(temporary)/'synthetic.apk'
            for payload,probe in [(b'dex-default',False),(b'AITRUST_INTAKE_V1: Lcom/aitrustid/android/IntakeActivityBase;',True)]:
                with zipfile.ZipFile(apk,'w') as archive:archive.writestr('classes.dex',payload)
                build.verify_probe_dex(apk,probe)
                with self.assertRaises(ValueError):build.verify_probe_dex(apk,not probe)

    def test_unexpected_duplicate_or_nonsequential_dex_cannot_hide_probe(self):
        marker=b'AITRUST_INTAKE_V1: Lcom/aitrustid/android/IntakeActivityBase;'
        with tempfile.TemporaryDirectory() as temporary:
            apk=Path(temporary)/'synthetic.apk'
            for extra in ('classes10.dex','classes0.dex','classes01.dex','classes5.dex','CLASSES2.DEX','other.dex','classes.dex','classes3.dex'):
                with self.subTest(extra=extra),warnings.catch_warnings():
                    warnings.simplefilter('ignore',UserWarning)
                    with zipfile.ZipFile(apk,'w') as archive:
                        archive.writestr('classes.dex',b'ordinary');archive.writestr(extra,marker)
                    with self.assertRaises(ValueError):build.verify_probe_dex(apk,False)
            with zipfile.ZipFile(apk,'w') as archive:
                archive.writestr('classes2.dex',b'ordinary');archive.writestr('classes.dex',b'ordinary')
            build.verify_probe_dex(apk,False)

    def test_zip_count_is_bounded_before_zipfile_and_large_dex_refuses(self):
        with tempfile.TemporaryDirectory() as temporary:
            apk=Path(temporary)/'synthetic.apk'
            with zipfile.ZipFile(apk,'w') as archive:
                for i in range(65):archive.writestr('fixture'+str(i),b'')
            with mock.patch.object(build.zipfile,'ZipFile',side_effect=AssertionError('Must refuse before allocation')):
                with self.assertRaises(ValueError):build.verify_probe_dex(apk,False)
            with zipfile.ZipFile(apk,'w') as archive:archive.writestr('classes.dex',b'X'*(16*1024*1024+1))
            with self.assertRaises(ValueError):build.verify_probe_dex(apk,False)


class ProbeParser(unittest.TestCase):
    def frame(self,value=None):
        if value is None:value={'schema':1,'instances':1,'truncated':False,'events':[[1,'CREATE_BEGIN','SEND',False,'UNBUILT',False],[1,'CREATE_END','MAIN',True,'RECEIVED',False]]}
        return b'PRIVATE_FRAMEWORK_HEADER /private/irrelevant\n  AITRUST_INTAKE_V1:'+json.dumps(value).encode()+b'\n'

    def test_exact_fixed_frame_discards_other_headers(self):
        result=driver.intake_probe_observation(self.frame())
        self.assertEqual(result['state'],'OBSERVED');self.assertEqual(result['events'][1],[1,'CREATE_END','MAIN',True,'RECEIVED',False])
        self.assertNotIn('PRIVATE',json.dumps(result));self.assertNotIn('/private',json.dumps(result))

    def test_missing_duplicate_oversized_malformed_private_fields_are_unavailable(self):
        value={'schema':1,'instances':1,'truncated':False,'events':[[1,'CREATE_BEGIN','SEND',False,'UNBUILT',False]]}
        values=[]
        for field,item in [('schema',True),('instances',True),('instances',0),('instances',256),('truncated',0),('events',[]),('events',value['events']*33),('PRIVATE',True)]:
            values.append({**value,field:item})
        for index,item in [(0,True),(0,2),(1,'PRIVATE_CALLBACK'),(2,'PRIVATE_INTENT'),(3,'PRIVATE_TEXT'),(4,'PRIVATE_STATUS'),(5,1)]:
            row=list(value['events'][0]);row[index]=item;values.append({**value,'events':[row]})
        raws=[b'',b'\xff',self.frame()+self.frame(),b'X'*65537,b'AITRUST_INTAKE_V1:'+b'['*4000,
            b'AITRUST_INTAKE_V1:{"schema":1,"schema":1}']+[self.frame(v) for v in values]
        for raw in raws:
            with self.subTest(length=len(raw)):
                self.assertEqual(driver.intake_probe_observation(raw),{'state':'UNAVAILABLE','reason':'intake_provenance_unavailable'})

    def test_exact_owned_read_five_seconds_and_fault_isolation(self):
        shell=mock.Mock(return_value=self.frame())
        self.assertEqual(driver.collect_intake_probe(shell)['state'],'OBSERVED')
        shell.assert_called_once_with(['dumpsys','activity',driver.COMPONENT,'aitrust-intake-v1'],5)
        shell.side_effect=OSError('PRIVATE_PATH_CANARY')
        self.assertEqual(driver.collect_intake_probe(shell),{'state':'UNAVAILABLE','reason':'intake_provenance_unavailable'})

    def run_controls(self,fail=False,probe=None):
        report={};cases=[];calls=[]
        def send(*args):calls.append('send')
        def wait(predicate):
            calls.append('wait')
            if fail:raise ValueError('PRIVATE_PRIMARY_FAILURE')
            import xml.etree.ElementTree as ET
            view=ET.fromstring('<hierarchy><node text="Text received. Review it, then tap Check."/></hierarchy>')
            self.assertTrue(predicate(view));return view
        def click(*args):calls.append('click');raise OSError('PRIVATE_LATER_FAILURE')
        try:driver.verify_share_controls(send,None,wait,click,report,cases,first_receive_metadata=probe)
        except driver.AndroidControlRefusal as error:return report,cases,calls,error
        self.fail('A scripted fault must fail')

    def test_successful_receive_collects_once_before_check_and_later_failure_is_preserved(self):
        probe=mock.Mock(return_value={'state':'OBSERVED'})
        report,cases,calls,error=self.run_controls(probe=probe)
        probe.assert_called_once_with();self.assertEqual(calls,['send','wait','click'])
        self.assertEqual(cases,[{'case':'receive_requires_explicit_check','pass':True}])
        self.assertEqual(error.code,'share_finding_tap_unavailable')
        self.assertEqual(report['first_receive_provenance'],{'state':'OBSERVED'})

    def test_failed_receive_still_collects_once_and_probe_failure_never_grants_a_case(self):
        probe=mock.Mock(side_effect=OSError('PRIVATE_PROBE_FAILURE'))
        report,cases,calls,error=self.run_controls(True,probe)
        probe.assert_called_once_with();self.assertEqual(cases,[])
        self.assertEqual(error.code,'share_first_receive_unavailable')
        self.assertEqual(report['first_receive_provenance'],{'state':'UNAVAILABLE','reason':'intake_provenance_unavailable'})
        self.assertNotIn('PRIVATE',json.dumps(report)+str(error))


def extracted_method(source,start,end):
    """Exact contiguous production method bytes, not a reimplementation."""
    if source.count(start)!=1 or source.count(end)!=1:raise ValueError('Ambiguous method fixture')
    return source[source.index(start):source.index(end)]


class ActualProductionMethodJVM(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        configured=os.environ.get('JAVA_HOME')
        choices=[Path(configured)] if configured else []
        choices+=[Path('/opt/homebrew/opt/openjdk@21'),Path('/opt/homebrew/opt/openjdk')]
        cls.home=next((p for p in choices if (p/'bin/javac').is_file()),None)
        if cls.home is None:
            javac=shutil.which('javac')
            # /usr/bin/javac on macOS may be only Apple's unconfigured launcher.
            if javac and os.uname().sysname!='Darwin':cls.home=Path(javac).resolve().parents[1]
        if cls.home is None:raise unittest.SkipTest('Existing actual JDK required; no toolchain downloaded')

    def test_actual_methods_transfer_config_draft_and_preserve_real_leave_clearing_without_runtime_claim(self):
        source=(ROOT/'mobile/android/src/com/aitrustid/android/CheckActivity.java').read_text()
        receive=extracted_method(source,'    private void receive(Intent intent){','    @Override protected void onNewIntent')
        new_intent=extracted_method(source,'    @Override protected void onNewIntent','    private void setText(String value){')
        methods=extracted_method(source,'    private void setText(String value){','    private void startCheck(){')
        lifecycle=extracted_method(source,'    private void stopEngine(){','    @Override protected void onSaveInstanceState')
        # The UI/framework fixture is deliberately minimal. The receive/clear
        # bodies and ShareSession are actual source, but this is NOT Android.
        base='''package com.aitrustid.android;
import android.app.Activity; import android.content.*; import android.widget.*; import android.view.View;
class IntakeActivityBase extends Activity {
 private ShareSession session=new ShareSession(); private EditText editor=new EditText();
 private TextView status=new TextView(),tag=new TextView(),details=new TextView();
 private Button check=new Button(),cancel=new Button(),more=new Button();
 private Engine engine; private boolean settingText=false,detailsOpen=false;private String evidence="";
 private boolean viewsReady=false,userLeaving=false;
 private ConfigurationDraft pendingDraft,transferredDraft;
 private boolean fixtureCreated=false;
 static class Engine {void stop(){}}
 public void onCreate(android.os.Bundle saved){super.onCreate(null);fixtureCreated=true;viewsReady=true;receiveOrRestore(getIntent(),getLastNonConfigurationInstance());}
 public void editForTest(String text){session.replace(text);setText(text);}
 public void clearForTest(){wipe();}
 public long beginForTest(){return session.begin();}
 public boolean finishForTest(long ticket){return session.finish(ticket,ShareSession.State.FINDING);}
 @SuppressWarnings("unchecked") public <T extends View> T findViewById(int id){if(!fixtureCreated)throw new AssertionError("Premature diagnostic UI read");return (T)(id==R.id.editor?editor:status);}
'''+receive+new_intent+methods+lifecycle+'}\n'
        files={
            'com/aitrustid/android/IntakeActivityBase.java':base,
            'com/aitrustid/android/CheckActivity.java':(ROOT/'tests/android/CheckActivity.java').read_text(),
            'com/aitrustid/android/ShareSession.java':(ROOT/'mobile/android/src/com/aitrustid/android/ShareSession.java').read_text(),
            'com/aitrustid/android/ConfigurationDraft.java':(ROOT/'mobile/android/src/com/aitrustid/android/ConfigurationDraft.java').read_text(),
            'com/aitrustid/android/ConfigurationLifecycleHarness.java':(ROOT/'tests/android/ConfigurationLifecycleHarness.java').read_text(),
            'com/aitrustid/android/R.java':'package com.aitrustid.android; class R {static class id {static final int editor=1,status=2;}}',
            'android/os/Bundle.java':'package android.os; public class Bundle {}',
            'android/content/ClipData.java':'package android.content; public class ClipData {public int getItemCount(){return 1;} public Item getItemAt(int n){return new Item();} public static class Item {public Object getUri(){return null;}}}',
            'android/content/Intent.java':'''package android.content; public class Intent {
 public static final String ACTION_MAIN="android.intent.action.MAIN",ACTION_SEND="android.intent.action.SEND",EXTRA_STREAM="stream",EXTRA_TEXT="text";
 private String action,type;private CharSequence text;
 public Intent(String action){this.action=action;}public String getAction(){return action;}
 public Intent setType(String type){this.type=type;return this;}public String getType(){return type;}
 public Intent putExtra(String key,String value){text=value;return this;}public boolean hasExtra(String key){return false;}
 public Object getData(){return null;}public ClipData getClipData(){return null;}public CharSequence getCharSequenceExtra(String key){return text;}
}''',
            'android/view/View.java':'package android.view; public class View {public static final int VISIBLE=0,GONE=8;public void setVisibility(int value){} public void setEnabled(boolean value){} public void clearFocus(){} public Object getWindowToken(){return null;}}',
            'android/widget/TextView.java':'package android.widget; public class TextView extends android.view.View {private String text="";public void setText(String value){text=value;}public CharSequence getText(){return text;}public int length(){return text.length();}}',
            'android/widget/EditText.java':'package android.widget; public class EditText extends TextView {}',
            'android/widget/Button.java':'package android.widget; public class Button extends TextView {}',
            'android/view/inputmethod/InputMethodManager.java':'package android.view.inputmethod; public class InputMethodManager {public void hideSoftInputFromWindow(Object token,int flags){}}',
            'android/app/Activity.java':'''package android.app; public class Activity {
 public static final String INPUT_METHOD_SERVICE="input";private android.content.Intent intent;public boolean changing=false,finishing=false;public Object lastNonConfig;
 public android.content.Intent getIntent(){return intent;} public void setIntent(android.content.Intent value){intent=value;}
 public Object getSystemService(String name){return new android.view.inputmethod.InputMethodManager();}
 public boolean isChangingConfigurations(){return changing;}
 public boolean isFinishing(){return finishing;}public Object getLastNonConfigurationInstance(){return lastNonConfig;}
 public Object onRetainNonConfigurationInstance(){return null;}protected void onUserLeaveHint(){}
 public void onCreate(android.os.Bundle b){} protected void onNewIntent(android.content.Intent i){}
 protected void onResume(){}protected void onPause(){}protected void onStop(){}protected void onDestroy(){}
 public <T extends android.view.View> T findViewById(int id){return null;}
 public void dump(String p,java.io.FileDescriptor f,java.io.PrintWriter w,String[] args){w.println("DEFAULT_DUMP");}
 protected void onSaveInstanceState(android.os.Bundle b){}
}''',
            'com/aitrustid/android/IntakeHarness.java':'''package com.aitrustid.android;
import android.content.Intent;import android.widget.TextView;import java.io.PrintWriter;
public class IntakeHarness {
 static void require(boolean ok){if(!ok)throw new AssertionError("Finite JVM control failed");}
 public static void main(String[] args){
  CheckActivity first=new CheckActivity();
  first.setIntent(new Intent(Intent.ACTION_SEND).setType("text/plain").putExtra(Intent.EXTRA_TEXT,"PRIVATE_SYNTHETIC_CANARY"));
  first.onCreate(null);first.onResume();
  require(((TextView)first.findViewById(R.id.status)).getText().toString().startsWith("Text received."));
  // This handoff is taken from Android16 ActivityThread, not an Android VM run.
  Intent custom=first.getIntent();require(Intent.ACTION_MAIN.equals(custom.getAction()));
  first.changing=true;first.onPause();first.onStop();Object retained=first.onRetainNonConfigurationInstance();first.onDestroy();
  CheckActivity recreated=new CheckActivity();recreated.setIntent(custom);recreated.lastNonConfig=retained;recreated.onCreate(new android.os.Bundle());recreated.onResume();
  require(((TextView)recreated.findViewById(R.id.status)).getText().toString().startsWith("Text received."));
  require(((TextView)recreated.findViewById(R.id.editor)).length()>0);
  if(args.length>0&&"overflow".equals(args[0])){for(int i=0;i<50;i++)recreated.onResume();}
  if(args.length>0&&("main".equals(args[0])||"pause".equals(args[0]))){
   recreated.onNewIntent(new Intent(Intent.ACTION_SEND).setType("text/plain").putExtra(Intent.EXTRA_TEXT,"PRIVATE_SECOND_SYNTHETIC_CANARY"));
   if("main".equals(args[0])){
    recreated.onNewIntent(new Intent(Intent.ACTION_MAIN));
    require("Ready when you are.".contentEquals(((TextView)recreated.findViewById(R.id.status)).getText()));
   }else{
    recreated.onPause();recreated.onResume();
    require("Cleared. Your text and result are no longer shown.".contentEquals(((TextView)recreated.findViewById(R.id.status)).getText()));
   }
   require(((TextView)recreated.findViewById(R.id.editor)).length()==0);
  }
  recreated.dump("",null,new PrintWriter(System.out,true),new String[]{args.length>0&&"unknown".equals(args[0])?"PRIVATE_ARGUMENT_CANARY":"aitrust-intake-v1"});
 }
}''',
        }
        with tempfile.TemporaryDirectory(prefix='aitrust-intake-jvm-') as temporary:
            home=Path(temporary);paths=[]
            for name,text in files.items():
                path=home/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(text);paths.append(path)
            result=subprocess.run([str(self.home/'bin/javac'),'--release','8','-encoding','UTF-8','-d',str(home/'classes'),*[str(p) for p in paths]],capture_output=True,timeout=30)
            self.assertEqual(result.returncode,0,result.stderr.decode())
            for extra in ([],['overflow'],['main'],['pause'],['unknown']):
                result=subprocess.run([str(self.home/'bin/java'),'-ea','-cp',str(home/'classes'),'com.aitrustid.android.IntakeHarness',*extra],capture_output=True,timeout=10)
                self.assertEqual(result.returncode,0,result.stderr.decode())
                self.assertNotIn(b'PRIVATE',result.stdout)
                observed=driver.intake_probe_observation(result.stdout)
                if extra==['unknown']:
                    self.assertEqual(observed['state'],'UNAVAILABLE');continue
                self.assertEqual(observed['state'],'OBSERVED');self.assertEqual(observed['instances'],2)
                self.assertEqual(observed['truncated'],extra==['overflow'])
                self.assertIn([1,'CREATE_BEGIN','SEND',False,'UNBUILT',False],observed['events'])
                self.assertIn([1,'CREATE_END','MAIN',True,'RECEIVED',False],observed['events'])
                self.assertIn([1,'DESTROY_BEGIN','MAIN',False,'CLEARED',True],observed['events'])
                self.assertIn([2,'CREATE_END','MAIN',True,'RECEIVED',False],observed['events'])
                if extra==['main']:self.assertEqual(observed['events'][-1],[2,'NEW_INTENT_END','MAIN',False,'READY',False])
                if extra==['pause']:self.assertEqual(observed['events'][-1],[2,'RESUME_END','MAIN',False,'CLEARED',False])
            result=subprocess.run([str(self.home/'bin/java'),'-ea','-cp',str(home/'classes'),'com.aitrustid.android.ConfigurationLifecycleHarness'],capture_output=True,timeout=10)
            self.assertEqual(result.returncode,0,result.stderr.decode())
            self.assertEqual(json.loads(result.stdout),{'pass':True,'modeled_lifecycle_controls':19,'android_runtime':False})
            # Reintroduce exactly the old pre-create UI read. The actual wrapper
            # must fail the spy before it can process any supplied text.
            wrapper=home/'com/aitrustid/android/CheckActivity.java'
            corrected=wrapper.read_text();anchor='recordFixed("CREATE_BEGIN",getIntent(),false,"UNBUILT",false);'
            self.assertEqual(corrected.count(anchor),1)
            wrapper.write_text(corrected.replace(anchor,'record("CREATE_BEGIN",getIntent());',1))
            result=subprocess.run([str(self.home/'bin/javac'),'--release','8','-cp',str(home/'classes'),'-d',str(home/'classes'),str(wrapper)],capture_output=True,timeout=30)
            self.assertEqual(result.returncode,0,result.stderr.decode())
            result=subprocess.run([str(self.home/'bin/java'),'-ea','-cp',str(home/'classes'),'com.aitrustid.android.IntakeHarness'],capture_output=True,timeout=10)
            self.assertNotEqual(result.returncode,0)
            self.assertIn(b'Premature diagnostic UI read',result.stderr)
            self.assertNotIn(b'PRIVATE',result.stderr+result.stdout)


if __name__=='__main__':unittest.main()
