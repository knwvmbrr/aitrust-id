# Native privacy manifest packaging

## Job and current evidence

Package a source-reviewed `PrivacyInfo.xcprivacy` at the root of both native
bundles. The current app owns no tracking endpoint, account, analytics SDK or
telemetry flow. Keep the declaration limited to `NSPrivacyTracking: false`.
The existing prose notice remains available in the app. Source/binary review is
separate from App Store Connect declarations and legal/platform approval.

Read-only inspection of the actually validated Release IPA found no imports for
fstat/stat/lstat, file-attribute, system-uptime, disk-capacity or user-defaults
candidate APIs in either executable. This is a bounded symbol observation, not
proof of every indirect call or transitive SDK obligation. The unused legacy
file-reader source includes fstat; do not infer from source alone that it is used
in the shipped executable. F-057/X-02 review remains open.

## Architecture and risks

The project generator reads one canonical, tracked XML plist through existing
no-symlink source boundaries. Only the reviewed false-tracking declaration is
accepted. A changed declaration needs a new source/privacy review. Both targets
copy the file through their resources phases. Add the manifest to source-bound
native evidence, and inspect the actual generated bundle manifest bytes.

Do not add empty accessed-API or tracking-domain arrays. Apple's TN3181 says to
omit an empty accessed-API entry and omit tracking domains when tracking is false.
No required-reason identifier is invented to fill a form. Add a reason only when
actual use and an approved purpose have been reviewed. A manifest does not make
future data collection acceptable or clear every bundled dependency.

Risks: invalid plist, duplicate/shadowed keys, unreviewed tracking declarations,
missing target membership, stale copied resources, missing source binding and
borrowing old package approval for changed bytes. Exercise real packaging and
refusal controls, plist lint and native bundle inspection. A changed generated
package requires its own signing/Apple validation; preserve the already validated
IPA as history. Do not submit final platform declarations without the owner.

## Sources checked November 16, 2026

- [Apple TN3181](https://developer.apple.com/documentation/technotes/tn3181-debugging-invalid-privacy-manifest)
- [Adding a privacy manifest](https://developer.apple.com/documentation/bundleresources/adding-a-privacy-manifest-to-your-app-or-third-party-sdk)
- [Describing data use](https://developer.apple.com/documentation/bundleresources/describing-data-use-in-privacy-manifests)

The release-specific import observations are stored privately beside the validated
IPA; no signing key, account token, user example or private input is included in
the public packaging contract.
