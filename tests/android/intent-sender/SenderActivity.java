package com.aitrustid.synthetic;

import android.app.Activity;
import android.content.ClipData;
import android.content.ComponentName;
import android.content.Intent;
import android.net.Uri;
import android.os.Bundle;
import java.io.FileDescriptor;
import java.io.PrintWriter;

/** CI-only synthetic sender. Never reads caller text, paths, URIs or targets. */
public final class SenderActivity extends Activity {
    static final String MARKER="owned synthetic ingress marker";
    static Intent selected(int selection){
        if(selection<0||selection>9)throw new IllegalArgumentException("Unsupported synthetic selection");
        Intent send=new Intent(Intent.ACTION_SEND);
        send.setComponent(new ComponentName("com.aitrustid.android","com.aitrustid.android.CheckActivity"));
        send.setType("text/plain");send.putExtra(Intent.EXTRA_TEXT,MARKER);
        Uri inert=Uri.parse("content://synthetic.invalid/item");
        switch(selection){
            case 0:break;
            case 1:send.removeExtra(Intent.EXTRA_TEXT);break;
            case 2:send.removeExtra(Intent.EXTRA_TEXT);send.putExtra(Intent.EXTRA_TEXT,17);break;
            case 3:send.setAction(Intent.ACTION_SEND_MULTIPLE);break;
            case 4:send.putExtra(Intent.EXTRA_STREAM,inert);break;
            case 5:send.setDataAndType(inert,"text/plain");break;
            case 6:send.setClipData(new ClipData("synthetic",new String[]{"text/uri-list"},new ClipData.Item(inert)));break;
            case 7:
                ClipData clip=ClipData.newPlainText("synthetic",MARKER);
                clip.addItem(new ClipData.Item("owned second synthetic item"));send.setClipData(clip);break;
            case 8:
                char[] oversized=new char[20001];java.util.Arrays.fill(oversized,'x');
                send.putExtra(Intent.EXTRA_TEXT,new String(oversized));break;
            case 9:send.putExtra(Intent.EXTRA_TEXT,new String(new char[]{'x','\ud800'}));break;
            default:throw new IllegalArgumentException("Unsupported synthetic selection");
        }
        return send;
    }
    private int counter=0,lastSelection=-1;
    private String outcome="NONE",callback="NONE";
    private synchronized void dispatch(Intent delivered,String from){
        if(counter>=32){lastSelection=-1;outcome="LIMIT";return;}
        counter++;lastSelection=-1;callback=from;outcome="START_REFUSED";
        try{
            int selection=delivered==null?-1:delivered.getIntExtra("selection",-1);
            if(selection<0||selection>9)return;
            lastSelection=selection;
            startActivity(selected(selection));outcome="START_RETURNED";
        }catch(RuntimeException unsupported){outcome="START_REFUSED";}
        finally{setIntent(new Intent(Intent.ACTION_MAIN));}
    }
    @Override public void onCreate(Bundle saved){
        super.onCreate(null);dispatch(getIntent(),"CREATE");
    }
    @Override protected void onNewIntent(Intent delivered){
        super.onNewIntent(delivered);dispatch(delivered,"NEW_INTENT");
    }
    @Override public synchronized void dump(String prefix,FileDescriptor fd,PrintWriter writer,String[] args){
        if(args==null||args.length!=1||!"synthetic-ingress-v1".equals(args[0])){
            super.dump(prefix,fd,writer,args);return;
        }
        // Only code-owned enums and a bounded counter; never general Intent data.
        writer.println(prefix+"AITRUST_SYNTHETIC_V1:{\"schema\":1,\"counter\":"+counter+
            ",\"selection\":"+lastSelection+",\"outcome\":\""+outcome+"\",\"callback\":\""+callback+"\"}");
        lastSelection=-1;outcome="NONE";callback="NONE";
    }
}
