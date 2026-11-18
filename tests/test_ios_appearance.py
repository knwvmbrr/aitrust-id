"""Run actual Foundation preference storage without touching owner defaults."""
from pathlib import Path
import json
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.skipif(sys.platform != 'darwin', reason='Actual Apple Foundation test needs the macOS SDK')
def test_actual_appearance_defaults_are_bounded_persistent_and_isolated(tmp_path):
    source = tmp_path / 'main.swift'
    source.write_text(r'''
import Foundation
let names = ["aitrust-appearance-check-app-" + UUID().uuidString,
             "aitrust-appearance-check-share-" + UUID().uuidString]
let app = UserDefaults(suiteName: names[0])!
let share = UserDefaults(suiteName: names[1])!
defer {
    app.removePersistentDomain(forName: names[0])
    share.removePersistentDomain(forName: names[1])
}
let appSettings = AppearanceSettings(defaults: app)
let shareSettings = AppearanceSettings(defaults: share)
precondition(appSettings.preference == .system && shareSettings.preference == .system)
app.set("invented private text", forKey: "unrelated-input-like-key")
app.set(17, forKey: "unrelated-setting")
appSettings.preference = .dark
precondition(app.object(forKey: AppearanceSettings.key) as? String == "dark")
precondition(AppearanceSettings(defaults: UserDefaults(suiteName: names[0])!).preference == .dark)
precondition(shareSettings.preference == .system)
shareSettings.preference = .light
precondition(appSettings.preference == .dark && shareSettings.preference == .light)
appSettings.preference = .light
precondition(appSettings.preference == .light)
appSettings.preference = .system
precondition(appSettings.preference == .system && app.object(forKey: AppearanceSettings.key) == nil)
for malformed: Any in ["sepia", "", "DARK", 1, true, ["appearance": "dark"], ["dark"], Data([1])] {
    app.set(malformed, forKey: AppearanceSettings.key)
    precondition(appSettings.preference == .system)
}
appSettings.preference = .dark
precondition(app.string(forKey: "unrelated-input-like-key") == "invented private text")
precondition(app.integer(forKey: "unrelated-setting") == 17)
precondition(Set(app.persistentDomain(forName: names[0])!.keys) ==
             Set([AppearanceSettings.key, "unrelated-input-like-key", "unrelated-setting"]))
precondition(Set(share.persistentDomain(forName: names[1])!.keys) == Set([AppearanceSettings.key]))
print("{\"pass\":true,\"malformed_fallbacks\":8,\"isolated_domains\":2,\"unrelated_keys_preserved\":2,\"physical_device\":false}")
''')
    binary = tmp_path / 'appearance-checks'
    subprocess.run(['xcrun', '--sdk', 'macosx', 'swiftc', '-swift-version', '5',
                    '-module-cache-path', str(tmp_path / 'CompilerCache'),
                    str(ROOT / 'mobile/ios/Source/AppearancePreference.swift'), str(source),
                    '-o', str(binary)], check=True, capture_output=True, timeout=90)
    actual = subprocess.run([str(binary)], check=True, capture_output=True, timeout=15)
    assert json.loads(actual.stdout) == {'pass': True, 'malformed_fallbacks': 8,
        'isolated_domains': 2, 'unrelated_keys_preserved': 2, 'physical_device': False}
