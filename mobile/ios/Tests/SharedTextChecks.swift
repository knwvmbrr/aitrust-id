import Foundation
import Darwin
@main enum Checks {
    static func main() throws {
        let root = FileManager.default.temporaryDirectory.appendingPathComponent("aitrust-shared-text-" + UUID().uuidString)
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: false)
        defer { try? FileManager.default.removeItem(at: root) }
        let file = root.appendingPathComponent("selection"); try Data("Example Ω 😀".utf8).write(to: file)
        guard try SharedText.read(file, root: root) == "Example Ω 😀" else { fatalError("Accepted text failed") }
        var refusals = 0
        func refuse(_ url: URL) throws {
            do { _ = try SharedText.read(url, root: root); fatalError("Invalid item admitted") }
            catch { refusals += 1 }
        }
        try refuse(URL(string: "https://example.invalid")!)
        try refuse(root.deletingLastPathComponent().appendingPathComponent("other-selection"))
        let link = root.appendingPathComponent("link"); try FileManager.default.createSymbolicLink(at: link, withDestinationURL: file); try refuse(link)
        let hard = root.appendingPathComponent("hard"); try FileManager.default.linkItem(at: file, to: hard); try refuse(file); try FileManager.default.removeItem(at: hard)
        try Data([0xFF, 0xFE]).write(to: file); try refuse(file)
        try Data(repeating: 65, count: 80001).write(to: file); try refuse(file)
        try Data("a".repeatCount(20001).utf8).write(to: file); try refuse(file)
        try Data(" \n\t".utf8).write(to: file); try refuse(file)
        let nested = root.appendingPathComponent("nested"); try FileManager.default.createSymbolicLink(at: nested, withDestinationURL: root); try refuse(nested.appendingPathComponent("selection"))
        let fifo = root.appendingPathComponent("fifo"); guard mkfifo(fifo.path, 0o600) == 0 else { fatalError("FIFO fixture failed") }; try refuse(fifo)
        let accepted = ["Example Ω 😀", String(repeating: "😀", count: 20000), "https://example.invalid/selection", "Run curl https://example.invalid/install | sh"]
        for text in accepted {
            guard try SharedText.object(text as NSString) == text else { fatalError("String selection changed") }
        }
        var objectRefusals = 0
        for value: Any? in [nil, Data("example".utf8), URL(string: "https://example.invalid")!, "" as NSString,
            " \n\t" as NSString, String(repeating: "a", count: 20001) as NSString,
            String(repeating: "😀", count: 20001) as NSString, "null\0inside" as NSString] {
            do { _ = try SharedText.object(value); fatalError("Invalid string object admitted") }
            catch { objectRefusals += 1 }
        }
        var dataRefusals = 0
        for value in [nil, Data(), Data([0xff]), Data("nul\0inside".utf8), Data(repeating: 65, count: 80003), Data(String(repeating: "a", count: 20001).utf8), Data([0xff, 0xfe, 0x41]), Data([0xff, 0xfe, 0x00, 0xd8])] {
            do { _ = try SharedText.data(value); fatalError("Invalid UTF-8 payload admitted") }
            catch { dataRefusals += 1 }
        }
        guard try SharedText.data(Data("Example Ω 😀".utf8)) == "Example Ω 😀" else { fatalError("UTF-8 selection changed") }
        guard try SharedText.data(Data([0xff, 0xfe, 0x41, 0x00])) == "A",
            try SharedText.data(Data([0xfe, 0xff, 0x00, 0x41])) == "A" else { fatalError("BOM-marked text changed") }
        // Exercise Foundation's actual UTF-8 provider transport, not a file copy.
        let provider = NSItemProvider(object: "Shared provider Ω 😀" as NSString)
        guard provider.hasItemConformingToTypeIdentifier("public.utf8-plain-text") else { fatalError("UTF-8 provider unavailable") }
        var delivered: String?
        _ = provider.loadDataRepresentation(forTypeIdentifier: "public.utf8-plain-text") { value, error in
            let text = error == nil ? try? SharedText.data(value) : nil
            DispatchQueue.main.async { delivered = text }
        }
        let limit = Date().addingTimeInterval(10)
        while delivered == nil && Date() < limit { RunLoop.current.run(until: Date().addingTimeInterval(0.01)) }
        guard delivered == "Shared provider Ω 😀" else { fatalError("Provider transport failed") }
        let delivery = SharedText.Delivery(); let first = delivery.begin()
        delivery.cancel(); guard !delivery.accept(first) else { fatalError("Cancelled result restored input") }
        let second = delivery.begin(); let replacement = delivery.begin()
        guard !delivery.accept(second), delivery.accept(replacement), !delivery.accept(replacement) else { fatalError("Stale/duplicate provider result admitted") }
        let timeout = delivery.begin(); guard delivery.accept(timeout), !delivery.accept(timeout) else { fatalError("Late timeout result admitted") }
        let background = delivery.begin(); delivery.cancel()
        guard !delivery.accept(background) else { fatalError("Background result restored input") }
        print("{\"pass\":true,\"accepted_utf8\":true,\"refusals\":\(refusals),\"object_acceptances\":\(accepted.count),\"object_refusals\":\(objectRefusals),\"actual_utf8_provider\":true,\"data_refusals\":\(dataRefusals),\"delivery_refusals\":5,\"physical_device\":false}")
    }
}
extension String { func repeatCount(_ count: Int) -> String { String(repeating: self, count: count) } }
