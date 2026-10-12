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
        print("{\"pass\":true,\"accepted_utf8\":true,\"refusals\":\(refusals),\"physical_device\":false}")
    }
}
extension String { func repeatCount(_ count: Int) -> String { String(repeating: self, count: count) } }
