import Foundation
import Darwin

/// Read only the selected provider's copy beneath the app's own temporary root.
/// No URI/file input is accepted through the user interface.
enum SharedText {
    enum Refusal: Error { case unsupported }
    static func read(_ url: URL, root: URL = FileManager.default.temporaryDirectory) throws -> String {
        guard url.isFileURL else { throw Refusal.unsupported }
        let root = root.standardizedFileURL.resolvingSymlinksInPath()
        let file = url.standardizedFileURL
        let prefix = root.path + "/"
        guard file.path.hasPrefix(prefix) else { throw Refusal.unsupported }
        let parts = String(file.path.dropFirst(prefix.count)).split(separator: "/").map(String.init)
        guard !parts.isEmpty, parts.allSatisfy({ !$0.isEmpty && $0 != "." && $0 != ".." }) else { throw Refusal.unsupported }
        var directory = open(root.path, O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC)
        guard directory >= 0 else { throw Refusal.unsupported }; defer { close(directory) }
        for component in parts.dropLast() {
            let next = openat(directory, component, O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC)
            guard next >= 0 else { throw Refusal.unsupported }; close(directory); directory = next
        }
        let descriptor = openat(directory, parts.last!, O_RDONLY | O_NOFOLLOW | O_CLOEXEC | O_NONBLOCK)
        guard descriptor >= 0 else { throw Refusal.unsupported }
        let handle = FileHandle(fileDescriptor: descriptor, closeOnDealloc: true); defer { try? handle.close() }
        var before = stat(); guard fstat(descriptor, &before) == 0,
            (before.st_mode & S_IFMT) == S_IFREG, before.st_nlink == 1, before.st_uid == geteuid(), before.st_size >= 0, before.st_size <= 80000 else { throw Refusal.unsupported }
        let data = try handle.read(upToCount: 80001) ?? Data()
        var after = stat(); guard fstat(descriptor, &after) == 0, data.count <= 80000,
            before.st_dev == after.st_dev, before.st_ino == after.st_ino, before.st_size == after.st_size,
            before.st_mtimespec.tv_sec == after.st_mtimespec.tv_sec, before.st_mtimespec.tv_nsec == after.st_mtimespec.tv_nsec,
            data.count == before.st_size, let text = String(data: data, encoding: .utf8),
            text.unicodeScalars.count <= 20000, !text.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else { throw Refusal.unsupported }
        return text
    }
}
