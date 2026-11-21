package com.aitrustid.android;

import android.content.Intent;
import android.widget.TextView;

/** JVM only: actual extracted activity methods, explicitly modeled framework order. */
public final class ConfigurationLifecycleHarness {
    private static void need(boolean value){if(!value)throw new AssertionError("Lifecycle control failed");}
    private static String text(CheckActivity activity){return ((TextView)activity.findViewById(R.id.editor)).getText().toString();}
    private static CheckActivity create(String text,Object retained){
        CheckActivity activity=new CheckActivity();
        activity.setIntent(text==null?new Intent(Intent.ACTION_MAIN):share(text));
        activity.lastNonConfig=retained;activity.onCreate(null);return activity;
    }
    private static CheckActivity open(String text,Object retained){CheckActivity activity=create(text,retained);activity.onResume();return activity;}
    private static Intent share(String text){return new Intent(Intent.ACTION_SEND).setType("text/plain").putExtra(Intent.EXTRA_TEXT,text);}
    private static Object capture(CheckActivity old){
        old.changing=true;old.onPause();need(text(old).isEmpty());old.onStop();
        need(Intent.ACTION_MAIN.equals(old.getIntent().getAction()));
        return old.onRetainNonConfigurationInstance();
    }
    public static void main(String[] args){
        int controls=0;
        {
            CheckActivity old=open("owned first",null);old.editForTest("owned edited");
            Object holder=capture(old);need(holder instanceof ConfigurationDraft);
            CheckActivity next=open(null,holder);need("owned edited".equals(text(next)));
            need(((ConfigurationDraft)holder).take()==null);need(old.onRetainNonConfigurationInstance()==null);
            old.onDestroy();need("owned edited".equals(text(next)));controls++;
        }
        {
            CheckActivity current=open("owned one",null);
            for(int i=0;i<4;i++){
                String latest="owned edit "+i;current.editForTest(latest);Object holder=capture(current);
                CheckActivity next=open(null,holder);current.onDestroy();need(latest.equals(text(next)));current=next;
            }
            controls++;
        }
        {
            CheckActivity old=open("owned pending",null);long ticket=old.beginForTest();Object holder=capture(old);
            need(!old.finishForTest(ticket));CheckActivity next=open(null,holder);
            need("owned pending".equals(text(next)));need(next.beginForTest()>0);old.onDestroy();controls++;
        }
        {
            CheckActivity old=open("owned background",null);old.onPause();old.onStop();
            need(old.onRetainNonConfigurationInstance()==null);old.onResume();need(text(old).isEmpty());controls++;
        }
        {
            CheckActivity old=open("owned leave before pause",null);old.onUserLeaveHint();
            need(capture(old)==null);need(text(old).isEmpty());controls++;
        }
        {
            CheckActivity old=open("owned leave after pause",null);old.changing=true;old.onPause();old.onUserLeaveHint();old.onStop();
            need(old.onRetainNonConfigurationInstance()==null);controls++;
        }
        {
            CheckActivity old=open("owned leave after transfer",null);Object holder=capture(old);old.onUserLeaveHint();old.onDestroy();
            CheckActivity next=open(null,holder);need(text(next).isEmpty());controls++;
        }
        {
            CheckActivity old=open("owned HOME before new resume",null);Object holder=capture(old);old.onDestroy();
            CheckActivity next=create(null,holder);next.onUserLeaveHint();next.onStop();next.onResume();
            need(text(next).isEmpty());need(capture(next)==null);controls++;
        }
        {
            CheckActivity old=open("owned stopped successor",null);Object holder=capture(old);old.onDestroy();
            CheckActivity next=create(null,holder);next.onStop();next.onResume();need(text(next).isEmpty());controls++;
        }
        {
            CheckActivity old=open("owned cleared old",null);Object holder=capture(old);old.clearForTest();
            CheckActivity next=open(null,holder);need(text(next).isEmpty());old.onDestroy();controls++;
        }
        {
            CheckActivity old=open("owned cleared new",null);Object holder=capture(old);old.onDestroy();
            CheckActivity next=open(null,holder);next.clearForTest();need(capture(next)==null);need(text(next).isEmpty());controls++;
        }
        {
            CheckActivity old=open("owned previous",null);Object holder=capture(old);old.onDestroy();
            CheckActivity next=open("owned replacement",holder);need("owned replacement".equals(text(next)));
            need(((ConfigurationDraft)holder).take()==null);controls++;
        }
        {
            CheckActivity old=open("owned unsupported replacement",null);Object holder=capture(old);old.onDestroy();
            CheckActivity next=new CheckActivity();next.lastNonConfig=holder;
            next.setIntent(share("owned ignored").setType("image/png"));next.onCreate(null);next.onResume();
            need(text(next).isEmpty());need(((ConfigurationDraft)holder).take()==null);controls++;
        }
        {
            CheckActivity old=open("owned no holder",null);old.onUserLeaveHint();old.onPause();old.onStop();old.onDestroy();
            CheckActivity replacement=open(null,null);need(text(replacement).isEmpty());controls++;
        }
        {
            ConfigurationDraft holder=new ConfigurationDraft("owned null intent");CheckActivity next=new CheckActivity();
            next.lastNonConfig=holder;next.setIntent(null);next.onCreate(null);next.onResume();
            need(text(next).isEmpty());need(holder.take()==null);controls++;
        }
        {
            ConfigurationDraft holder=new ConfigurationDraft("owned unknown intent");CheckActivity next=new CheckActivity();
            next.lastNonConfig=holder;next.setIntent(new Intent("owned.unsupported.action"));next.onCreate(null);next.onResume();
            need(text(next).isEmpty());need(holder.take()==null);controls++;
        }
        {
            CheckActivity old=open("owned finishing",null);old.finishing=true;need(capture(old)==null);controls++;
        }
        {
            CheckActivity early=new CheckActivity();early.setIntent(new Intent(Intent.ACTION_MAIN));
            early.onUserLeaveHint();early.onCreate(null);early.onResume();need(text(early).isEmpty());controls++;
        }
        {
            ConfigurationDraft draft=new ConfigurationDraft("owned one use");need("owned one use".equals(draft.take()));need(draft.take()==null);
            draft=new ConfigurationDraft("owned revoked");draft.discard();need(draft.take()==null);
            for(String invalid:new String[]{null,""," ","\uD800"}){
                boolean refused=false;try{new ConfigurationDraft(invalid);}catch(IllegalArgumentException expected){refused=true;}need(refused);
            }
            controls++;
        }
        need(controls==19);
        System.out.println("{\"pass\":true,\"modeled_lifecycle_controls\":"+controls+",\"android_runtime\":false}");
    }
}
