"""Inert chooser driver controls and real JDK construction; not Android execution."""
import ast
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
import zipfile
from unittest import mock
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,ROOT/path)
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value
m=load('chooser_controls','scripts/android-chooser-controls.py')
driver=load('chooser_parent','scripts/verify-android-emulator.py')

def node(root,package,rid='',text='',enabled=True,bounds='[10,20][110,80]',description=''):
    return ET.SubElement(root,'node',{'package':package,'resource-id':package+':id/'+rid,
        'text':text,'enabled':str(enabled).lower(),'bounds':bounds,'content-desc':description})

def view(state,fault=None):
    root=ET.Element('hierarchy')
    if state.startswith('source'):
        count=int(state[-1]);shown=count
        if fault=='source_counter' and count==1:shown=0
        if fault=='cancel_no_resume' and count==2:shown=1
        node(root,m.SOURCE,text='Chooser source ready '+str(shown),description='owned chooser source state')
        node(root,m.SOURCE,text='Share fixed sample',enabled=count<2,bounds='[10,100][150,180]',description='owned chooser share button')
    elif state.startswith('picker'):
        if fault=='missing_target':return root
        package='private.foreign.app' if fault=='foreign_target' else 'android'
        target=node(root,package,text='AI Trust ID',bounds='[200,300][400,500]')
        if fault=='duplicate_target':ET.SubElement(root,'node',dict(target.attrib))
        if fault=='inert_target':target.set('enabled','false')
    else:
        first=state in ('receive','finding');cancel=state=='cancel_revival'
        editor=m.FIRST if first else m.SECOND if cancel else m.HINT
        if fault=='wrong_sample' and state=='receive':editor='PRIVATE_INPUT_CANARY'
        if fault=='unknown_hint' and state=='cleared':editor='PRIVATE_HINT_CANARY'
        if fault=='retained_first' and state=='cleared':editor=m.FIRST
        node(root,m.PACKAGE,'editor',editor)
        node(root,m.PACKAGE,'status',m.RECEIVED if state=='receive' else m.FINDING if state=='finding' else m.CLEARED)
        if fault!='missing_check':node(root,m.PACKAGE,'check','Check PS',first or fault=='enabled_clear',bounds='[10,200][150,260]')
        if state=='finding' or fault=='automatic_result':node(root,m.PACKAGE,'tag','FI' if fault=='wrong_tag' else 'PS')
        if fault=='stale_details':node(root,m.PACKAGE,'details','PRIVATE_RESULT_CANARY')
    return root

class ChooserStateMachine(unittest.TestCase):
    def exercise(self,fault=None):
        report={};state='source0';count=0;calls=[];waits=[]
        def shell(args,timeout=10):
            nonlocal state,count
            calls.append(args)
            if args[:3]==['am','start','-W']:
                state='source'+str(count);return b'PRIVATE_START_HEADER'
            if args[:2]==['input','tap']:
                if state.startswith('source'):count+=1;state='picker'+str(count)
                elif state.startswith('picker'):state='receive'
                elif state=='receive':state='finding'
                else:raise AssertionError('Unexpected tap')
                if fault=='bypass_picker' and state.startswith('picker'):state='receive'
                return b''
            if args==['dumpsys','activity','activities']:
                prefix='mLastResumedActivity=' if fault=='historical_task' else 'topResumedActivity='
                component='private.foreign/.Other' if fault=='foreign_task' else 'com.aitrustid.android/.CheckActivity'
                return ('PRIVATE_DUMP_HEADER\n  '+prefix+'ActivityRecord{123abc u0 '+component+' t42}\n').encode()
            if args==['input','keyevent','4']:state='source2';return b''
            if args[:3]==['am','task','focus']:
                self.assertEqual(args,['am','task','focus','42']);state='cancel_revival' if fault=='cancel_revival' else 'cleared';return b''
            raise AssertionError('Unexpected command')
        def wait(predicate):
            waits.append(state);root=view(state,fault)
            if not predicate(root):raise ValueError('PRIVATE_TIMEOUT_CANARY')
            return root
        try:m.verify_cases(shell,wait,report)
        except m.ChooserControlRefusal as error:return report,calls,waits,error
        return report,calls,waits,None

    def test_real_system_target_path_then_cancel_refocus_without_new_checker_intent(self):
        report,calls,waits,error=self.exercise();self.assertIsNone(error)
        self.assertEqual(report['status'],'EXECUTED');self.assertTrue(report['pass']);self.assertEqual(report['case_count'],2)
        self.assertEqual(waits,['source0','picker1','receive','finding','source1','picker2','source2','cleared'])
        self.assertEqual([c for c in calls if c[:3]==['am','start','-W']], [['am','start','-W','-n',m.SOURCE_COMPONENT]]*2)
        self.assertEqual(calls[-2:],[['input','keyevent','4'],['am','task','focus','42']])
        self.assertEqual(len([c for c in calls if c[:2]==['input','tap']]),4)
        raw=json.dumps(report)
        for secret in ['PRIVATE_',m.FIRST,m.SECOND,'t42','[200,300]']:self.assertNotIn(secret,raw)

    def test_missing_foreign_ambiguous_or_bypassed_system_route_cannot_pass(self):
        for fault in ['missing_target','foreign_target','duplicate_target','inert_target','bypass_picker']:
            with self.subTest(fault=fault):
                report,calls,waits,error=self.exercise(fault)
                self.assertIsInstance(error,m.ChooserControlRefusal);self.assertEqual(error.code,'chooser_system_target_unavailable')
                self.assertFalse(report['pass']);self.assertEqual(report['case_count'],0)
                self.assertNotIn('PRIVATE_',json.dumps(report)+str(error))

    def test_exact_sample_explicit_check_result_and_task_are_mandatory(self):
        for fault in ['wrong_sample','automatic_result','wrong_tag','historical_task','foreign_task','missing_check','stale_details']:
            with self.subTest(fault=fault):
                report,calls,waits,error=self.exercise(fault)
                self.assertIsInstance(error,m.ChooserControlRefusal);self.assertFalse(report['pass']);self.assertEqual(report['case_count'],0)
                self.assertNotIn('PRIVATE_',json.dumps(report)+str(error))

    def test_cancel_requires_positive_source_return_and_exact_empty_checker(self):
        for fault in ['source_counter','cancel_no_resume','cancel_revival','retained_first','enabled_clear','unknown_hint']:
            with self.subTest(fault=fault):
                report,calls,waits,error=self.exercise(fault)
                self.assertIsInstance(error,m.ChooserControlRefusal);self.assertFalse(report['pass']);self.assertEqual(report['case_count'],1)
                if fault in ('source_counter','cancel_no_resume'):self.assertFalse(any(c[:3]==['am','task','focus'] for c in calls))
                self.assertNotIn('PRIVATE_',json.dumps(report)+str(error))

