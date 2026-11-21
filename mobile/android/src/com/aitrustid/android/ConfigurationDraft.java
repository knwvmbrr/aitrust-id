package com.aitrustid.android;

/** One-use in-process configuration handoff. No activity, result or serialization. */
final class ConfigurationDraft {
    private String text;
    ConfigurationDraft(String value){
        if(!ShareSession.validText(value))throw new IllegalArgumentException("Unsupported draft");
        text=value;
    }
    synchronized String take(){String value=text;text=null;return value;}
    synchronized void discard(){text=null;}
}
