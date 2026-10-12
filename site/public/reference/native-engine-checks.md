# Check the PS engine in an iPhone simulator

This is a developer verification route, not an iPhone app download. Native Share
is still open: the tested prototype did not deliver the selected text reliably,
and it is not distributed as an installable app. The website's separate phone
checker remains available.

The failed prototype is retained in a
[plain source archive](https://github.com/knwvmbrr/aitrust-id/blob/main/docs/experiments/native-share-unreleased.json)
for inspection and future repair. It is not an app download or a passing workflow.

The verification executable bundles the same PS Python method, frozen Unicode
normalization and Pyodide runtime used by the device preview. It checks invented
examples on a newly created simulator, records results and removes only that
simulator. It does not read your phone, clipboard, messages or browser profile.
No text is sent to a service. Apple's SDK and simulator are host development
tools; the wrapper source is open, which does not make Apple's OS open source.

## Run the developer check

Use a Mac with Xcode, an **already installed** available iOS simulator runtime,
Python 3.12 or later, and at least 5 GB of free disk space. OS boot can take
longer than checker execution; boot failures return unavailable and remain
distinct from detector failures. No OS image or signing credential is created
or downloaded by the verifier.

From a current downloaded checkout, install its pinned website dependencies and
prepare the current public assets using the documented site build. Then use the
exact identifier listed by `xcrun simctl list runtimes`:

```sh
practice="$(mktemp -d "${TMPDIR:-/tmp}/aitrust-native.XXXXXXXX")"
python3 scripts/verify-ios-bundle.py --output "$practice/engine-proof" --runtime com.apple.CoreSimulator.SimRuntime.iOS-26-2
```

Use your installed runtime's identifier if it differs. The output directory must
be new and outside the repository. The private `proof.json` distinguishes
success from unavailable prerequisites. The command compiles and ad-hoc signs a
disposable verification executable; it never signs or installs a physical-phone
app. It checks 86 development examples, 41 normalization witnesses and 10 Unicode
boundary examples, with separate resource and invalid-input refusals. Those
examples do not measure independent accuracy.

The observed engine pass used Xcode 27.0, SDK 27.0 and the iPhone 14 Plus simulator
on iOS 26.2. After factoring resource packaging out of the unreleased app
prototype, two fresh-runtime attempts timed out during OS startup. The retained
passing engine observation and exact resource comparison do not turn those
later unavailable runs into passes.

## Inspect the exact resources

```sh
python3 scripts/prepare-native-bundle.py --output "$practice/resources"
```

This creates an owner-private ZIP of public verification resources only. It is
not an installable app and contains no phone profile, credential or user input.
The bundle rejects stale method/runtime/normalization identities and unknown
assets. Preparing it successfully does not establish native sharing, device
memory safety or real-user usability.

## Test temporary-copy refusals separately

```sh
python3 scripts/verify-shared-text.py --output "$practice/file-proof"
```

This macOS-only check exercises accepted UTF-8 and ten hostile/unsupported file
cases against the proposed provider-copy reader. It does not establish an iOS
provider can deliver that copy. Apple's documented
[temporary-file provider API](https://developer.apple.com/documentation/foundation/nsitemprovider/loadfilerepresentation%28fortypeidentifier%3Acompletionhandler%3A%29)
can use temporary files; no OS storage or memory-erasure guarantee is made.

Keep outputs private. Remove your practice folder when finished. Physical iPhone
install, Share compatibility, memory/lifecycle, VoiceOver and independent tag
validation remain separate open acceptance tasks.
