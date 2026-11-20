package com.aitrustid.android;

/** Pure state controller: no Android, storage, network or detector dependency. */
public final class ShareSession {
    public static final int MAX_CODEPOINTS = 20000;
    public enum State { EMPTY, REVIEW, CHECKING, FINDING, NO_FINDING, UNAVAILABLE }
    private String text = "";
    private long revision = 0;
    private State state = State.EMPTY;
    public static boolean validText(String value) {
        if (value == null || value.length() > MAX_CODEPOINTS * 2 || value.isEmpty()) return false;
        for (int i = 0; i < value.length(); i++) {
            char c = value.charAt(i);
            if (Character.isHighSurrogate(c)) {
                if (++i >= value.length() || !Character.isLowSurrogate(value.charAt(i))) return false;
            } else if (Character.isLowSurrogate(c)) return false;
        }
        boolean visible=false;
        for (int offset=0;offset<value.length();) {
            int cp=value.codePointAt(offset);offset+=Character.charCount(cp);
            if (!Character.isWhitespace(cp) && !Character.isSpaceChar(cp) && cp!=0x85) visible=true;
        }
        return visible && value.codePointCount(0, value.length()) <= MAX_CODEPOINTS;
    }
    public void replace(String value) {
        revision++;
        text = value == null ? "" : value;
        state = validText(text) ? State.REVIEW : State.EMPTY;
    }
    public long begin() {
        if (!validText(text) || state == State.CHECKING) throw new IllegalStateException("No supported review input");
        state = State.CHECKING;
        return ++revision;
    }
    public boolean finish(long ticket, State result) {
        if (ticket != revision || state != State.CHECKING) return false;
        if (result != State.FINDING && result != State.NO_FINDING && result != State.UNAVAILABLE)
            throw new IllegalArgumentException("Unsupported result state");
        state = result;
        return true;
    }
    public void cancel() { revision++; state = validText(text) ? State.REVIEW : State.EMPTY; }
    public void clear() { revision++; text = ""; state = State.EMPTY; }
    public boolean current(long ticket) { return revision == ticket && state == State.CHECKING; }
    public String text() { return text; }
    public State state() { return state; }
}
