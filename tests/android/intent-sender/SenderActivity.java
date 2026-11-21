package com.aitrustid.synthetic;

import android.app.Activity;
import android.content.ClipData;
import android.content.ComponentName;
import android.content.Intent;
import android.net.Uri;
import android.os.Bundle;

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
    @Override public void onCreate(Bundle saved){
        super.onCreate(null);
        // Only an enumerated integer is read. Nothing from the incoming intent
        // can replace a synthetic payload, recipient, URI or permission flags.
        try{startActivity(selected(getIntent().getIntExtra("selection",-1)));}
        finally{finish();}
    }
}
