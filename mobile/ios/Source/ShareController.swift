import UIKit
import UniformTypeIdentifiers

@objc(ShareController) final class ShareController: CheckerController {
    private let delivery = SharedText.Delivery()
    override func viewDidLoad() {
        shareMode = true; super.viewDidLoad(); status.text = "Loading selected text…"
        let items = extensionContext?.inputItems.compactMap { $0 as? NSExtensionItem } ?? []
        let providers = items.flatMap { $0.attachments ?? [] }
        guard items.count == 1 else { status.text = "Share one item at a time."; return }
        guard providers.count == 1 else { status.text = "Choose one text selection to share."; return }
        let profiles = [UTType.utf8PlainText.identifier, UTType.plainText.identifier, UTType.text.identifier]
        guard let profile = profiles.first(where: { providers[0].hasItemConformingToTypeIdentifier($0) }) else {
            status.text = "This sharing app did not offer a supported text format."; return
        }
        let request = delivery.begin()
        // Some activity providers serialize their public.text representation;
        // loadItem asks the provider for the typed object, not its archive bytes.
        // This compatibility API remains available on the supported SDK, although
        // deprecated in iOS 27. URL/file objects are deliberately never opened.
        providers[0].loadItem(forTypeIdentifier: profile, options: nil) { [weak self] value, error in
            let parse: () throws -> String = {
                if error != nil { throw SharedText.Refusal.unsupported }
                if let data = value as? Data { return try SharedText.data(data) }
                return try SharedText.object(value)
            }
            let text: String?
            let refusal: String
            do {
                text = try parse(); refusal = ""
            } catch SharedText.Refusal.missing { text = nil; refusal = "No text arrived from the sharing app." }
              catch SharedText.Refusal.encoding { text = nil; refusal = "The selection is not supported text. Try copying just the words." }
              catch SharedText.Refusal.empty { text = nil; refusal = "The selection is empty. Select the words and try again." }
              catch SharedText.Refusal.tooLong { text = nil; refusal = "Choose a shorter selection, up to 20,000 characters." }
              catch SharedText.Refusal.nullCharacter { text = nil; refusal = "The selection contains a control character. Try copying just the words." }
              catch { text = nil; refusal = "The sharing app could not provide the text. Select the words and try again." }
            DispatchQueue.main.async {
                guard let self, self.delivery.accept(request) else { return }
                guard let text else {
                    self.status.text = refusal; return
                }
                self.input.text = text; self.status.text = "Review the selection, then choose Check with PS."
            }
        }
        DispatchQueue.main.asyncAfter(deadline: .now() + 10) { [weak self] in
            guard let self, self.delivery.accept(request) else { return }
            self.status.text = "The selection did not arrive. Cancel and try another plain-text selection."
        }
    }
    override func textViewDidChange(_ textView: UITextView) {
        delivery.cancel()
        super.textViewDidChange(textView)
    }
    override func clear() { delivery.cancel(); super.clear() }
}
