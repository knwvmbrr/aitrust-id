package com.aitrustid.android;

import android.content.Intent;
import android.os.Bundle;
import android.widget.EditText;
import android.widget.TextView;
import java.io.FileDescriptor;
import java.io.PrintWriter;
import java.util.ArrayList;

/** Explicit diagnostic APK only. Never compiled into the default application. */
public final class CheckActivity extends IntakeActivityBase {
    private static final int LIMIT=32;
    private static final ArrayList<String> events=new ArrayList<String>();
    private static int instances=0;
    private static boolean truncated=false;
    private final int instance=nextInstance();

    private static synchronized int nextInstance(){
        if(instances<255)return ++instances;
        truncated=true;return 255;
    }
    private static String action(Intent intent){
        if(intent==null)return "NONE";
        if(Intent.ACTION_SEND.equals(intent.getAction()))return "SEND";
        if(Intent.ACTION_MAIN.equals(intent.getAction()))return "MAIN";
        return "OTHER";
    }
    private void record(String callback,Intent delivered){
        EditText editor=findViewById(R.id.editor);
        TextView status=findViewById(R.id.status);
        String state="UNBUILT";
        if(status!=null){
            CharSequence value=status.getText();
            if("Ready when you are.".contentEquals(value))state="READY";
            else if("Text received. Review it, then tap Check.".contentEquals(value))state="RECEIVED";
            else if("Cleared. Your text and result are no longer shown.".contentEquals(value))state="CLEARED";
            else state="OTHER";
        }
        // Every string inserted below is a code-owned enum, never a subject value.
        String row="["+instance+",\""+callback+"\",\""+action(delivered)+"\","+
            (editor!=null&&editor.length()>0)+",\""+state+"\","+isChangingConfigurations()+"]";
        synchronized(CheckActivity.class){
            if(events.size()<LIMIT)events.add(row);else truncated=true;
        }
    }
    @Override public void onCreate(Bundle saved){
        record("CREATE_BEGIN",getIntent());super.onCreate(saved);record("CREATE_END",getIntent());
    }
    @Override protected void onNewIntent(Intent intent){
        record("NEW_INTENT_BEGIN",intent);super.onNewIntent(intent);record("NEW_INTENT_END",getIntent());
    }
    @Override protected void onResume(){
        record("RESUME_BEGIN",getIntent());super.onResume();record("RESUME_END",getIntent());
    }
    @Override protected void onPause(){
        record("PAUSE_BEGIN",getIntent());super.onPause();record("PAUSE_END",getIntent());
    }
    @Override protected void onStop(){
        record("STOP_BEGIN",getIntent());super.onStop();record("STOP_END",getIntent());
    }
    @Override protected void onDestroy(){
        record("DESTROY_BEGIN",getIntent());super.onDestroy();record("DESTROY_END",getIntent());
    }
    @Override protected void onSaveInstanceState(Bundle state){
        record("SAVE_BEGIN",getIntent());super.onSaveInstanceState(state);record("SAVE_END",getIntent());
    }
    @Override public void dump(String prefix,FileDescriptor fd,PrintWriter writer,String[] args){
        if(args==null||args.length!=1||!"aitrust-intake-v1".equals(args[0])){
            super.dump(prefix,fd,writer,args);return;
        }
        synchronized(CheckActivity.class){
            writer.print(prefix+"AITRUST_INTAKE_V1:{\"schema\":1,\"instances\":"+instances+
                ",\"truncated\":"+truncated+",\"events\":[");
            for(int i=0;i<events.size();i++){if(i>0)writer.print(",");writer.print(events.get(i));}
            writer.println("]}");
        }
    }
}
