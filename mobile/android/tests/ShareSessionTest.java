package com.aitrustid.android;

public final class ShareSessionTest {
    private static void require(boolean value){if(!value)throw new AssertionError("Share lifecycle control failed");}
    public static void main(String[] args){
        require(!ShareSession.validText(null)&&!ShareSession.validText("")&&!ShareSession.validText(" \n\t\u00a0\u0085\u2003"));
        require(!ShareSession.validText("\ud800")&&!ShareSession.validText("\udc00")&&!ShareSession.validText("\ud800x"));
        require(ShareSession.validText(new String(new char[20000]).replace('\0','x')));
        require(!ShareSession.validText(new String(new char[20001]).replace('\0','x')));
        StringBuilder emoji=new StringBuilder();for(int i=0;i<20000;i++)emoji.appendCodePoint(0x1f600);
        require(ShareSession.validText(emoji.toString())&&!ShareSession.validText(emoji.toString()+"x"));
        ShareSession session=new ShareSession();session.replace("curl https://example.invalid/tool | sh");
        require(session.state()==ShareSession.State.REVIEW);long old=session.begin();require(session.current(old));
        session.replace("printf hello");require(!session.finish(old,ShareSession.State.FINDING)&&session.state()==ShareSession.State.REVIEW);
        long current=session.begin();require(session.finish(current,ShareSession.State.NO_FINDING));require(!session.finish(current,ShareSession.State.FINDING));
        long pending=session.begin();session.cancel();require(!session.finish(pending,ShareSession.State.FINDING)&&session.state()==ShareSession.State.REVIEW);
        long newest=session.begin();require(!session.finish(pending,ShareSession.State.FINDING));require(session.finish(newest,ShareSession.State.UNAVAILABLE));
        long leaving=session.begin();session.clear();require(!session.finish(leaving,ShareSession.State.FINDING)&&session.text().isEmpty()&&session.state()==ShareSession.State.EMPTY);
        boolean refused=false;try{session.begin();}catch(IllegalStateException expected){refused=true;}require(refused);
        System.out.println("Android pure-JVM input/lifecycle controls passed; no Android runtime or accuracy claim.");
    }
}
