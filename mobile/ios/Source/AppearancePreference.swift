import Foundation

/// Only this non-sensitive display choice is persisted, in this bundle's domain.
enum AppearancePreference: String {
    case system, light, dark
}

final class AppearanceSettings {
    static let key = "com.aitrustid.appearance.v1"
    private let defaults: UserDefaults
    init(defaults: UserDefaults = .standard) { self.defaults = defaults }
    var preference: AppearancePreference {
        get {
            guard let raw = defaults.object(forKey: Self.key) as? String,
                  let preference = AppearancePreference(rawValue: raw) else { return .system }
            return preference
        }
        set {
            if newValue == .system { defaults.removeObject(forKey: Self.key) }
            else { defaults.set(newValue.rawValue, forKey: Self.key) }
        }
    }
}