class OwnedBoundaries(unittest.TestCase):
    def test_task_uses_only_single_exact_resumed_record_not_history(self):
        valid=b'PRIVATE_FIELDS\n topResumedActivity=ActivityRecord{123abc u0 com.aitrustid.android/.CheckActivity t42}\n'
        self.assertEqual(m.checker_task(valid),42)
        for raw in [b'',valid*2,valid.replace(b'u0',b'u10'),valid.replace(b't42',b't0'),valid.replace(b't42',b't42 f}'),valid.replace(b'topResumedActivity',b'mLastResumedActivity'),valid.replace(b'.CheckActivity',b'.OtherActivity'),valid+b' topResumedActivity=ActivityRecord{1 u0 foreign.app/.Other t2}\n',b'\xff',b'x'*524289]:
            with self.assertRaises(ValueError) as error:m.checker_task(raw)
            self.assertNotIn('PRIVATE_',str(error.exception))

    def test_bounds_unique_package_and_enabled_state_are_required(self):
        for bounds in ['', '[0,0][0,20]','[-1,0][10,20]','[0,0][99999,20]','[0,0][20,10]PRIVATE']:
            root=ET.Element('hierarchy');n=node(root,m.SOURCE,bounds=bounds)
            with self.assertRaises(ValueError):m.center(n)
        root=ET.Element('hierarchy');node(root,m.PACKAGE,'editor');node(root,m.PACKAGE,'editor')
        with self.assertRaises(ValueError):m.observe(root)

    def test_default_dex_uid_portrait_and_source_drift_refuse_safely(self):
        boundary=load('chooser_inert_boundary','scripts/android-intent-controls.py')
        for fault in ['default_leak','default_malformed','same_uid','portrait','source_drift']:
            report={};wait=mock.Mock()
            def shell(args,timeout=10):
                if args[0]=='pm':return ('package:'+args[-1]+' uid:'+('10042' if fault=='same_uid' or args[-1]==m.SOURCE else '10041')+'\n').encode()
                if args==['wm','user-rotation']:return b'free\n' if fault=='portrait' else b'lock 0\n'
                raise AssertionError('Unexpected command')
            boundary.dex_bytes=mock.Mock(side_effect=zipfile.BadZipFile('PRIVATE_ARCHIVE_CANARY')) if fault=='default_malformed' else lambda path:boundary.CHOOSER_DEX if fault=='default_leak' else b'ordinary'
            spec=mock.Mock();spec.loader.exec_module=lambda mod:None
            identity=mock.Mock(side_effect=[{'f':'a'},{'f':'b'}]) if fault=='source_drift' else mock.Mock(return_value={'f':'a'})
            with mock.patch.object(m.importlib.util,'spec_from_file_location',return_value=spec),mock.patch.object(m.importlib.util,'module_from_spec',return_value=boundary),mock.patch.object(m,'source_identity',identity),mock.patch.object(m,'verify_cases') as cases:
                with self.assertRaises(m.ChooserControlRefusal):m.run_controls(Path('/not-read'),shell,wait,report)
                if fault!='source_drift':cases.assert_not_called()
            self.assertFalse(report['pass']);self.assertNotIn('PRIVATE_',json.dumps(report))

    def test_lazy_import_failure_and_unknown_diagnostic_never_leak(self):
        for error in [ImportError('PRIVATE_IMPORT_CANARY'),type('Fault',(ValueError,),{'code':'PRIVATE_CODE'})('PRIVATE_MESSAGE')]:
            report={}
            with mock.patch.object(driver.importlib.util,'spec_from_file_location',side_effect=error):
                with self.assertRaises(driver.AndroidChooserRefusal) as caught:driver.verify_chooser_controls(None,None,None,report)
            self.assertEqual(caught.exception.code,'chooser_workflow_unavailable');self.assertEqual(report,{'status':'FAILED','pass':False})

    def test_original_seven_config_two_and_invalid_pairs_unchanged(self):
        source=(ROOT/'scripts/verify-android-emulator.py').read_text();tree=ast.parse(source)
        expected={'verify_share_controls':'ae33c0b4175732b8eab516123e104ea2cfc93dc4d19984cf2eb58517c7227ab7',
            'verify_background_clear':'0d25c47bdabe7b57b2aa937792ba72e34323d035d06167ece20332ae439220aa',
            'verify_configuration_controls':'4b5ed8cd7631d013b078614abfa49cf63918dc1e037bccb4fe30a6face128ba8',
            'wait':'ca25559a2aa7f3aeb49e5210744dc93b6a079562da3310ec113025ae37c96141'}
        for name,wanted in expected.items():
            rows=[n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name==name]
            self.assertEqual(len(rows),1);self.assertEqual(hashlib.sha256(ast.get_source_segment(source,rows[0]).encode()).hexdigest(),wanted)
        # Exact source-segment identities from reviewed3941603, not a Git-history dependency.
        # This guard must work in a clean source ZIP and depth-one CI checkout.
        original={'verify_cases':'90f7ac9b6d4a2ca0b00707608c8bb1dbc095d4d1ea6474c0349462cc65923727',
            'parse_dispatch':'74cd207aeafcfa1ce6cde351a7d27dc1c6da358435fa391b39e8407c95e4cbc6',
            'observe':'830a3e14144832f2f5600f5f038673565d54f071488d89d280bbb48514dbbf6d',
            'installed_uid':'d149734e21223f1340a9d332cac6a15ee06d83d49b7f16642a3c43f6f5eaf313'}
        current=(ROOT/'scripts/android-intent-controls.py').read_text()
        def identities(raw):
            tree=ast.parse(raw);values={}
            for name in original:
                rows=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==name]
                self.assertEqual(len(rows),1)
                values[name]=hashlib.sha256(ast.get_source_segment(raw,rows[0]).encode()).hexdigest()
            return values
        with mock.patch.object(subprocess,'run',side_effect=AssertionError('Guard must not start Git or another process')):
            self.assertEqual(identities(current),original)
            weakened=current.replace("if value['result_tag_present'] or value['result_details_present']:","if False:",1)
            self.assertNotEqual(weakened,current)
            self.assertNotEqual(identities(weakened),original)

