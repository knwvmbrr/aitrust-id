package com.aitrustid.android;

import android.app.Activity;
import android.content.ClipData;
import android.content.Intent;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.os.Bundle;
import android.text.Editable;
import android.text.InputFilter;
import android.text.TextWatcher;
import android.view.View;
import android.view.WindowManager;
import android.view.inputmethod.EditorInfo;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import org.json.JSONArray;
import org.json.JSONObject;

public final class CheckActivity extends Activity {
    private final ShareSession session=new ShareSession();
    private LinearLayout column;
    private EditText editor;
    private TextView status,tag,details;
    private Button check,cancel,more;
    private OfflineEngine engine;
    private boolean settingText=false,detailsOpen=false;
    private String evidence="";
    private int dp(int value){return Math.round(value*getResources().getDisplayMetrics().density);}
    @SuppressWarnings("deprecation") private int color(int id){return getResources().getColor(id);}
    private TextView text(String value,int size){
        TextView view=new TextView(this);view.setText(value);view.setTextSize(size);view.setTextColor(color(R.color.ink));
        view.setPadding(0,dp(8),0,dp(8));view.setLineSpacing(dp(2),1);return view;
    }
    private Button button(String value,int id){
        Button view=new Button(this);view.setText(value);view.setAllCaps(false);view.setMinHeight(dp(48));
        view.setId(id);view.setTextColor(color(R.color.ink));return view;
    }
    @Override public void onCreate(Bundle saved){
        super.onCreate(null);getWindow().addFlags(WindowManager.LayoutParams.FLAG_SECURE);
        getWindow().setSoftInputMode(WindowManager.LayoutParams.SOFT_INPUT_ADJUST_RESIZE|WindowManager.LayoutParams.SOFT_INPUT_STATE_ALWAYS_HIDDEN);
        ScrollView scroll=new ScrollView(this);scroll.setFillViewport(true);scroll.setBackgroundColor(color(R.color.page));
        column=new LinearLayout(this);column.setOrientation(LinearLayout.VERTICAL);column.setFocusableInTouchMode(true);
        column.setPadding(dp(22),dp(22),dp(22),dp(24));column.setBackgroundResource(R.drawable.camouflage);
        scroll.addView(column);setContentView(scroll);
        // Preserve content access below edge-to-edge system bars without fixed notch assumptions.
        column.setOnApplyWindowInsetsListener((view,insets)->{
            view.setPadding(dp(22)+insets.getSystemWindowInsetLeft(),dp(22)+insets.getSystemWindowInsetTop(),
                dp(22)+insets.getSystemWindowInsetRight(),dp(24)+insets.getSystemWindowInsetBottom());return insets;
        });
        TextView title=text("AI TRUST ID",25);title.setTypeface(Typeface.create("sans-serif-medium",Typeface.NORMAL));
        if(android.os.Build.VERSION.SDK_INT>=28)title.setAccessibilityHeading(true);column.addView(title);
        column.addView(text("Check a command",23));
        column.addView(text("PS looks for a few ways commands download and run code. Review the text, then tap Check.",16));
        TextView label=text("Your text",16);label.setLabelFor(R.id.editor);column.addView(label);
        editor=new EditText(this);editor.setId(R.id.editor);editor.setMinLines(5);editor.setMaxLines(12);
        editor.setGravity(android.view.Gravity.TOP|android.view.Gravity.START);editor.setTextSize(17);
        editor.setTextColor(color(R.color.ink));editor.setHintTextColor(color(R.color.muted));
        editor.setHint("Share text from another app, or paste it here.");editor.setPadding(dp(12),dp(12),dp(12),dp(12));
        GradientDrawable panel=new GradientDrawable();panel.setColor(color(R.color.panel));panel.setCornerRadius(dp(14));panel.setStroke(dp(1),color(R.color.line));editor.setBackground(panel);
        editor.setSaveEnabled(false);editor.setFreezesText(false);editor.setImportantForAutofill(View.IMPORTANT_FOR_AUTOFILL_NO_EXCLUDE_DESCENDANTS);
        editor.setInputType(android.text.InputType.TYPE_CLASS_TEXT|android.text.InputType.TYPE_TEXT_FLAG_MULTI_LINE|android.text.InputType.TYPE_TEXT_FLAG_NO_SUGGESTIONS);
        editor.setImeOptions(EditorInfo.IME_FLAG_NO_PERSONALIZED_LEARNING|EditorInfo.IME_FLAG_NO_EXTRACT_UI);
        editor.setFilters(new InputFilter[]{(source,start,end,dest,dstart,dend)->{
            String proposed=dest.subSequence(0,dstart).toString()+source.subSequence(start,end)+dest.subSequence(dend,dest.length());
            if(proposed.codePointCount(0,proposed.length())>ShareSession.MAX_CODEPOINTS){status.setText("Keep the text under 20,001 characters. The extra text was not added.");return "";}return null;
        }});
        column.addView(editor,new LinearLayout.LayoutParams(-1,dp(180)));
        TextView privacy=text("Stays on this device. Text and results clear when this screen pauses, including some system dialogs.",14);privacy.setTextColor(color(R.color.muted));column.addView(privacy);
        LinearLayout actions=new LinearLayout(this);actions.setOrientation(LinearLayout.HORIZONTAL);
        check=button("Check PS",R.id.check);Button clear=button("Clear",R.id.clear);cancel=button("Cancel check",R.id.cancel);
        actions.addView(check,new LinearLayout.LayoutParams(0,-2,1));actions.addView(clear,new LinearLayout.LayoutParams(0,-2,1));column.addView(actions);
        column.addView(cancel);cancel.setVisibility(View.GONE);
        status=text("Ready when you are.",17);status.setId(R.id.status);status.setAccessibilityLiveRegion(View.ACCESSIBILITY_LIVE_REGION_POLITE);column.addView(status);
        tag=text("PS",14);tag.setId(R.id.tag);tag.setTypeface(Typeface.DEFAULT_BOLD);tag.setPadding(dp(12),dp(5),dp(12),dp(5));
        GradientDrawable chip=new GradientDrawable();chip.setColor(color(R.color.panel));chip.setCornerRadius(dp(9));chip.setStroke(dp(1),color(R.color.line));tag.setBackground(chip);
        column.addView(tag,new LinearLayout.LayoutParams(-2,-2));tag.setVisibility(View.GONE);
        more=button("Why this tag",View.generateViewId());column.addView(more);more.setVisibility(View.GONE);
        details=text("",15);details.setId(R.id.details);details.setTextIsSelectable(true);column.addView(details);details.setVisibility(View.GONE);
        TextView limit=text("PS preview. No finding is not a safety clearance. This check does not identify scams, intent or every unsafe command.",14);limit.setTextColor(color(R.color.muted));column.addView(limit);
        Button done=button("Done",View.generateViewId());column.addView(done);done.setOnClickListener(v->{wipe();finish();});
        check.setOnClickListener(v->startCheck());clear.setOnClickListener(v->wipe());
        cancel.setOnClickListener(v->{stopEngine();session.cancel();resetResult();status.setText("Check canceled. You can edit the text or try again.");refresh();});
        more.setOnClickListener(v->{detailsOpen=!detailsOpen;details.setVisibility(detailsOpen?View.VISIBLE:View.GONE);more.setText(detailsOpen?"Hide details":"Why this tag");});
        editor.addTextChangedListener(new TextWatcher(){public void beforeTextChanged(CharSequence s,int st,int c,int a){}public void onTextChanged(CharSequence s,int st,int before,int count){}public void afterTextChanged(Editable value){if(!settingText){stopEngine();session.replace(value.toString());resetResult();status.setText("Text changed. Tap Check for a new result.");refresh();}}});
        receive(getIntent());
    }
    private void receive(Intent intent){
        stopEngine();session.clear();setText("");resetResult();
        editor.clearFocus();
        ((android.view.inputmethod.InputMethodManager)getSystemService(INPUT_METHOD_SERVICE)).hideSoftInputFromWindow(editor.getWindowToken(),0);
        try{
            if(intent==null||Intent.ACTION_MAIN.equals(intent.getAction())){status.setText("Ready when you are.");refresh();return;}
            if(!Intent.ACTION_SEND.equals(intent.getAction())||!"text/plain".equals(intent.getType())||intent.hasExtra(Intent.EXTRA_STREAM)||intent.getData()!=null)throw new IllegalArgumentException();
            ClipData clip=intent.getClipData();if(clip!=null&&(clip.getItemCount()!=1||clip.getItemAt(0).getUri()!=null))throw new IllegalArgumentException();
            CharSequence value=intent.getCharSequenceExtra(Intent.EXTRA_TEXT);
            if(value==null||value.length()>40000||!ShareSession.validText(value.toString()))throw new IllegalArgumentException();
            String supplied=value.toString();session.replace(supplied);setText(supplied);status.setText("Text received. Review it, then tap Check.");
        }catch(RuntimeException unsupported){status.setText("Share one plain-text item, up to 20,000 characters. Files and multiple items are not supported.");}
        finally{setIntent(new Intent(Intent.ACTION_MAIN));refresh();}
    }
    @Override protected void onNewIntent(Intent intent){super.onNewIntent(intent);receive(intent);}
    private void setText(String value){settingText=true;editor.setText(value);settingText=false;}
    private void resetResult(){evidence="";detailsOpen=false;details.setText("");details.setVisibility(View.GONE);more.setVisibility(View.GONE);more.setText("Why this tag");tag.setVisibility(View.GONE);}
    private void refresh(){check.setEnabled(ShareSession.validText(session.text())&&session.state()!=ShareSession.State.CHECKING);cancel.setVisibility(session.state()==ShareSession.State.CHECKING?View.VISIBLE:View.GONE);}
    private void startCheck(){
        stopEngine();resetResult();final long ticket;
        try{ticket=session.begin();}catch(IllegalStateException invalid){status.setText("Add one plain-text item first.");return;}
        status.setText("Preparing the offline check…");refresh();
        engine=new OfflineEngine(this,column,new OfflineEngine.Listener(){
            public void ready(){if(session.current(ticket)&&engine!=null){status.setText("Checking PS…");engine.check(session.text());}}
            public void unavailable(){if(session.finish(ticket,ShareSession.State.UNAVAILABLE)){engine=null;status.setText("PS is unavailable. No result was issued. You can try again.");refresh();}}
            public void result(JSONObject value){
                if(!session.current(ticket))return;
                try{
                    boolean finding="FINDING".equals(value.getString("state"));
                    JSONArray matches=value.getJSONArray("matches");StringBuilder lines=new StringBuilder();
                    for(int i=0;i<matches.length();i++){JSONObject match=matches.getJSONObject(i);if(i>0)lines.append("\n\n");lines.append(match.getString("reason")).append("\n").append(match.getString("excerpt"));if(match.getBoolean("truncated"))lines.append("…");}
                    String parsedEvidence=lines.toString();
                    if(!session.finish(ticket,finding?ShareSession.State.FINDING:ShareSession.State.NO_FINDING))return;
                    if(finding){
                        tag.setVisibility(View.VISIBLE);status.setText("Review before running this command.");
                        evidence=parsedEvidence;details.setText(evidence);more.setVisibility(View.VISIBLE);
                    }else status.setText("No supported command pattern found. This does not mean the command is safe.");
                }catch(Exception invalid){session.finish(ticket,ShareSession.State.UNAVAILABLE);status.setText("PS is unavailable. No result was issued.");resetResult();}
                finally{stopEngine();refresh();}
            }
        });
        engine.start();
    }
    private void stopEngine(){if(engine!=null){engine.stop();engine=null;}}
    private void wipe(){stopEngine();session.clear();setText("");resetResult();status.setText("Cleared. Your text and result are no longer shown.");refresh();}
    @Override protected void onPause(){wipe();super.onPause();}
    @Override protected void onStop(){wipe();super.onStop();}
    @Override protected void onDestroy(){stopEngine();session.clear();super.onDestroy();}
    @Override protected void onSaveInstanceState(Bundle state){super.onSaveInstanceState(state);state.clear();}
}
