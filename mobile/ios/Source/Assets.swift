import Foundation
import WebKit
import CryptoKit

/// Exact public bundle resources; no file, network or input-bearing URL fallback.
final class Assets: NSObject, WKURLSchemeHandler {
    private static let paths: Set<String> = ["/index.html", "/bridge.mjs", "/method.py", "/device-manifest.json", "/runtime/pyodide.mjs", "/runtime/pyodide.asm.mjs", "/runtime/pyodide.asm.wasm", "/runtime/python_stdlib.zip", "/runtime/pyodide-lock.json"]
    private static func fingerprint(_ value: String) -> Bool {
        value.count == 64 && value.allSatisfy { "0123456789abcdef".contains($0) }
    }
    private let folder: URL
    private let hashes: [String: String]
    let methodHash: String
    init(bundle: Bundle = .main) throws {
        guard let folder = bundle.url(forResource: "Assets", withExtension: nil),
              let configuration = try JSONSerialization.jsonObject(with: Data(contentsOf: folder.appendingPathComponent("native-assets.json"))) as? [String: Any],
              Set(configuration.keys) == ["format", "method_sha256", "bundle_sha256", "hashes"],
              configuration["format"] as? String == "ai-trust-id-native-assets/v1",
              let hashes = configuration["hashes"] as? [String: String],
              let methodHash = configuration["method_sha256"] as? String,
              Self.fingerprint(methodHash), Set(hashes.keys) == Self.paths, hashes.values.allSatisfy(Self.fingerprint),
              hashes["/method.py"] == configuration["bundle_sha256"] as? String,
              !hashes.isEmpty else { throw AssetError.refused }
        self.folder = folder; self.hashes = hashes; self.methodHash = methodHash
        super.init()
    }
    enum AssetError: Error { case refused }
    func resource(_ request: URLRequest) throws -> (Data, String) {
        guard let url = request.url, request.httpMethod == "GET",
              request.httpBody == nil, request.httpBodyStream == nil,
              url.absoluteString == "aitrust-asset://bundle" + url.path,
              let expected = hashes[url.path], expected.count == 64 else { throw AssetError.refused }
        let file = folder.appendingPathComponent(String(url.path.dropFirst()))
        var parent = file.deletingLastPathComponent()
        while parent.path.hasPrefix(folder.path) {
            guard try parent.resourceValues(forKeys: [.isSymbolicLinkKey]).isSymbolicLink != true else { throw AssetError.refused }
            if parent == folder { break }; parent.deleteLastPathComponent()
        }
        let values = try file.resourceValues(forKeys: [.isRegularFileKey, .isSymbolicLinkKey])
        guard values.isRegularFile == true, values.isSymbolicLink != true else { throw AssetError.refused }
        let data = try Data(contentsOf: file)
        guard SHA256.hash(data: data).map({ String(format: "%02x", $0) }).joined() == expected else { throw AssetError.refused }
        let types = ["html": "text/html", "mjs": "text/javascript", "py": "text/plain", "wasm": "application/wasm", "json": "application/json", "zip": "application/zip"]
        return (data, types[url.pathExtension] ?? "application/octet-stream")
    }
    func webView(_ webView: WKWebView, start task: WKURLSchemeTask) {
        do {
            let (data, mime) = try resource(task.request)
            guard let url = task.request.url, let response = HTTPURLResponse(url: url, statusCode: 200, httpVersion: "HTTP/1.1", headerFields: ["Content-Type": mime, "Access-Control-Allow-Origin": "*"]) else { throw AssetError.refused }
            task.didReceive(response); task.didReceive(data); task.didFinish()
        } catch { task.didFailWithError(AssetError.refused) }
    }
    func webView(_ webView: WKWebView, stop task: WKURLSchemeTask) {}
}
