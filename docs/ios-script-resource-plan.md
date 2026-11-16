# Treat the bundled detector as interpreted source text

## Observed failure and architecture

Apple's actual November 12 validation rejected
`AITrustIDShare.appex/Assets/method.py` as unsigned code. Local strict bundle
signature verification and IPA export had passed. Preserve that failure; they
are different gates. The detector is fixed, bundled Python source loaded as
text by the offline WebKit/Pyodide runtime. It is not a native executable.

Package its physical resource as `Assets/method.py.txt`, explicitly denoting
source text, while preserving the existing allowlisted logical `/method.py`
route, exact detector bytes, MIME type, SHA-256 identities, input bounds,
privacy constraints and offline execution. Map that one logical route to the
fixed physical name in the native resource handler. Do not allow arbitrary
mapping, remote code, mutable downloaded methods, new entitlements, unsigned
native code or excluded resource sealing. The resource stays covered by the
containing signed bundle. This naming change is a repair candidate, not proof
of Apple acceptance or that filename alone caused the rejection.

Apple's [bundle placement guidance](https://developer.apple.com/documentation/bundleresources/placing-content-in-a-bundle)
classifies interpreted scripts as resources, and distinguishes them from native
code. [TN2206](https://developer.apple.com/library/archive/technotes/tn2206/)
warns that script signatures stored in extended attributes can be lost during
App Store transfer. It describes macOS layouts; do not copy its `Contents/`
layout into the iOS app. Recheck Apple's actual iOS validator for this package.

## Risks and verification

The principal risk is a mismatched physical path hiding a broken checker behind
a valid native signature. Keep the logical asset fingerprints unchanged; verify
package bytes, loader refusals, tamper rejection, actual offline execution and
the existing five native app/Share workflows with current source hashes. Update
packaging checks and the disposable mutation probe for the physical filename.

Create a fresh signed Release archive and export, preserving failed artifacts
and the owner's existing certificate/profiles. Verify both signatures, resource
bytes, entitlements and version before actual Apple validation. Only its success
permits upload preparation. Record a new failure instead of weakening signing
rules if Apple still rejects it. No full scope closure follows from packaging;
independent tag validation and human/physical acceptance remain open.

## Recorded candidate execution

All 137 detector cases and 11 resource refusal controls pass on an owned iPhone
14 Plus simulator with iOS 26.2. The initial five-workflow run had two failures
(keyboard opening and Share-cell discovery); retain that failed receipt. A
separate run with failure attachments enabled and no concurrent Xcode work
passed all five workflows. This does not prove the cause of the first failure
or establish physical or human acceptance. No existing assertion was relaxed.
The updated source-bound native evidence guard and its 20 refusal controls pass.

A command-line archive attempt failed with `errSecInternalComponent`; read-only
Keychain status showed it unlocked. Do not infer a root cause from that. The
same manually provisioned project then archived through Xcode. Both signatures,
32 resource copies and the existing four entitlement keys were inspected. The
repaired archive still requires actual Apple revalidation and upload.

## Candidate rejected

Actual Apple revalidation rejected `method.py.txt` with the same unsigned-code
error. This naming candidate is superseded, not accepted. The additional hosted
iOS 27.2 workflow passed four tests and failed Share entry; its cause is not yet
established. Continue with [sealed module packaging](ios-module-archive-plan.md),
preserving both failures and the unchanged detector source identity.