class ActualChooserJVM(unittest.TestCase):
    def test_real_jdk_constructs_only_two_untargeted_ui_triggered_chooser_intents(self):
        home=Path(os.environ.get('JAVA_HOME','/opt/homebrew/opt/openjdk@21'))
        if not(home/'bin/javac').is_file() or not(home/'bin/java').is_file():self.skipTest('Existing JDK unavailable; no JVM execution claimed')
        sources={
            'android/os/Bundle.java':'package android.os; public class Bundle {}',
            'android/util/DisplayMetrics.java':'package android.util; public class DisplayMetrics { public float density=1.0f; }',
            'android/content/res/Resources.java':'package android.content.res; public class Resources { public android.util.DisplayMetrics getDisplayMetrics(){return new android.util.DisplayMetrics();} }',
            'android/content/Intent.java':'''package android.content; import java.util.*; public class Intent { public static final String ACTION_SEND="SEND",ACTION_MAIN="MAIN",EXTRA_TEXT="TEXT";public static final int FLAG_ACTIVITY_NEW_TASK=0x10000000;public String action,type;public int flags;public Object component=null;public Intent target;public final HashMap<String,Object> extras=new HashMap<>();public Intent(String a){action=a;}public Intent setType(String t){type=t;return this;}public Intent putExtra(String k,String v){extras.put(k,v);return this;}public Intent addFlags(int f){flags|=f;return this;}public static Intent createChooser(Intent i,CharSequence t){Intent c=new Intent("CHOOSER");c.target=i;return c;} }''',
            'android/view/View.java':'''package android.view; public class View {public interface OnClickListener {void onClick(View v);}public OnClickListener listener;public boolean enabled=true;public String description;public void setContentDescription(CharSequence s){description=s.toString();}public void setEnabled(boolean b){enabled=b;}public void setOnClickListener(OnClickListener l){listener=l;} }''',
            'android/widget/TextView.java':'package android.widget; public class TextView extends android.view.View {public String text;public TextView(android.app.Activity a){}public void setText(CharSequence s){text=s.toString();}}',
            'android/widget/Button.java':'package android.widget; public class Button extends TextView {public Button(android.app.Activity a){super(a);}}',
            'android/widget/LinearLayout.java':'''package android.widget; import java.util.*; public class LinearLayout extends android.view.View {public static final int VERTICAL=1;public ArrayList<android.view.View> children=new ArrayList<>();public LinearLayout(android.app.Activity a){}public void setOrientation(int n){}public void setPadding(int a,int b,int c,int d){}public void addView(android.view.View v){children.add(v);} }''',
            'android/app/Activity.java':'''package android.app; import android.content.Intent; public class Activity {public Intent incoming=new Intent("PRIVATE_INPUT");public Intent launchedIntent;public int launches=0;public android.widget.LinearLayout content;public void onCreate(android.os.Bundle b){}protected void onResume(){}protected void onNewIntent(Intent i){}public void setIntent(Intent i){incoming=i;}public android.content.res.Resources getResources(){return new android.content.res.Resources();}public void setContentView(android.view.View v){content=(android.widget.LinearLayout)v;}public void startActivity(Intent i){launchedIntent=i;launches++;}}''',
            'com/aitrustid/synthetic/Harness.java':'''package com.aitrustid.synthetic; import android.content.Intent;import android.widget.*;public class Harness {static void ok(boolean b){if(!b)throw new AssertionError("fixed chooser mismatch");}public static void main(String[] a){for(int n:new int[]{0,3}){try{ChooserActivity.selected(n);throw new AssertionError();}catch(IllegalArgumentException expected){}}ChooserActivity c=new ChooserActivity();c.onCreate(null);c.onResume();ok(c.launches==0&&c.incoming.action.equals(Intent.ACTION_MAIN));TextView state=(TextView)c.content.children.get(0);Button b=(Button)c.content.children.get(1);ok(state.text.equals("Chooser source ready 0")&&b.enabled);for(int n=1;n<=2;n++){b.listener.onClick(b);ok(c.launches==n&&c.launchedIntent.action.equals("CHOOSER"));Intent target=c.launchedIntent.target;ok(target.action.equals(Intent.ACTION_SEND)&&target.type.equals("text/plain")&&target.component==null&&target.flags==Intent.FLAG_ACTIVITY_NEW_TASK&&target.extras.size()==1);ok(target.extras.get(Intent.EXTRA_TEXT).equals(n==1?ChooserActivity.FIRST:ChooserActivity.SECOND));ok(!b.enabled);c.onResume();ok(state.text.equals("Chooser source ready "+n));}c.onNewIntent(new Intent("PRIVATE_INPUT").putExtra("TEXT","PRIVATE_CANARY"));ok(c.launches==2&&c.incoming.extras.isEmpty());b.listener.onClick(b);ok(c.launches==2&&!b.enabled);System.out.println("SYNTHETIC_CHOOSER:2");}}'''}
        with tempfile.TemporaryDirectory() as p:
            stage=Path(p);files=[]
            for name,raw in sources.items():
                path=stage/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(raw);files.append(path)
            path=stage/'com/aitrustid/synthetic/ChooserActivity.java';path.write_bytes((ROOT/'tests/android/intent-sender/ChooserActivity.java').read_bytes());files.append(path)
            result=subprocess.run([str(home/'bin/javac'),'--release','8','-d',str(stage),*[str(p) for p in files]],capture_output=True,timeout=20)
            self.assertEqual(result.returncode,0,'Existing JDK fixed chooser compilation failed')
            result=subprocess.run([str(home/'bin/java'),'-cp',str(stage),'com.aitrustid.synthetic.Harness'],capture_output=True,timeout=10)
            self.assertEqual(result.returncode,0);self.assertEqual(result.stdout,b'SYNTHETIC_CHOOSER:2\n')

if __name__=='__main__':unittest.main()
