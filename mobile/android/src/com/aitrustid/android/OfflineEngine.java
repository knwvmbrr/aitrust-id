package com.aitrustid.android;

import android.app.Activity;
import android.net.Uri;
import android.os.Handler;
import android.os.Looper;
import android.os.SystemClock;
import android.webkit.WebResourceRequest;
import android.webkit.WebResourceResponse;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.webkit.RenderProcessGoneDetail;
import android.view.View;
import android.widget.LinearLayout;
import org.json.JSONObject;
import org.json.JSONTokener;
import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.security.MessageDigest;
import java.util.Collections;
import java.util.HashMap;
import java.util.Iterator;
import java.util.Map;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/** No JS-to-native interface; only native-initiated evaluation of verified local code. */
final class OfflineEngine {
    interface Listener { void ready(); void result(JSONObject value); void unavailable(); }
    private static final String ORIGIN = "https://appassets.androidplatform.net";
    private static final String INDEX = ORIGIN + "/assets/index.html";
    private static final long STARTUP_MS = 30000, CHECK_MS = 5000;
    private final Activity activity;
    private final LinearLayout host;
    private final Listener listener;
    private final Handler handler = new Handler(Looper.getMainLooper());
    private final ExecutorService verifier = Executors.newSingleThreadExecutor();
    private volatile boolean stopped = false;
    private Map<String, JSONObject> entries = Collections.emptyMap();
    private WebView web;
    private long deadline;
    private Runnable timeout;

