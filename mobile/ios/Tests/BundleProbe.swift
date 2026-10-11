// Verification executable only; never linked into the personal app or Share extension.
import UIKit
import WebKit

@main final class BundleProbe: UIResponder, UIApplicationDelegate, WKScriptMessageHandler, WKNavigationDelegate {
    var window: UIWindow?, web: WKWebView?, assets: Assets?
    var wrote = false
    func application(_ application: UIApplication, didFinishLaunchingWithOptions options: [UIApplication.LaunchOptionsKey: Any]? = nil) -> Bool {
        do {
            let resources = try Assets(); assets = resources
            let config = WKWebViewConfiguration(); config.websiteDataStore = .nonPersistent()
            config.setURLSchemeHandler(resources, forURLScheme: "aitrust-asset")
            config.userContentController.add(self, name: "lifecycle")
            let child = WKWebView(frame: .zero, configuration: config); web = child; child.navigationDelegate = self
            let controller = UIViewController(); controller.view = child
            let window = UIWindow(frame: CGRect(x: 0, y: 0, width: 430, height: 932)); window.rootViewController = controller; window.makeKeyAndVisible(); self.window = window
            child.load(URLRequest(url: URL(string: "aitrust-asset://bundle/index.html")!))
            DispatchQueue.main.asyncAfter(deadline: .now() + 90) { self.write(["pass": false, "stage": "deadline"]) }
        } catch { write(["pass": false, "stage": "resource_configuration"]) }
        return true
    }
    func webView(_ webView: WKWebView, decidePolicyFor action: WKNavigationAction, decisionHandler: @escaping (WKNavigationActionPolicy) -> Void) {
        decisionHandler(action.request.url?.absoluteString == "aitrust-asset://bundle/index.html" ? .allow : .cancel)
    }
    func userContentController(_ controller: WKUserContentController, didReceive message: WKScriptMessage) {
        guard message.webView === web, let state = message.body as? [String: String], state["state"] == "ready", let child = web, let assets else { write(["pass": false, "stage": "bridge_startup"]); return }
        do {
            var refusals = 0
            for path in ["https://example.invalid/", "file:///private/input", "aitrust-asset://other/method.py", "aitrust-asset://bundle/method.py?q=input", "aitrust-asset://bundle/method.py#input", "aitrust-asset://bundle/%6dethod.py", "aitrust-asset://bundle/../private", "aitrust-asset://bundle/unknown.py"] {
                do { _ = try assets.resource(URLRequest(url: URL(string: path)!)); throw ProbeError.failed }
                catch Assets.AssetError.refused { refusals += 1 }
            }
            var post = URLRequest(url: URL(string: "aitrust-asset://bundle/method.py")!); post.httpMethod = "POST"
            do { _ = try assets.resource(post); throw ProbeError.failed } catch Assets.AssetError.refused { refusals += 1 }
            var body = URLRequest(url: post.url!); body.httpBody = Data("input".utf8)
            do { _ = try assets.resource(body); throw ProbeError.failed } catch Assets.AssetError.refused { refusals += 1 }
            let method = Bundle.main.bundleURL.appendingPathComponent("Assets/method.py")
            let original = try Data(contentsOf: method)
            // Owned disposable probe bundle only, then restore before runtime use.
            try (original + Data("\nchanged".utf8)).write(to: method)
            do { _ = try assets.resource(URLRequest(url: post.url!)); try original.write(to: method); throw ProbeError.failed }
            catch Assets.AssetError.refused { try original.write(to: method); refusals += 1 }
            let rows = try JSONSerialization.jsonObject(with: Data(contentsOf: Bundle.main.bundleURL.appendingPathComponent("cases.json")))
            child.callAsyncJavaScript("""
                const canonical=value=>JSON.stringify(value,(_,item)=>item && typeof item==='object' && !Array.isArray(item) ? Object.fromEntries(Object.keys(item).sort().map(key=>[key,item[key]])) : item);
                let count=0;
                for(const row of rows){
                    const result=window.checkAnswer(row.text);
                    if(canonical(result)!==canonical(row.expected))throw Error('Parity');
                    count++;
                }
                let invalid=0;
                for(const value of ['', ' ', 'a'.repeat(20001), '😀'.repeat(20001), null]){
                    try{window.checkAnswer(value);}catch{invalid++;}
                }
                if(invalid!==5)throw Error('Bounds');
                const before=document.body.textContent;
                window.checkAnswer("__import__('js').document.body.textContent='DO_NOT_EXECUTE_INPUT'");
                if(document.body.textContent!==before)throw Error('Input execution');
                let networkRefused=false;
                try{await fetch('https://example.invalid/verification-only');}catch{networkRefused=true;}
                if(!networkRefused)throw Error('CSP');
                return {pass:true,case_count:count,input_refusals:invalid,input_not_executed:true,remote_fetch_refused:true};
                """, arguments: ["rows": rows], in: nil, in: .page) { outcome in
                    guard case .success(let value) = outcome, var result = value as? [String: Any] else { self.write(["pass": false, "stage": "parity_and_controls"]); return }
                    result["resource_refusals"] = refusals; result["method_sha256"] = assets.methodHash
                    result["physical_device"] = false; result["independent_accuracy"] = false
                    self.write(result)
                }
        } catch { write(["pass": false, "stage": "native_controls"]) }
    }
    enum ProbeError: Error { case failed }
    func write(_ value: Any) {
        guard !wrote else { return }; wrote = true
        let file = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0].appendingPathComponent("proof.json")
        if let data = try? JSONSerialization.data(withJSONObject: value, options: [.sortedKeys]) { try? data.write(to: file, options: [.withoutOverwriting]) }
    }
}