    OfflineEngine(Activity activity, LinearLayout host, Listener listener) {
        this.activity=activity; this.host=host; this.listener=listener;
    }
    void start() {
        deadline=SystemClock.elapsedRealtime()+STARTUP_MS;
        timeout=this::fail; handler.postDelayed(timeout,STARTUP_MS);
        verifier.submit(() -> {
            try {
                byte[] raw=read("asset-manifest.json",65536);
                if(!sha(raw).equals(BuildIdentity.ASSET_MANIFEST_SHA256))throw new Exception();
                JSONObject inventory=new JSONObject(new String(raw,"UTF-8"));
                if(!inventory.getString("format").equals("ai-trust-id-android-assets/v1")||
                   !inventory.getString("method_sha256").equals(BuildIdentity.METHOD_SHA256))throw new Exception();
                JSONObject hashes=inventory.getJSONObject("files");
                if(hashes.length()!=9)throw new Exception();
                Map<String,JSONObject> checked=new HashMap<>(); long total=0;
                Iterator<String> names=hashes.keys();
                while(names.hasNext()){
                    String name=names.next();
                    if(!name.matches("(?:index\\.html|bridge\\.mjs|method\\.py|device-manifest\\.json|runtime/(?:pyodide\\.mjs|pyodide\\.asm\\.mjs|pyodide\\.asm\\.wasm|python_stdlib\\.zip|pyodide-lock\\.json))"))throw new Exception();
                    JSONObject row=hashes.getJSONObject(name); int size=row.getInt("bytes");
                    if(size<=0||size>33554432||(total+=size)>67108864)throw new Exception();
                    byte[] data=read(name,size);
                    if(data.length!=size||!sha(data).equals(row.getString("sha256")))throw new Exception();
                    checked.put(name,row);
                }
                handler.post(() -> {if(!stopped){entries=Collections.unmodifiableMap(checked);open();}});
            } catch(Exception error){handler.post(this::fail);}
            finally {verifier.shutdown();}
        });
    }
    private byte[] read(String name,int limit) throws Exception {
        try(InputStream in=activity.getAssets().open(name);ByteArrayOutputStream out=new ByteArrayOutputStream()){
            byte[] buffer=new byte[16384]; int count;
            while((count=in.read(buffer))!=-1){if(out.size()+count>limit)throw new Exception();out.write(buffer,0,count);}
            return out.toByteArray();
        }
    }
    private static String sha(byte[] raw) throws Exception {
        byte[] digest=MessageDigest.getInstance("SHA-256").digest(raw); StringBuilder value=new StringBuilder();
        for(byte b:digest)value.append(String.format(java.util.Locale.ROOT,"%02x",b&255));return value.toString();
    }
    private WebResourceResponse blocked(){return new WebResourceResponse("text/plain","UTF-8",403,"Blocked",Collections.emptyMap(),new ByteArrayInputStream(new byte[0]));}
    private WebResourceResponse asset(WebResourceRequest request){
        Uri uri=request.getUrl();
        if(stopped||!"GET".equals(request.getMethod())||!"https".equals(uri.getScheme())||
           !"appassets.androidplatform.net".equals(uri.getHost())||uri.getPort()!=-1||uri.getUserInfo()!=null||
           uri.getQuery()!=null||uri.getFragment()!=null||uri.getEncodedPath()==null||!uri.getEncodedPath().startsWith("/assets/"))return blocked();
        String name=uri.getEncodedPath().substring(8);JSONObject row=entries.get(name);
        if(row==null)return blocked();
        try{
            byte[] raw=read(name,row.getInt("bytes"));if(!sha(raw).equals(row.getString("sha256")))return blocked();
            String mime=name.endsWith(".mjs")?"text/javascript":name.endsWith(".wasm")?"application/wasm":name.endsWith(".html")?"text/html":name.endsWith(".json")?"application/json":name.endsWith(".zip")?"application/zip":"text/plain";
            Map<String,String> headers=new HashMap<>();headers.put("Cache-Control","no-store");headers.put("X-Content-Type-Options","nosniff");
            return new WebResourceResponse(mime,"UTF-8",200,"OK",headers,new ByteArrayInputStream(raw));
        }catch(Exception error){return blocked();}
    }
    @SuppressWarnings("deprecation") private void open(){
        if(stopped)return;
        WebView.setWebContentsDebuggingEnabled(false);
        web=new WebView(activity);web.setVisibility(View.INVISIBLE);host.addView(web,new LinearLayout.LayoutParams(1,1));
        WebSettings settings=web.getSettings();settings.setJavaScriptEnabled(true);
        settings.setAllowFileAccess(false);settings.setAllowContentAccess(false);
        settings.setAllowFileAccessFromFileURLs(false);settings.setAllowUniversalAccessFromFileURLs(false);
        settings.setBlockNetworkLoads(true);settings.setMixedContentMode(WebSettings.MIXED_CONTENT_NEVER_ALLOW);
        settings.setDomStorageEnabled(false);settings.setDatabaseEnabled(false);settings.setCacheMode(WebSettings.LOAD_NO_CACHE);
        settings.setSaveFormData(false);settings.setSupportMultipleWindows(false);settings.setJavaScriptCanOpenWindowsAutomatically(false);
        android.webkit.CookieManager.getInstance().setAcceptCookie(false);
        web.setWebViewClient(new WebViewClient(){
            @Override public WebResourceResponse shouldInterceptRequest(WebView view,WebResourceRequest request){return asset(request);}
            @Override public boolean shouldOverrideUrlLoading(WebView view,WebResourceRequest request){return true;}
            @Override public void onPageFinished(WebView view,String url){if(INDEX.equals(url))poll();else fail();}
            @Override public boolean onRenderProcessGone(WebView view,RenderProcessGoneDetail detail){fail();return true;}
        });
        web.loadUrl(INDEX);
    }
    private void poll(){
        if(stopped)return;
        if(SystemClock.elapsedRealtime()>=deadline){fail();return;}
        web.evaluateJavascript("window.AndroidPS ? window.AndroidPS.state : 'booting'",raw -> {
            if(stopped)return;
            if("\"ready\"".equals(raw)){
                if(web.getWebViewRenderProcess()==null){fail();return;}
                handler.removeCallbacks(timeout);listener.ready();
            }
            else if("\"unavailable\"".equals(raw))fail();
            else handler.postDelayed(this::poll,100);
        });
    }
    void check(String input){
        if(stopped||web==null||!ShareSession.validText(input)){fail();return;}
        timeout=this::fail;handler.postDelayed(timeout,CHECK_MS);
        String expression="JSON.stringify(window.AndroidPS.check("+JSONObject.quote(input).replace("\u2028","\\u2028").replace("\u2029","\\u2029")+"))";
        web.evaluateJavascript(expression,raw -> {
            if(stopped)return;
            handler.removeCallbacks(timeout);
            try{
                if(raw==null||raw.length()>131072)throw new Exception();
                Object value=new JSONTokener(raw).nextValue();
                if(!(value instanceof String))throw new Exception();
                JSONObject result=new JSONObject((String)value);
                if(result.length()!=7)throw new Exception();
                for(String key:new String[]{"format","state","method_sha256","normalization_id"})
                    if(!(result.get(key) instanceof String))throw new Exception();
                if(!Boolean.FALSE.equals(result.get("independently_validated"))||!Boolean.FALSE.equals(result.get("redaction_performed"))||!(result.get("matches") instanceof org.json.JSONArray))throw new Exception();
                if(!"ai-trust-id-android-summary/v1".equals(result.getString("format"))||
                   !BuildIdentity.METHOD_SHA256.equals(result.getString("method_sha256"))||
                   !"NFC-Unicode-15.0.0/v1".equals(result.getString("normalization_id"))||
                   result.getBoolean("independently_validated")||result.getBoolean("redaction_performed"))throw new Exception();
                if(!"FINDING".equals(result.getString("state"))&&!"NO_FINDING".equals(result.getString("state")))throw new Exception();
                if(result.getJSONArray("matches").length()>10||("FINDING".equals(result.getString("state"))!=(result.getJSONArray("matches").length()>0)))throw new Exception();
                for(int i=0;i<result.getJSONArray("matches").length();i++){
                    JSONObject match=result.getJSONArray("matches").getJSONObject(i);
                    if(match.length()!=3||!(match.get("reason") instanceof String)||!(match.get("excerpt") instanceof String)||!(match.get("truncated") instanceof Boolean))throw new Exception();
                    String reason=match.getString("reason");
                    if(!java.util.Arrays.asList("Downloads code and passes it straight to a shell to run.","Puts downloaded output into a command that runs it.","Hands downloaded code to a shell to run.","Inserts downloaded output into a command that runs it.","Passes encoded content to eval or exec, which can run code.").contains(reason)||match.getString("excerpt").codePointCount(0,match.getString("excerpt").length())>320)throw new Exception();
                }
                listener.result(result);
            }catch(Exception error){fail();}
        });
    }
    private void fail(){if(!stopped){stop();listener.unavailable();}}
    void stop(){
        if(stopped)return;stopped=true;handler.removeCallbacksAndMessages(null);verifier.shutdownNow();
        WebView retiring=web;web=null;
        if(retiring!=null){
            host.removeView(retiring);
            // A renderer-loss callback means this WebView may already reject
            // normal methods. Teardown must still leave native review usable.
            try{
                android.webkit.WebViewRenderProcess process=retiring.getWebViewRenderProcess();
                if(process!=null)process.terminate();
            }catch(RuntimeException unavailable){ /* Already dead or unavailable. */ }
            finally{try{retiring.destroy();}catch(RuntimeException alreadyGone){ /* No view remains mounted. */ }}
        }
        entries=Collections.emptyMap();
    }
}
